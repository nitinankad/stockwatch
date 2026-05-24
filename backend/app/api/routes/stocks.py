from fastapi import APIRouter, HTTPException, Query

from app.schemas.stock import StockListResponse, StockResponse
from app.services.stock_service import StockService

router = APIRouter()
stock_service = StockService()


@router.get("", response_model=StockListResponse)
def list_stocks(
    q: str | None = Query(default=None, description="Filter by ticker or company name."),
    limit: int = Query(default=50, ge=1, le=500),
) -> StockListResponse:
    stocks = stock_service.list_stocks(query=q, limit=limit)
    return StockListResponse(count=len(stocks), results=stocks)


@router.get("/{ticker}", response_model=StockResponse)
def get_stock(ticker: str) -> StockResponse:
    stock = stock_service.get_stock(ticker)
    if stock is None:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker.upper()}' was not found.")
    return stock
