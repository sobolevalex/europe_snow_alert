from __future__ import annotations

import json
import logging
import os
from datetime import date, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import NamedTuple

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = Path(__file__).resolve().parent
DEFAULT_CITIES_PATH = CONFIG_DIR / "cities.json"
DEFAULT_LOG_PATH = BASE_DIR / "snow_alert.log"

load_dotenv(BASE_DIR / ".env")


def setup_logger() -> logging.Logger:
    log_path = Path(os.environ.get("LOG_FILE_PATH", DEFAULT_LOG_PATH))
    logger = logging.getLogger("europe_snow_alert")

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Console Output (INFO and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. File Output (DEBUG and above with rotation up to 5 MB, keeping 3 backups)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()
LOG_FILE_PATH = Path(os.environ.get("LOG_FILE_PATH", DEFAULT_LOG_PATH))


class City(NamedTuple):
    name: str
    latitude: float
    longitude: float
    country: str = ""


def load_cities(config_path: str | Path | None = None) -> list[City]:
    path = Path(config_path) if config_path else Path(os.environ.get("CITIES_CONFIG_PATH", DEFAULT_CITIES_PATH))
    logger.debug("Loading cities from %s", path)
    with open(path, "r", encoding="utf-8") as f:
        raw_cities = json.load(f)

    cities = [
        City(
            name=c["name"],
            latitude=float(c["latitude"]),
            longitude=float(c["longitude"]),
            country=c.get("country", ""),
        )
        for c in raw_cities
    ]
    logger.debug("Successfully loaded %d cities", len(cities))
    return cities


# Загружаем список городов из конфигурационного файла
CITIES = load_cities()


def get_upcoming_fri_sat() -> tuple[str, str]:
    today = date.today()
    # weekday(): Пн=0 ... Пт=4, Сб=5, Вс=6
    # Если сегодня суббота (5), берем следующую неделю; если Пт (4) — текущую Пт и Сб
    days_to_fri = (4 - today.weekday()) % 7
    fri = today + timedelta(days=days_to_fri)
    sat = fri + timedelta(days=1)
    logger.debug("Upcoming weekend calculated: Fri=%s, Sat=%s (from today=%s)", fri, sat, today)
    return fri.isoformat(), sat.isoformat()


def check_snow(cities: list[City] | None = None) -> tuple[list[str], str, str]:
    target_cities = cities if cities is not None else CITIES
    fri_str, sat_str = get_upcoming_fri_sat()
    lats = ",".join(str(c.latitude) for c in target_cities)
    lons = ",".join(str(c.longitude) for c in target_cities)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lats,
        "longitude": lons,
        "daily": "snowfall_sum,temperature_2m_max",
        "start_date": fri_str,
        "end_date": sat_str,
        "timezone": "auto",
    }

    logger.info("Querying Open-Meteo weather API for %d cities (%s — %s)...", len(target_cities), fri_str, sat_str)
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        logger.info("Open-Meteo response received successfully (HTTP %d)", resp.status_code)
    except requests.RequestException as e:
        logger.error("Failed to fetch weather from Open-Meteo: %s", e)
        raise

    # Если город 1, API возвращает dict, если несколько — list[dict]
    results = data if isinstance(data, list) else [data]
    snowy_cities = []

    for city, city_data in zip(target_cities, results):
        daily = city_data.get("daily", {})
        snow = daily.get("snowfall_sum", [0.0, 0.0])
        temps = daily.get("temperature_2m_max", [None, None])

        fri_snow = (snow[0] or 0.0) if len(snow) > 0 and snow[0] is not None else 0.0
        sat_snow = (snow[1] or 0.0) if len(snow) > 1 and snow[1] is not None else 0.0
        fri_temp = temps[0] if len(temps) > 0 else None
        sat_temp = temps[1] if len(temps) > 1 else None

        # Порог >= 1 см и температура ниже 0°C отсекают мокрый снег и осадки при плюсовой температуре
        fri_snow_valid = fri_snow >= 1 and fri_temp is not None and fri_temp < 0
        sat_snow_valid = sat_snow >= 1 and sat_temp is not None and sat_temp < 0

        if fri_snow_valid or sat_snow_valid:
            location_label = f"{city.name} ({city.country})" if city.country else city.name
            entry = f"• <b>{location_label}</b>: Пт {fri_snow:.1f} см ({fri_temp}°C) | Сб {sat_snow:.1f} см ({sat_temp}°C)"
            snowy_cities.append(entry)
            logger.debug(
                "Snow alert match: %s [Fri: %.1f cm (%s°C), Sat: %.1f cm (%s°C)]",
                location_label,
                fri_snow,
                fri_temp,
                sat_snow,
                sat_temp,
            )

    logger.info("Snow check completed. %d of %d cities expect snow.", len(snowy_cities), len(target_cities))
    return snowy_cities, fri_str, sat_str


def send_telegram(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        err_msg = "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing in .env"
        logger.error(err_msg)
        raise ValueError(err_msg)

    masked_token = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else "***"
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    # Telegram has a 4096 character limit per message
    max_length = 4000
    chunks = [text[i:i + max_length] for i in range(0, len(text), max_length)]

    logger.info("Sending message to Telegram (chat_id=%s, bot=%s, %d chunk(s))...", chat_id, masked_token, len(chunks))

    for idx, chunk in enumerate(chunks, start=1):
        if len(chunks) > 1:
            logger.info("Sending Telegram chunk %d/%d (%d chars)...", idx, len(chunks), len(chunk))

        try:
            resp = requests.post(
                url,
                json={"chat_id": chat_id, "text": chunk, "parse_mode": "HTML"},
                timeout=(10, 30),  # (connect timeout: 10s, read timeout: 30s)
            )
            resp.raise_for_status()
            logger.info("Telegram chunk %d/%d delivered successfully (HTTP %d)", idx, len(chunks), resp.status_code)
        except requests.exceptions.Timeout as e:
            logger.error("Timeout while communicating with Telegram API: %s", e)
            raise
        except requests.exceptions.RequestException as e:
            logger.error("Error sending Telegram message: %s", e)
            raise

    logger.info("All Telegram message chunks delivered successfully!")


if __name__ == "__main__":
    logger.info("Starting Europe Snow Alert (logging to file: %s)", LOG_FILE_PATH)
    cities, fri, sat = check_snow()
    if cities:
        logger.info("Formatting Telegram alert for %d cities with snow forecast for %s — %s...", len(cities), fri, sat)
        msg = f"❄️ <b>Прогноз снега на выходные ({fri} — {sat}):</b>\n\n" + "\n".join(cities)
        send_telegram(msg)
    else:
        logger.info("No snow expected for %s — %s across all %d cities.", fri, sat, len(CITIES))
        print(f"На {fri} — {sat} снега в списке городов не ожидается.")