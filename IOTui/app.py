import os
import threading
import time
from flask import Flask, jsonify, render_template, request
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv

from device_api.gps import get_latest_gps
from device_api.dht11 import get_latest_sensor
from device_api.mpu6050 import get_latest_accelerometer
from device_api.button import get_latest_button
from weather.weather import get_or_fetch_weather
from device_api.alerts import get_latest_alerts

load_dotenv()
app = Flask(__name__)

# Initialize Firebase once
cred = credentials.Certificate(os.getenv('FIREBASE_CRED_PATH'))
firebase_admin.initialize_app(cred, {
    'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
})

def worker():
    while True:
        for device in ['esp32_01']:
            g = get_latest_gps()
            d = get_latest_sensor()
            m = get_latest_accelerometer()
            b = get_latest_button()
            a = get_latest_alerts()

            if g:
                ts, lat, lon = g
                cell, wdata = get_or_fetch_weather(lat, lon, device)
                # You can optionally push combined snapshots here if needed
        time.sleep(2)

threading.Thread(target=worker, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/map_data')
def map_data():
    gps = get_latest_gps()
    dht = get_latest_sensor()
    mpu = get_latest_accelerometer()
    btn = get_latest_button()
    alerts = get_latest_alerts()  # Fetch all alerts

    lat = gps[1] if gps else None
    lon = gps[2] if gps else None
    ts = gps[0] if gps else 0

    cell, wdata = get_or_fetch_weather(lat, lon, "esp32_01") if lat and lon else (None, {})

    return jsonify({
        'timestamp': ts,
        'lat': lat,
        'lon': lon,
        'temperature': dht[1] if dht else None,
        'humidity': dht[2] if dht else None,
        'accel': mpu[1].get('x') if mpu else None,
        'accel_y': mpu[1].get('y') if mpu else None,
        'accel_z': mpu[1].get('z') if mpu else None,
        'magnitude': mpu[1].get('magnitude') if mpu else None,
        'button': btn[1] if btn else None,
        'alerts': alerts,   # Add all alerts here
        'weather': wdata or {}
    })



if __name__ == '__main__':
    app.run(debug=True)
