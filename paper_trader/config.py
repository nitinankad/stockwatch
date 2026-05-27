from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import SettingsConfigDict

from shared.settings import CsvAwareSettings

_DEFAULT_MODEL_DIR = str(Path(__file__).resolve().parents[1] / "models")


class Settings(CsvAwareSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    alpaca_api_key: str = ""
    alpaca_api_secret: str = ""

    # Tickers to watch and trade
    paper_symbols: list[str] = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]

    # Portfolio
    paper_initial_cash: float = 100_000.0
    paper_position_size_usd: float = 5_000.0   # dollars per trade

    # Signal
    paper_trade_horizon: str = "1h"             # which XGBoost model to use
    paper_min_signal_pct: float = 0.10          # minimum |prob - 0.5| to enter (e.g. 0.10 → prob must be ≥0.60 or ≤0.40)
    paper_ohlcv_timeframe: str = "5Min"         # bar resolution for live feature computation
    paper_alpaca_feed: str = "iex"              # 'iex' (free tier) or 'sip' (paid plan)

    # Risk management
    paper_stop_loss_pct: float = 1.5
    paper_trailing_stop_pct: float = 2.0   # close when price retraces X% from position peak
    paper_max_hold_multiplier: float = 2.0 # hard-close at horizon × this, regardless of signal
    paper_flip_persistence: int = 2        # consecutive opposing ticks required to exit on signal flip
    paper_allow_shorts: bool = False
    paper_max_positions: int = 5

    # Loop
    paper_poll_interval_seconds: int = 300      # how often to re-evaluate (seconds)

    database_url: str = ""
    model_dir: str = _DEFAULT_MODEL_DIR
    log_level: str = "INFO"

    @field_validator("paper_symbols", mode="before")
    @classmethod
    def _split_csv(cls, v: object) -> object:
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v
