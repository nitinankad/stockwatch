from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_conn
from app.schemas.stock import (
    HorizonPrediction,
    PredictionsResponse,
    StockListResponse,
    StockResponse,
)
from app.services.stock_service import StockService

router = APIRouter()
stock_service = StockService()

Conn = Annotated[psycopg.AsyncConnection, Depends(get_conn)]


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


@router.get("/{ticker}/predictions", response_model=PredictionsResponse)
async def get_predictions(ticker: str, conn: Conn) -> PredictionsResponse:
    from shared.db.prediction_log_repo import PredictionLogRepository

    rows = await PredictionLogRepository(conn).get_latest_for_ticker(ticker.upper())
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No predictions found for '{ticker.upper()}'. "
                   "Make sure the pipeline has processed news for this ticker.",
        )
    return PredictionsResponse(
        ticker=ticker.upper(),
        predictions=[
            HorizonPrediction(
                horizon=row["prediction_horizon"],
                predicted_pct_change=row["predicted_pct_change"],
                direction=row["derived_direction"],
                actual_pct_change=row["actual_pct_change"],
                error=row["error"],
                predicted_at=row["predicted_at"],
                resolved_at=row["resolved_at"],
                snapshot_timestamp=row["snapshot_timestamp"],
            )
            for row in rows
        ],
    )
