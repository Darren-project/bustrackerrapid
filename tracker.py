source = "https://api.data.gov.my/gtfs-realtime/vehicle-position/prasarana/?category="

from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict
import requests
import csv
import time

def get_bus(category):
    feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get(source + category)
    try:
        data = response.json()
        print("Request was throttled. Expected available in", data["detail"].replace("Request was throttled. Expected available in ", "").replace(" seconds.", ""), "seconds.")
        timets = int(data["detail"].replace("Request was throttled. Expected available in ", "").replace(" seconds.", ""))
        time.sleep(timets + 1)
        try:
            response = requests.get(source + category)
        except:
            return []
    except ValueError:
        pass
    feed.ParseFromString(response.content)
    return [MessageToDict(entity.vehicle) for entity in feed.entity]

def get_trips():
    trips = {}
    with open('gtfs_data/trips.txt', newline='') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
        for row in spamreader:
            if len(row) == 1:
                continue
            trips[row[2]] = row[3]
    return trips

def parser(raw):
    buses = []
    for bus in raw:
        buses.append([bus['vehicle']['licensePlate'], bus['position']['latitude'], bus['position']['longitude'], bus["trip"]["tripId"]])
    return buses