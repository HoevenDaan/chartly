# StockPulse v1.0.0

**Stock Market Technical Advisor** — A local, production-ready web application that provides real-time technical analysis and trading signals for your stock watchlist.

![StockPulse Dashboard](screenshot-placeholder.png)

---

## Features

- **Real-time Stock Data** — Fetches price, volume, and company data via Yahoo Finance (free, no API key needed)
- **10 Technical Indicators** — RSI, MACD, SMA (20/50/200), EMA (12/26), Bollinger Bands, ATR, Stochastic Oscillator, Volume Analysis, 52-Week Position, Golden/Death Cross detection
- **Smart Signal Generation** — BUY/SELL/HOLD signals based on indicator confluence
- **Confidence Scoring** — 0-100 score showing signal strength with color-coded badges
- **Advisor Reports** — Human-readable analysis with support/resistance levels and stop-loss suggestions
- **Interactive Dashboard** — Dark-themed, responsive web UI with charts (Chart.js), signal cards, and detailed stock views
- **WhatsApp Notifications** — Optional alerts via CallMeBot (free) for signal alerts and daily summaries
- **Caching** — SQLite caching layer to respect rate limits and speed up responses
- **Background Scheduler** — Automatic data refresh and signal checking
- **REST API** — Full API with Swagger docs at `/docs`

---

## Prerequisites

- **Python 3.11+**
- Internet connection (for fetching stock data)

---

## Quick Start

### 1. Clone / Navigate to the project

```bash
cd stockpulse
```

### 2. Run setup

```bash
# Linux/Mac
chmod +x setup.sh
./setup.sh

# Windows (Git Bash)
bash setup.sh

# Or manually:
python -m venv venv
venv\Scripts\activate     # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
copy .env.example .env    # Windows
cp .env.example .env      # Linux/Mac
mkdir data logs
```

### 3. Start the app

```bash
python run.py
```

Open **http://127.0.0.1:8000** in your browser.

---

## Configuration

All settings are in `config.yaml`. Key options:

| Section | Setting | Default | Description |
|---------|---------|---------|-------------|
| `app.port` | Port | `8000` | Server port |
| `app.debug` | Debug | `false` | Enable debug mode |
| `app.log_level` | Log Level | `INFO` | Logging level |
| `watchlist.default_stocks` | Stocks | 5 stocks | Default watchlist |
| `data.cache_ttl_minutes` | Cache TTL | `15` | Minutes before cache expires |
| `data.history_period` | History | `1y` | How far back to fetch |
| `analysis.signals.min_confidence` | Min Confidence | `65` | Threshold for active signals |
| `analysis.signals.min_agreement` | Min Agreement | `3` | Indicators needed for signal |
| `scheduler.data_refresh_minutes` | Refresh | `15` | Data refresh interval |
| `scheduler.daily_summary_time` | Summary Time | `18:00` | Daily summary time |
| `notifications.whatsapp.enabled` | WhatsApp | `false` | Enable notifications |

### Environment Variables (`.env`)

```
ALPHA_VANTAGE_API_KEY=your_key   # Optional fallback data source
WHATSAPP_PHONE=+32xxxxxxxxx      # For WhatsApp notifications
CALLMEBOT_API_KEY=your_key       # For WhatsApp notifications
```

---

## WhatsApp Notification Setup (Optional)

StockPulse uses the **free CallMeBot API** for WhatsApp notifications.

### Step-by-step:

1. **Save the CallMeBot number** — Add **+34 644 52 74 88** to your WhatsApp contacts
2. **Send activation message** — Send `I allow callmebot to send me messages` to that number on WhatsApp
3. **Receive your API key** — You'll get a reply with your API key instantly
4. **Configure StockPulse** — Edit `.env`:
   ```
   WHATSAPP_PHONE=+32xxxxxxxxx
   CALLMEBOT_API_KEY=123456
   ```
