from firebase_admin import db

def get_latest_button():
    ref = db.reference("alerts")
    data = ref.get()
    if not data:
        return None
    return int(data.get("timestamp", 0)), data.get("button") or False
