# Europe Snow Alert ❄️

Automated alert service that monitors weather forecasts across 60+ European cities and ski destinations for upcoming weekends (Friday and Saturday). When snowfall is predicted (≥ 1 cm) with sub-zero temperatures (< 0°C), it sends an instant notification to a Telegram chat with snowfall amounts and maximum temperatures.

---

## Features

- **Weekend Focus**: Automatically targets the upcoming Friday and Saturday.
- **Batch Weather Queries**: Fetches multi-location forecasts in a single request via the free [Open-Meteo API](https://open-meteo.com/).
- **Configurable Locations**: External [cities.json](europe_snow_alert/cities.json) with 60+ European capitals, ski resorts, and alpine hubs.
- **Telegram Notifications**: Clean HTML alerts formatted and delivered directly to your Telegram bot.
- **Dual Logging**: Real-time console logs and rotating file logs (`snow_alert.log`).

---

## Project Structure

```text
europe_snow_alert/
├── .env                  # Secrets (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
├── .env.example          # Template for environment variables
├── .gitignore            # Git ignore configuration
├── requirements.txt      # Python dependencies
├── snow_alert.log        # Generated runtime log file
└── europe_snow_alert/
    ├── __init__.py       # Package definition
    ├── cities.json       # European cities database (lat/lon/country)
    └── main.py           # Core forecasting & notification script
```

---

## Quickstart

### 1. Set Up Environment

Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Telegram Credentials

Copy `.env.example` to `.env` and fill in your Telegram details:

```bash
cp .env.example .env
```

Edit `.env`:
```env
TELEGRAM_BOT_TOKEN="your_bot_token_from_botfather"
TELEGRAM_CHAT_ID="your_telegram_chat_id"
```

### 3. Run the Alert

```bash
python europe_snow_alert/main.py
```

---

## Configuration

### Cities Configuration (`cities.json`)
You can add, remove, or customize monitored locations in `europe_snow_alert/cities.json`:

```json
[
  {
    "name": "Инсбрук",
    "country": "Австрия",
    "latitude": 47.2692,
    "longitude": 11.4041
  }
]
```

### Environment Variables
- `TELEGRAM_BOT_TOKEN`: Telegram bot token from [@BotFather](https://t.me/BotFather).
- `TELEGRAM_CHAT_ID`: Telegram chat or channel ID to receive alerts.
- `CITIES_CONFIG_PATH`: *(Optional)* Path to a custom JSON cities file.
- `LOG_FILE_PATH`: *(Optional)* Custom location for `snow_alert.log`.

---

## License

MIT License

