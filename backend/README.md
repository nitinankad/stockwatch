# StockWatch Backend

FastAPI backend for StockWatch.

## Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
```

## Run

```powershell
uvicorn app.main:app --reload
```

API docs are available at:

- http://localhost:8000/docs
- http://localhost:8000/redoc

## Endpoints

- `GET /health`
- `GET /api/v1/stocks`
- `GET /api/v1/stocks/{ticker}`
