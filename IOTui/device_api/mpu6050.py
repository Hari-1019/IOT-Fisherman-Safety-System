from firebase_admin import db

def get_latest_accelerometer():
    ref = db.reference("accelerometer")
    data = ref.get()
    if not data:
        return None
    return int(data.get("timestamp", 0)), {
        "x": data.get("x"),
        "y": data.get("y"),
        "z": data.get("z"),
        "magnitude": data.get("magnitude")
    }
