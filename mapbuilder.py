import requests
import zipfile
import os
import pandas as pd
import folium

from folium.plugins import MiniMap
from folium.utilities import JsCode
from folium.plugins import Realtime
from folium.plugins import Search

gtfs_url = "https://api.data.gov.my/gtfs-static/prasarana?category=rapid-bus-penang"
gtfs_zip_file = "gtfs_data.zip"
extracted_folder = "gtfs_data"

print("Downloading GTFS data...")

response = requests.get(gtfs_url)
if response.status_code == 200:
    with open(gtfs_zip_file, "wb") as file:
        file.write(response.content)
else:
    exit()

print("Extracting GTFS data...")
with zipfile.ZipFile(gtfs_zip_file, "r") as zip_ref:
    zip_ref.extractall(extracted_folder)

print("Creating map...")
stops = pd.read_csv(os.path.join(extracted_folder, "stops.txt"))
shapes = pd.read_csv(os.path.join(extracted_folder, "shapes.txt"))

map_center = [stops.iloc[0]['stop_lat'], stops.iloc[0]['stop_lon']]
transit_map = folium.Map(location=map_center, zoom_start=13)



stations = folium.FeatureGroup(name="Stations")

for _, stop in stops.iterrows():
    folium.Marker(
        [stop['stop_lat'], stop['stop_lon']],
        tooltip=f"{stop['stop_name']}",
        icon=folium.Icon(
            icon="sign-hanging",
            prefix="fa",
            icon_color="white"
        )
    ).add_to(stations)

stations.add_to(transit_map)

shape_groups = shapes.groupby("shape_id")



for shape_id, shape_points in shape_groups:
    route_coordinates = shape_points.sort_values("shape_pt_sequence")[["shape_pt_lat", "shape_pt_lon"]].values
    folium.PolyLine(
        locations=route_coordinates,
        weight=3,
        opacity=0.8,
    ).add_to(transit_map)

rt = Realtime("https://rapidbustrackerapi.darrenmc.dev",
              point_to_layer=JsCode("function(feature, latlng) { return L.marker(latlng).bindTooltip('<div>' + feature.properties.tooltip + '</div>').setIcon(L.AwesomeMarkers.icon({'markerColor': 'blue','iconColor': 'white','icon': 'bus','prefix': 'fa','extraClasses': 'fa-rotate-0'})); }"),
              interval=10000)

rt.add_to(transit_map)

folium.plugins.LocateControl(auto_start=True).add_to(transit_map)

MiniMap().add_to(transit_map)



print("Saving map...")
transit_map.save("transit_map.html")
