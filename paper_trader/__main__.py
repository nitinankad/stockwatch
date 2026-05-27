"""
In-memory paper trading bot.

Run from the project root:
    python -m paper_trader

The bot loads the trained XGBoost models from models/, fetches live bars from
Alpaca's market data API, computes technical indicators in real time, and
manages a fake portfolio in memory — no Alpaca paper trading account needed.

Optional flags (pass as env vars or in .env):
    PAPER_SYMBOLS=AAPL,MSFT,NVDA          # tickers to watch (default: AAPL,MSFT,NVDA,TSLA,AMZN)
    PAPER_INITIAL_CASH=100000             # starting fake cash (default: 100000)
    PAPER_POSITION_SIZE_USD=5000          # dollars per trade (default: 5000)
    PAPER_TRADE_HORIZON=1h                # model horizon: 1h | 4h | 1d (default: 1h)
    PAPER_MIN_SIGNAL_PCT=0.15             # minimum |predicted %| to trade (default: 0.15)
    PAPER_STOP_LOSS_PCT=1.5               # hard stop below entry % (default: 1.5)
    PAPER_TRAILING_STOP_PCT=2.0           # retrace from peak before exit % (default: 2.0)
    PAPER_MAX_HOLD_MULTIPLIER=2.0         # hard-close at horizon × N (default: 2.0)
    PAPER_FLIP_PERSISTENCE=2              # consecutive opposing ticks to trigger exit (default: 2)
    PAPER_ALLOW_SHORTS=false              # allow short selling (default: false)
    PAPER_MAX_POSITIONS=5                 # max concurrent positions (default: 5)
    PAPER_OHLCV_TIMEFRAME=5Min            # bar resolution for feature computation (default: 5Min)
    PAPER_POLL_INTERVAL_SECONDS=300       # how often to re-evaluate (default: 300)
    DATABASE_URL=...                      # required for --backtest mode

Add --once to run a single evaluation and exit (useful for testing):
    python -m paper_trader --once

Backtest mode — replay historical OHLCV bars from the DB (no Alpaca key needed):
    python -m paper_trader --backtest --start 2024-01-01 --end 2024-06-30
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from paper_trader.config import Settings
from paper_trader.engine import PaperTradingEngine
from paper_trader.portfolio import Portfolio
from shared.alpaca import AlpacaClient

load_dotenv()


def _parse_date(s: str) -> datetime:
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date '{s}' — expected YYYY-MM-DD")


def main() -> None:
    parser = argparse.ArgumentParser(description="StockWatch paper trader")
    parser.add_argument("--once",     action="store_true", help="Run a single tick and exit")
    parser.add_argument("--backtest", action="store_true", help="Replay historical bars from the DB")
    parser.add_argument("--start",    type=_parse_date,    metavar="YYYY-MM-DD",
                        help="Backtest start date (inclusive)")
    parser.add_argument("--end",      type=_parse_date,    metavar="YYYY-MM-DD",
                        help="Backtest end date (inclusive, defaults to today)")
    args = parser.parse_args()

    settings = Settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    if not settings.paper_symbols:
        print("ERROR: PAPER_SYMBOLS is empty — set at least one ticker")
        sys.exit(1)

    if args.backtest:
        # Backtest mode: needs DATABASE_URL, no Alpaca keys required.
        if not settings.database_url:
            print("ERROR: DATABASE_URL must be set in .env for backtest mode")
            sys.exit(1)
        if args.start is None:
            print("ERROR: --start YYYY-MM-DD is required for --backtest")
            sys.exit(1)
        end_dt = args.end or datetime.now(timezone.utc)

        portfolio = Portfolio(initial_cash=settings.paper_initial_cash)
        engine = PaperTradingEngine(
            portfolio=portfolio,
            alpaca=None,
            symbols=settings.paper_symbols,
            model_dir=Path(settings.model_dir),
            trade_horizon=settings.paper_trade_horizon,
            position_size_usd=settings.paper_position_size_usd,
            min_signal_pct=settings.paper_min_signal_pct,
            stop_loss_pct=settings.paper_stop_loss_pct,
            trailing_stop_pct=settings.paper_trailing_stop_pct,
            max_hold_multiplier=settings.paper_max_hold_multiplier,
            flip_persistence=settings.paper_flip_persistence,
            allow_shorts=settings.paper_allow_shorts,
            max_positions=settings.paper_max_positions,
            ohlcv_timeframe=settings.paper_ohlcv_timeframe,
            poll_interval_seconds=settings.paper_poll_interval_seconds,
        )

        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(engine.run_backtest(args.start, end_dt, settings.database_url))
        return

    # Live mode: requires Alpaca keys.
    if not settings.alpaca_api_key or not settings.alpaca_api_secret:
        print("ERROR: ALPACA_API_KEY and ALPACA_API_SECRET must be set in .env")
        sys.exit(1)

    portfolio = Portfolio(initial_cash=settings.paper_initial_cash)
    alpaca = AlpacaClient(settings.alpaca_api_key, settings.alpaca_api_secret)

    engine = PaperTradingEngine(
        portfolio=portfolio,
        alpaca=alpaca,
        symbols=settings.paper_symbols,
        model_dir=Path(settings.model_dir),
        trade_horizon=settings.paper_trade_horizon,
        position_size_usd=settings.paper_position_size_usd,
        min_signal_pct=settings.paper_min_signal_pct,
        stop_loss_pct=settings.paper_stop_loss_pct,
        trailing_stop_pct=settings.paper_trailing_stop_pct,
        max_hold_multiplier=settings.paper_max_hold_multiplier,
        flip_persistence=settings.paper_flip_persistence,
        allow_shorts=settings.paper_allow_shorts,
        max_positions=settings.paper_max_positions,
        ohlcv_timeframe=settings.paper_ohlcv_timeframe,
        poll_interval_seconds=settings.paper_poll_interval_seconds,
        alpaca_feed=settings.paper_alpaca_feed,
    )

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    if args.once:
        asyncio.run(engine.run_once())
    else:
        asyncio.run(engine.run())


if __name__ == "__main__":
    main()
