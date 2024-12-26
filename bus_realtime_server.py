import tracker

from flask import Flask
from flask_cors import CORS, cross_origin

app = Flask(__name__)
cors = CORS(app)

@app.route("/")
def realtime():
    bus = tracker.get_bus("rapid-bus-penang")
    trip = tracker.get_trips()
    base = {
        "type": "FeatureCollection",
        "features": [
        ]
    }
    for b in bus:
        tripdata = ''
        if trip.get(b["trip"]["tripId"]):
            tripdata = trip[b["trip"]["tripId"]]
        else: 
            tripdata = "No data"
        base["features"].append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [b["position"]["longitude"], b["position"]["latitude"]]
            },
            "properties": {
                "id": b['vehicle']["licensePlate"],
                "trip_id": b["trip"]["tripId"],
                "tooltip": f"Bus {b['vehicle']['licensePlate']} \n {tripdata}"
            }
        })
    return base


if __name__ == "__main__":
  app.run(port=5000)