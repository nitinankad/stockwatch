from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Position:
    ticker: str
    direction: str          # 'long' | 'short'
    entry_price: float
    shares: float
    cost_basis: float       # dollars reserved (entry_price * shares)
    entry_time: datetime
    horizon: str
    predicted_pct: float
    peak_price: float = 0.0  # high-water mark (long) / trough (short) for trailing stop


@dataclass
class Trade:
    ticker: str
    direction: str
    entry_price: float
    exit_price: float
    shares: float
    pnl: float
    pnl_pct: float
    entry_time: datetime
    exit_time: datetime
    horizon: str
    reason: str             # 'stop_loss' | 'take_profit' | 'signal_flip' | 'timeout'


class Portfolio:
    def __init__(self, initial_cash: float = 100_000.0) -> None:
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: dict[str, Position] = {}
        self.trades: list[Trade] = []

    def open(
        self,
        ticker: str,
        direction: str,
        price: float,
        shares: float,
        horizon: str,
        predicted_pct: float,
        entry_time: datetime | None = None,
    ) -> bool:
        cost = price * shares
        if cost > self.cash:
            return False
        self.cash -= cost
        self.positions[ticker] = Position(
            ticker=ticker,
            direction=direction,
            entry_price=price,
            shares=shares,
            cost_basis=cost,
            entry_time=entry_time or datetime.now(timezone.utc),
            horizon=horizon,
            predicted_pct=predicted_pct,
            peak_price=price,
        )
        return True

    def close(self, ticker: str, price: float, reason: str, now: datetime | None = None) -> Trade | None:
        pos = self.positions.pop(ticker, None)
        if pos is None:
            return None

        if pos.direction == "long":
            pnl = (price - pos.entry_price) * pos.shares
        else:
            pnl = (pos.entry_price - price) * pos.shares

        # Return reserved capital ± P&L
        self.cash += pos.cost_basis + pnl
        pnl_pct = pnl / pos.cost_basis * 100

        trade = Trade(
            ticker=ticker,
            direction=pos.direction,
            entry_price=pos.entry_price,
            exit_price=price,
            shares=pos.shares,
            pnl=pnl,
            pnl_pct=pnl_pct,
            entry_time=pos.entry_time,
            exit_time=now or datetime.now(timezone.utc),
            horizon=pos.horizon,
            reason=reason,
        )
        self.trades.append(trade)
        return trade

    def equity(self, current_prices: dict[str, float]) -> float:
        """Total portfolio value: cash + open position value."""
        unrealized = 0.0
        for ticker, pos in self.positions.items():
            price = current_prices.get(ticker, pos.entry_price)
            if pos.direction == "long":
                unrealized += (price - pos.entry_price) * pos.shares
            else:
                unrealized += (pos.entry_price - price) * pos.shares
        return self.cash + sum(p.cost_basis for p in self.positions.values()) + unrealized

    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.pnl > 0)
        return wins / len(self.trades) * 100
