import requests

ticker = "RDDT"

URL_TEMPLATE = f"https://finviz.com/quote.ashx?t={ticker}&p=d"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
}

r = requests.get(URL_TEMPLATE, headers=HEADERS)

print(r.text)
