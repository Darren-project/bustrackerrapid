import tracker
import time

from flask import Flask
from flask_cors import CORS, cross_origin
from werkzeug.middleware.proxy_fix import ProxyFix


app = Flask(__name__)
cors = CORS(app)

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

last_bus_time = None
last_bus_data = {}

@app.route("/bus")
def buses():
    global last_bus_time
    global last_bus_data
    if last_bus_time is None:
        pass
    elif  not ((time.time() - last_bus_time) >= 30):
        print("Serving old Bus Location")
        return last_bus_data
    print("Getting Latest Bus Location")
    last_bus_time = time.time()
    bus = tracker.get_bus("rapid-bus-penang")
    trip = tracker.get_trips()
    base = {
        "type": "FeatureCollection",
        "features": [
        ]
    }
    for b in bus:
        #print(b)
        tripdata = ''
        if trip.get(b["trip"]["tripId"]):
            tripdata = trip[b["trip"]["tripId"]]['trip_headsign']
            route_id = trip[b["trip"]["tripId"]]['route_id']
        else:
            tripdata = "No data"
            route_id = None
        base["features"].append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [b["position"]["longitude"], b["position"]["latitude"]]
            },
            "properties": {
                "id": b['vehicle']["licensePlate"],
                "trip_id": b["trip"]["tripId"],
                "route_id": route_id,
                "tooltip": f"Bus {b['vehicle']['licensePlate']} {tripdata}",
                "speed": b["position"]["speed"]
            }
        })
    last_bus_data = base
    return base

@app.route("/routes")
def routes():
    return tracker.get_routes()

@app.route("/trips")
def trips():
    return tracker.get_trips()


@app.route("/stops")
def stops():
    return tracker.get_stops()

@app.route("/stop_times")
def stop_times():
     return tracker.get_stop_times()

@app.route("/stops_served_routes")
def stops_served_routes():
    return tracker.get_stop_served_routes()

@app.route("/agency")
def agency():
    return tracker.get_agency()

if __name__ == "__main__":
  app.run(port=5440, host="0.0.0.0")
