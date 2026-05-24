import requests
from dotenv import load_dotenv
import os

load_dotenv()

tickers = "OUST"

url = f"https://data.alpaca.markets/v1beta1/news?sort=desc&symbols={tickers}&limit=50&include_content=true&exclude_contentless=true"

headers = {
    "accept": "application/json",
    "APCA-API-KEY-ID": os.environ["ALPACA_API_KEY"],
    "APCA-API-SECRET-KEY": os.environ["ALPACA_API_SECRET"]
}

response = requests.get(url, headers=headers)

print(response.json())
