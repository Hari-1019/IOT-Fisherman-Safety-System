from firebase_admin import db

def get_latest_alerts():
    ref = db.reference("alerts")
    entry = ref.get()
    if not entry:
        return {
            "latest": None,
            "button": None,
            "geofence": None,
        }
    return {
        "latest": entry.get("latest"),
        "button": entry.get("button"),
        "geofence": entry.get("geofence"),
    }