5. **Enable in config.yaml**:
   ```yaml
   notifications:
     whatsapp:
       enabled: true
   ```
6. **Restart the app** — `python run.py`

### What you'll receive:
- **Signal Alerts** — Immediate notifications when a stock hits confidence >= 70
- **Daily Summary** — End-of-day summary of all watched stocks at 6 PM (configurable)

---

## API Documentation

Full interactive docs available at **http://127.0.0.1:8000/docs** (Swagger UI).

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/stocks` | All watched stocks with analysis |
| GET | `/api/stocks/{symbol}` | Detailed data for one stock |
| GET | `/api/stocks/{symbol}/history` | Historical price data |
| GET | `/api/stocks/{symbol}/analysis` | Full technical analysis |
| GET | `/api/signals` | All current signals |
| GET | `/api/signals/active` | Active signals (above threshold) |
| POST | `/api/watchlist` | Add stock `{"symbol": "AAPL"}` |
| DELETE | `/api/watchlist/{symbol}` | Remove stock |
| GET | `/api/config` | Current config |
| POST | `/api/refresh` | Force data refresh |

### Response Format

```json
{
  "status": "success",
  "data": { ... },
  "timestamp": "2026-02-28T14:30:00"
}
```

---

## How the Analysis Works

StockPulse combines 10 technical indicators to generate signals:

### Indicators

1. **RSI (Relative Strength Index)** — Measures momentum. Below 30 = oversold (buy signal), above 70 = overbought (sell signal)
2. **MACD** — Trend following. Bullish when histogram turns positive, bearish when negative
3. **SMA (20, 50, 200)** — Moving averages showing short, medium, and long-term trends
4. **EMA (12, 26)** — Faster-responding exponential moving averages
5. **Bollinger Bands** — Volatility bands. Price bouncing off lower band = potential buy
6. **ATR** — Average True Range measuring volatility, used for stop-loss calculation
7. **Stochastic Oscillator** — Momentum indicator with %K and %D crossovers
8. **Volume Analysis** — Compares current volume to 20-day average. Spikes confirm moves
9. **52-Week Position** — Where price sits in its yearly range
10. **Golden/Death Cross** — SMA 50/200 crossovers signaling major trend changes

### Signal Logic

- **BUY** — 3+ bullish indicators agree (configurable)
- **SELL** — 3+ bearish indicators agree
- **HOLD** — Insufficient confluence

### Confidence Scoring

- **80-100** — Strong signal (green)
- **65-79** — Moderate signal (yellow)
- **50-64** — Weak signal (orange)
- **0-49** — No actionable signal (grey)

---

## Running Tests

```bash
cd stockpulse
pytest tests/ -v
```

Tests use mocked data and require no API calls.

---

## FAQ

**Q: Is this free?**
A: Yes. StockPulse uses Yahoo Finance (free, no API key). WhatsApp via CallMeBot is also free.

**Q: How delayed is the data?**
A: Yahoo Finance data has approximately 15-minute delay during market hours.

**Q: Can I add any stock?**
A: Any stock symbol available on Yahoo Finance. US stocks, international stocks, ETFs, etc.

**Q: Will it work outside market hours?**
A: Yes. It shows the last available data with a "Market Closed" indicator.

**Q: How do I add Alpha Vantage as fallback?**
A: Get a free API key at https://www.alphavantage.co/support/#api-key and add it to `.env`.

---

## Disclaimer

DISCLAIMER: StockPulse is a technical analysis tool for educational and informational purposes only. It does NOT constitute financial advice, investment recommendations, or solicitations to buy or sell securities. Technical indicators are based on historical data and mathematical formulas — they cannot predict future market movements. Past performance does not guarantee future results. Always conduct your own research and consult with a qualified financial advisor before making any investment decisions. The creators of StockPulse assume no liability for any financial losses incurred through the use of this application.

---

## License

MIT License. See LICENSE file for details.
