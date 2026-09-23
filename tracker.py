source = "https://api.data.gov.my/gtfs-realtime/vehicle-position/prasarana/?category="

from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import MessageToDict
import requests
import time
import pandas as pd

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
    spamreader = pd.read_csv('gtfs_data/trips.txt')
    #print(dir(spamreader))
    trip_ids = spamreader["trip_id"]
    route_ids = spamreader["route_id"]
    trip_headsigns = spamreader["trip_headsign"]
    service_ids = spamreader["service_id"]
    shape_ids = spamreader["shape_id"]
    no = 0
    for trip in trip_ids:
       trips[trip] = {"route_id": int(route_ids[no]), "trip_headsign": trip_headsigns[no], "service_id": int(service_ids[no]), "shape_id": int(shape_ids[no])}
       no = no + 1
    return trips

def get_routes():
    routes = {}
    spamreader = pd.read_csv('gtfs_data/routes.txt')
    route_ids = spamreader["route_id"]
    route_long_names = spamreader["route_long_name"]
    no = 0
    for route in route_ids:
        routes[route] = {"route_name": route_long_names[no], "route_id": route}
        no = no + 1
    return routes

def get_stops():
    stops = {}
    spamreader = pd.read_csv('gtfs_data/stops.txt')
    stop_ids = spamreader["stop_id"]
    stop_codes = spamreader["stop_code"]
    stop_names = spamreader["stop_name"]
    stop_lats = spamreader["stop_lat"]
    stop_lons = spamreader["stop_lon"]
    no = 0
    for stop in stop_ids:
        stops[stop] = {"stop_code": stop_codes[no], "stop_ids": int(stop_ids[no]), "stop_name": stop_names[no], "stop_lat": float(stop_lats[no]), "stop_lon": float(stop_lons[no])}
        no = no + 1
    return stops

def get_stop_times():
    stop_times = {}
    spamreader = pd.read_csv('gtfs_data/stop_times.txt')
    trip_ids = spamreader["trip_id"]
    arrival_times = spamreader["arrival_time"]
    stop_ids = spamreader["stop_id"]
    stop_sequences = spamreader["stop_sequence"]
    stop_headsigns = spamreader["stop_headsign"]
    no = 0
    for trip_id in trip_ids:
        if not stop_times.get(trip_id):
            stop_times[trip_id] = [{"trip_id": trip_ids[no], "arrival_time": arrival_times[no], "stop_id": int(stop_ids[no]), "stop_sequence": int(stop_sequences[no]), "stop_headsign": stop_headsigns[no]}]
        else:
            stop_times[trip_id].append({"trip_id": trip_ids[no], "arrival_time": arrival_times[no], "stop_id": int(stop_ids[no]), "stop_sequence": int(stop_sequences[no]), "stop_headsign": stop_headsigns[no]})
        no = no + 1
    return stop_times

def get_stop_served_routes():
    all_stops = get_stops()
    full_data = get_stop_times()
    all_trips = get_trips()
    all_routes = get_routes()
    stop_times_lookup_dict = {}
    all_stop_ids = []
    stop_served_routes = {}
    for stop_id in all_stops:
        all_stop_ids.append(stop_id)
    for stop_times in full_data:
        temp_array = full_data[stop_times]
        stop_times_lookup_dict[stop_times] = {item["stop_id"]: item for item in temp_array}
    for each_stop in all_stop_ids:
        temp_holding = []
        for stop_times in full_data:
            result = stop_times_lookup_dict[stop_times]
            if each_stop not in result:
                pass
            else:
                temp_holding.append(result[each_stop]["trip_id"])
        used_route_ids = []
        for holds in temp_holding:
            route_id = all_trips[holds]["route_id"]
            if route_id in used_route_ids:
                pass
            else:
                used_route_ids.append(route_id)
                route = all_routes[route_id]
                if not stop_served_routes.get(each_stop):
                    stop_served_routes[each_stop] = [route]
                else:
                    stop_served_routes[each_stop].append(route)
    return stop_served_routes

def get_agency():
    agency = {}
    spamreader = pd.read_csv('gtfs_data/agency.txt')
    agency_name = spamreader["agency_name"][0]
    agency_url = spamreader["agency_url"][0]
    agency_phone = spamreader["agency_phone"][0]
    agency_timezone = spamreader["agency_timezone"][0]
    agency_lang = spamreader["agency_lang"][0]
    agency_id = spamreader["agency_id"][0]

    agency["agency_name"] = agency_name
    agency["agency_url"] = agency_url
    agency["agency_phone"] = agency_phone
    agency["agency_timezone"] = agency_timezone
    agency["agency_lang"] = agency_lang
    agency["agency_id"] = agency_id

    return agency
