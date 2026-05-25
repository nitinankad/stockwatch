from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from feature_eng.indicators import FEATURE_COLUMNS, bar_size_minutes, compute_ohlcv_features
from paper_trader.portfolio import Portfolio, Trade
from shared.alpaca import AlpacaClient

logger = logging.getLogger(__name__)

_HORIZON_MINUTES = {"1h": 60, "4h": 240, "1d": 390, "1w": 1_950, "2w": 3_900, "1m": 8_190}
_SENTIMENT_ZERO = {
    "sentiment_avg_1h": 0.0,
    "sentiment_count_1h": 0.0,
    "sentiment_deviation": 0.0,
    "sentiment_momentum": 0.0,
    "has_breaking_event": 0.0,
}


class PaperTradingEngine:
    def __init__(
        self,
        portfolio: Portfolio,
        alpaca: AlpacaClient,
        symbols: list[str],
        model_dir: Path,
        trade_horizon: str = "1h",
        position_size_usd: float = 5_000.0,
        min_signal_pct: float = 0.15,
        stop_loss_pct: float = 1.5,
        take_profit_pct: float = 3.0,
        allow_shorts: bool = False,
        max_positions: int = 5,
        ohlcv_timeframe: str = "5Min",
        poll_interval_seconds: int = 300,
        alpaca_feed: str = "iex",
    ) -> None:
        self._portfolio = portfolio
        self._alpaca = alpaca
        self._symbols = symbols
        self._model_dir = model_dir
        self._trade_horizon = trade_horizon
        self._position_size_usd = position_size_usd
        self._min_signal_pct = min_signal_pct
        self._stop_loss_pct = stop_loss_pct
        self._take_profit_pct = take_profit_pct
        self._allow_shorts = allow_shorts
        self._max_positions = max_positions
        self._ohlcv_timeframe = ohlcv_timeframe
        self._poll_interval_seconds = poll_interval_seconds
        self._alpaca_feed = alpaca_feed
        self._models: dict[str, xgb.Booster] = {}

    async def run(self) -> None:
        self._load_models()
        if self._trade_horizon not in self._models:
            raise RuntimeError(
                f"Model for horizon '{self._trade_horizon}' not found in {self._model_dir}. "
                "Run `python -m training` first."
            )

        self._print_header()
        logger.info(
            "paper_trader.start symbols=%s horizon=%s size_usd=%.0f poll=%ds",
            self._symbols, self._trade_horizon, self._position_size_usd, self._poll_interval_seconds,
        )

        while True:
            try:
                await self._tick()
            except Exception as exc:
                logger.error("paper_trader.tick_error %s", exc, exc_info=True)
            await asyncio.sleep(self._poll_interval_seconds)

    async def run_once(self) -> None:
        """Run a single evaluation tick (useful for testing)."""
        self._load_models()
        if self._trade_horizon not in self._models:
            raise RuntimeError(
                f"Model for horizon '{self._trade_horizon}' not found in {self._model_dir}."
            )
        self._print_header()
        await self._tick()

    # ------------------------------------------------------------------
    # Core tick
    # ------------------------------------------------------------------

    async def _tick(self) -> None:
        now = datetime.now(timezone.utc)
        # 8 calendar days covers 5 trading days needed for price_change_5d
        start = now - timedelta(days=8)

        bars_by_ticker = await self._alpaca.get_bars(
            self._symbols, start=start, end=now,
            timeframe=self._ohlcv_timeframe, feed=self._alpaca_feed,
        )

        prices: dict[str, float] = {}
        predictions: dict[str, float] = {}

        total_bars = sum(len(v) for v in bars_by_ticker.values())
        if total_bars == 0:
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}]  "
                "No bars returned — market is likely closed (holiday or outside trading hours). "
                f"Next check in {self._poll_interval_seconds}s."
            )
            return

        for ticker in self._symbols:
            bars = bars_by_ticker.get(ticker, [])
            if len(bars) < 10:
                logger.warning(
                    "paper_trader.skip ticker=%s reason=insufficient_bars n=%d", ticker, len(bars)
                )
                continue

            prices[ticker] = float(bars[-1].close)

            df = pd.DataFrame([{
                "open":      float(b.open),
                "high":      float(b.high),
                "low":       float(b.low),
                "close":     float(b.close),
                "volume":    float(b.volume),
                "timestamp": b.timestamp,
            } for b in bars])

            features = {**compute_ohlcv_features(df, bar_minutes=bar_size_minutes(self._ohlcv_timeframe)), **_SENTIMENT_ZERO}
            model = self._models[self._trade_horizon]
            x = np.array([[features.get(col, 0.0) for col in FEATURE_COLUMNS]], dtype=np.float32)
            dmatrix = xgb.DMatrix(x, feature_names=FEATURE_COLUMNS)
            predictions[ticker] = float(model.predict(dmatrix)[0])

        # Close positions first
        for ticker in list(self._portfolio.positions):
            price = prices.get(ticker)
            if price is None:
                continue
            should_close, reason = self._check_exit(
                self._portfolio.positions[ticker], predictions.get(ticker), price
            )
            if should_close:
                trade = self._portfolio.close(ticker, price, reason)
                if trade:
                    self._log_trade(trade)

        # Open new positions — highest conviction first (conviction = |prob - 0.5|)
        candidates = sorted(
            [(t, p) for t, p in predictions.items() if t not in self._portfolio.positions],
            key=lambda kv: abs(kv[1] - 0.5),
            reverse=True,
        )
        for ticker, prob in candidates:
            if len(self._portfolio.positions) >= self._max_positions:
                break
            conviction = abs(prob - 0.5)
            if conviction < self._min_signal_pct:
                continue
            direction = "long" if prob >= 0.5 else "short"
            if direction == "short" and not self._allow_shorts:
                continue
            price = prices[ticker]
            shares = self._position_size_usd / price
            opened = self._portfolio.open(ticker, direction, price, shares, self._trade_horizon, prob)
            if opened:
                logger.info(
                    "paper_trader.open ticker=%s dir=%s price=%.2f shares=%.4f prob=%.4f conv=%.4f",
                    ticker, direction, price, shares, prob, conviction,
                )

        self._print_status(prices, predictions)

    # ------------------------------------------------------------------
    # Exit logic
    # ------------------------------------------------------------------

    def _check_exit(self, pos, prob: float | None, price: float) -> tuple[bool, str]:
        if pos.direction == "long":
            pnl_pct = (price - pos.entry_price) / pos.entry_price * 100
        else:
            pnl_pct = (pos.entry_price - price) / pos.entry_price * 100

        if pnl_pct <= -self._stop_loss_pct:
            return True, "stop_loss"
        if pnl_pct >= self._take_profit_pct:
            return True, "take_profit"

        horizon_minutes = _HORIZON_MINUTES.get(self._trade_horizon, 60)
        age_minutes = (datetime.now(timezone.utc) - pos.entry_time).total_seconds() / 60
        if age_minutes >= horizon_minutes:
            return True, "timeout"

        if prob is not None:
            new_dir = "long" if prob >= 0.5 else "short"
            if new_dir != pos.direction and abs(prob - 0.5) >= self._min_signal_pct:
                return True, "signal_flip"

        return False, ""

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _load_models(self) -> None:
        for horizon in ("1h", "4h", "1d"):
            path = self._model_dir / f"xgb_{horizon}.json"
            if path.exists():
                model = xgb.Booster()
                model.load_model(str(path))
                self._models[horizon] = model
                logger.info("paper_trader.model_loaded horizon=%s", horizon)

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def _print_header(self) -> None:
        print(f"\n{'=' * 65}")
        print(f"  StockWatch Paper Trader")
        print(f"  Starting cash : ${self._portfolio.initial_cash:>12,.2f}")
        print(f"  Symbols       : {', '.join(self._symbols)}")
        print(f"  Horizon       : {self._trade_horizon}  |  Bar timeframe: {self._ohlcv_timeframe}")
        print(f"  Min conviction: |prob-0.5| >= {self._min_signal_pct:.2f}  |  Position size: ${self._position_size_usd:,.0f}")
        print(f"  Stop loss     : {self._stop_loss_pct:.1f}%   |  Take profit : {self._take_profit_pct:.1f}%")
        print(f"  Shorts        : {'enabled' if self._allow_shorts else 'disabled'}  |  Max positions: {self._max_positions}")
        print(f"{'=' * 65}\n")

    def _print_status(self, prices: dict[str, float], predictions: dict[str, float]) -> None:
        equity = self._portfolio.equity(prices)
        total_pnl = equity - self._portfolio.initial_cash
        pnl_pct = total_pnl / self._portfolio.initial_cash * 100
        sign = "▲" if total_pnl >= 0 else "▼"

        print(
            f"[{datetime.now().strftime('%H:%M:%S')}]  "
            f"Equity ${equity:,.2f}  "
            f"Cash ${self._portfolio.cash:,.2f}  "
            f"P&L {sign} ${total_pnl:+,.2f} ({pnl_pct:+.2f}%)  "
            f"Trades {len(self._portfolio.trades)}  "
            f"Win {self._portfolio.win_rate():.0f}%"
        )

        if self._portfolio.positions:
            print("  Open positions:")
            for ticker, pos in self._portfolio.positions.items():
                price = prices.get(ticker, pos.entry_price)
                if pos.direction == "long":
                    unrealized_pct = (price - pos.entry_price) / pos.entry_price * 100
                else:
                    unrealized_pct = (pos.entry_price - price) / pos.entry_price * 100
                age_min = (datetime.now(timezone.utc) - pos.entry_time).total_seconds() / 60
                arrow = "▲" if unrealized_pct >= 0 else "▼"
                print(
                    f"    {ticker:<6}  {pos.direction:<5}  {pos.shares:.3f}sh  "
                    f"entry ${pos.entry_price:.2f}  now ${price:.2f}  "
                    f"{arrow}{unrealized_pct:+.2f}%  {age_min:.0f}min old"
                )

        if predictions:
            print("  Signals:")
            for ticker, prob in sorted(predictions.items(), key=lambda kv: abs(kv[1] - 0.5), reverse=True):
                arrow = "▲" if prob >= 0.5 else "▼"
                direction = "bullish" if prob >= 0.5 else "bearish"
                conviction = abs(prob - 0.5)
                tag = "TRADE" if conviction >= self._min_signal_pct else "     "
                print(f"    {ticker:<6}  {arrow} {prob:.4f} ({conviction:+.4f} conv)  {direction}  {tag}")

    def _log_trade(self, trade: Trade) -> None:
        sign = "+" if trade.pnl >= 0 else ""
        logger.info(
            "paper_trader.close ticker=%s dir=%s entry=%.2f exit=%.2f "
            "pnl=%s%.2f (%s%.2f%%) reason=%s",
            trade.ticker, trade.direction,
            trade.entry_price, trade.exit_price,
            sign, trade.pnl, sign, trade.pnl_pct, trade.reason,
        )
        outcome = "WIN " if trade.pnl >= 0 else "LOSS"
        print(
            f"\n  [{outcome}] CLOSED {trade.ticker} ({trade.direction})"
            f"  entry ${trade.entry_price:.2f} → exit ${trade.exit_price:.2f}"
            f"  P&L ${trade.pnl:+.2f} ({trade.pnl_pct:+.2f}%)"
            f"  [{trade.reason}]\n"
        )
