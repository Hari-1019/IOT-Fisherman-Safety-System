from firebase_admin import db

def get_latest_sensor():
    ref = db.reference("sensor")
    data = ref.get()
    if not data:
        return None
    return int(data.get("timestamp", 0)), data.get("temperature"), data.get("humidity")
