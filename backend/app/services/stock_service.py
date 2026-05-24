from app.schemas.stock import StockResponse


SEED_STOCKS = [
    StockResponse(
        ticker="NVDA",
        company="NVIDIA Corporation",
        industry="Semiconductors",
        market_cap=2_180_000_000_000,
    ),
    StockResponse(
        ticker="MSFT",
        company="Microsoft Corporation",
        industry="Software - Infrastructure",
        market_cap=3_210_000_000_000,
    ),
    StockResponse(
        ticker="AAPL",
        company="Apple Inc.",
        industry="Consumer Electronics",
        market_cap=3_180_000_000_000,
    ),
]


class StockService:
    def __init__(self, stocks: list[StockResponse] | None = None) -> None:
        self._stocks = stocks or SEED_STOCKS

    def list_stocks(self, query: str | None = None, limit: int = 50) -> list[StockResponse]:
        stocks = self._stocks
        if query:
            normalized_query = query.lower()
            stocks = [
                stock
                for stock in stocks
                if normalized_query in stock.ticker.lower()
                or normalized_query in stock.company.lower()
            ]
        return stocks[:limit]

    def get_stock(self, ticker: str) -> StockResponse | None:
        normalized_ticker = ticker.upper()
        return next((stock for stock in self._stocks if stock.ticker == normalized_ticker), None)
