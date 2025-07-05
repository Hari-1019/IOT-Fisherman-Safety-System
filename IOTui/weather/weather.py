import os
import time
import math
import requests
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, db

# === Firebase Initialization ===


# === In-memory cache ===
device_weather_state = {}

def get_cell_key(lat, lon):
    """Return a grid cell ID for the given lat/lon, approx 5x5km resolution."""
    lat_step = 5.0 / 111.0  # ~5km
    cell_lat = math.floor(lat / lat_step) * lat_step
    lon_step = 5.0 / (111.32 * math.cos(math.radians(lat)))
    cell_lon = math.floor(lon / lon_step) * lon_step
    return f"{round(cell_lat, 5)}_{round(cell_lon, 5)}".replace('.', '_')


def fetch_weather(lat, lon):
    """Call the Open-Meteo marine API and return JSON."""
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": [
            "wave_height",
            "wave_direction",
            "wave_period",
            "ocean_current_velocity",
            "ocean_current_direction"
        ],
        "models": "best_match",
        "forecast_days": 1,
        "timezone": "auto"
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


def get_current_hour_data(api_json):
    """Extract only the data for the current hour from the API JSON."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:00')
    times = api_json['hourly']['time']
    if now not in times:
        return None
    i = times.index(now)
    return {
        key: api_json['hourly'][key][i]
        for key in api_json['hourly']
        if key != 'time'
    }


def get_or_fetch_weather(lat, lon, device_id):
    """
    Return current weather data for device.
    Cached if already fetched in the same cell in past 1 hour.
    Saves to Firebase at: weatherdata/data
    """
    now_ts = int(time.time())
    cell = get_cell_key(lat, lon)
    state = device_weather_state.get(device_id, {})

    if (
        state.get('cell') == cell
        and state.get('time') is not None
        and (now_ts - state.get('time')) < 3600
    ):
        return cell, state['data']

    # Fetch fresh data from API
    try:
        full_api = fetch_weather(lat, lon)
        current_data = get_current_hour_data(full_api)
    except Exception as e:
        print(f"❌ Failed to fetch weather: {e}")
        return cell, None

    if current_data:
        # Cache locally
        device_weather_state[device_id] = {
            'cell': cell,
            'time': now_ts,
            'data': current_data
        }

        # ✅ Save to Firebase
        try:
            ref = db.reference('weatherdata/data')
            ref.push({
                'device_id': device_id,
                'timestamp': now_ts,
                'lat': lat,
                'lon': lon,
                'cell': cell,
                'data': current_data
            })
            print(f"✅ Saved weather for {device_id} at cell {cell}")
        except Exception as e:
            print(f"❌ Failed to save to Firebase: {e}")

    return cell, current_data
