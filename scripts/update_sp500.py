"""Utility script to fetch the S&P 500 ticker list from Wikipedia and save to data/sp500_tickers.json."""

import json
import sys
from pathlib import Path

import requests

OUTPUT = Path(__file__).resolve().parent.parent / "data" / "sp500_tickers.json"


def fetch_sp500():
    """Scrape S&P 500 list from Wikipedia."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0 StockPulse/1.0"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    # Parse the HTML table
    from html.parser import HTMLParser

    class SP500Parser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.in_table = False
            self.in_tbody = False
            self.in_row = False
            self.in_cell = False
            self.current_row = []
            self.cell_text = ""
            self.rows = []
            self.table_count = 0

        def handle_starttag(self, tag, attrs):
            if tag == "table":
                self.table_count += 1
                if self.table_count == 1:
                    self.in_table = True
            if self.in_table and tag == "tbody":
                self.in_tbody = True
            if self.in_tbody and tag == "tr":
                self.in_row = True
                self.current_row = []
            if self.in_row and tag == "td":
                self.in_cell = True
                self.cell_text = ""
            if self.in_cell and tag == "a":
                pass  # text will be captured in handle_data

        def handle_endtag(self, tag):
            if tag == "td" and self.in_cell:
                self.current_row.append(self.cell_text.strip())
                self.in_cell = False
            if tag == "tr" and self.in_row:
                if self.current_row:
                    self.rows.append(self.current_row)
                self.in_row = False
            if tag == "tbody" and self.in_tbody:
                self.in_tbody = False
            if tag == "table" and self.in_table:
                self.in_table = False

        def handle_data(self, data):
            if self.in_cell:
                self.cell_text += data

    parser = SP500Parser()
    parser.feed(resp.text)

    tickers = []
    for row in parser.rows:
        if len(row) >= 4:
            symbol = row[0].replace(".", "-")  # BRK.B -> BRK-B for yfinance
            name = row[1]
            sector = row[3]
            if symbol and name:
                tickers.append({
                    "symbol": symbol,
                    "name": name,
                    "sector": sector,
                })

    return tickers


def main():
    print("Fetching S&P 500 list from Wikipedia...")
    tickers = fetch_sp500()
    print(f"Found {len(tickers)} tickers")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(tickers, f, indent=2)

    print(f"Saved to {OUTPUT}")

    # Show sector breakdown
    sectors = {}
    for t in tickers:
        s = t.get("sector", "Unknown")
        sectors[s] = sectors.get(s, 0) + 1
    print("\nSectors:")
    for s, c in sorted(sectors.items(), key=lambda x: -x[1]):
        print(f"  {s}: {c}")


if __name__ == "__main__":
    main()
