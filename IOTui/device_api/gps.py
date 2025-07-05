from firebase_admin import db

def get_latest_gps():
    ref = db.reference("gps")
    data = ref.get()
    if not data:
        return None
    lat = data.get("latitude")
    lon = data.get("longitude")
    ts = data.get("timestamp", 0)
    if lat is None or lon is None:
        return None
    return ts, lat, lon
