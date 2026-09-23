import requests
import zipfile
import os
import pandas as pd
import folium
import tracker
import sys

from folium.plugins import MiniMap
from folium.utilities import JsCode
from folium.plugins import Realtime
from folium.plugins import Search
from folium.plugins import LocateControl
from branca.element import Element
from folium.features import GeoJson

gtfs_url = "https://api.data.gov.my/gtfs-static/prasarana?category=rapid-bus-penang"
gtfs_zip_file = "gtfs_data.zip"
extracted_folder = "gtfs_data"
server_url = sys.argv[1]

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

agency_info = tracker.get_agency()

print("Creating map...")
stops = pd.read_csv(os.path.join(extracted_folder, "stops.txt"))
shapes = pd.read_csv(os.path.join(extracted_folder, "shapes.txt"))

map_center = [stops.iloc[0]['stop_lat'], stops.iloc[0]['stop_lon']]
transit_map = folium.Map(tiles="https://mt0.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
                         attr=f"""
                         Imagery ©2026 Airbus, Maxar Technologies, Map data ©2026 Google
                         <br> Data from <a href='https://data.gov.my'>data.gov.my <img src='https://developer.data.gov.my/favicon.ico' style='height: 17px; width: 17px;'></img></a>
                         on behalf of <a href='{agency_info["agency_url"]}'> {agency_info["agency_name"]} <img src='{agency_info["agency_url"]}/favicon.ico' style='height: 45px; width: 45px;'></img></a>
                         """,
                         location=map_center,
                         zoom_start=13)

maps_stop_route = tracker.get_stop_served_routes()

mapped_stop_route = {}

for stop in maps_stop_route:
    mapped_stop_route[stop] = ', '.join(route['route_name'] for route in  maps_stop_route[stop])

stations = folium.FeatureGroup(name="Stations")

for _, stop in stops.iterrows():
    folium.Marker(
        [stop['stop_lat'], stop['stop_lon']],
        tooltip=f"{stop['stop_name']} <br> Routes: " + mapped_stop_route[stop['stop_id']],
        icon=folium.Icon(
            icon="sign-hanging",
            prefix="fa",
            icon_color="white"
        ),
        stop_name=stop['stop_name'],
        stop_code=stop['stop_code'],
        stop_id=stop['stop_id'],
        stop_routes=mapped_stop_route[stop['stop_id']]
    ).add_to(stations)

stations.add_to(transit_map)

shape_groups = shapes.groupby("shape_id")

shape_no = 0

shape_fg = folium.FeatureGroup(name="Shapes")

shape_id_to_cord = {}

shape_id_to_leaflet_ids = {}

for shape_id, shape_points in shape_groups:
    route_coordinates = shape_points.sort_values("shape_pt_sequence")[["shape_pt_lat", "shape_pt_lon"]].values
    line = folium.PolyLine(
        locations=route_coordinates,
        weight=3,
        opacity=0.8,
        shape_id = str(shape_id)
    ).add_to(shape_fg)
    if not shape_id_to_leaflet_ids.get(str(shape_id)):
        shape_id_to_leaflet_ids[str(shape_id)] = line.get_name()
    if not shape_id_to_cord.get(str(shape_id)):
        shape_id_to_cord[str(shape_id)] = []
        shape_id_to_cord[str(shape_id)].append(route_coordinates.tolist())
    else:
        shape_id_to_cord[str(shape_id)].append(route_coordinates.tolist())
    shape_no = shape_no + 1

shape_fg.add_to(transit_map)

#print(str(shape_id_to_cord))

init_code = f"""
window.app_name = "RapidBusTracker"
window.app_log_color = "blue"

window.transportinfo = {{}}
window.following_bus = undefined
window.following_bus_lastloc = undefined

window.shapeid_to_cords = {shape_id_to_cord}
window.shape_id_to_leaflet_ids = {shape_id_to_leaflet_ids}
window.stations = {{}}

transportinfo.routes = {{}}
transportinfo.trips = {{}}
transportinfo.stops = {{}}
transportinfo.stop_times = {{}}
transportinfo.stops_served_routes = {{}}
transportinfo.agency = {{}}

let fetchloggroup = _loghelper_internal.console_group_logs("group", undefined, "Fetching live data from server")


Promise.all(
    Object.keys(transportinfo).map(async endpoint => {{
        try {{
            let response = await fetch("{server_url}" + "/" + endpoint)
            transportinfo[endpoint] = await response.json()
        }} catch (error) {{
            _loghelper_internal.console_group_logs("error", fetchloggroup, "Failed to fetch transportinfo." + endpoint, error)
        }} finally {{
            _loghelper_internal.console_group_logs("info", fetchloggroup, "Fetched transportinfo." + endpoint)
        }}
    }})
).finally(() => {{
    _loghelper_internal.console_group_logs("groupEnd", fetchloggroup)
}})

function waitForMap() {{
    if (typeof {transit_map.get_name()} !== "undefined") {{
        window.transportmap = {transit_map.get_name()};
        console.debug("Found Map Object")
        return;
    }}

    setTimeout(waitForMap, 100);
}}

function waitForShapes() {{
    if (typeof {shape_fg.get_name()} !== "undefined") {{
        window.transportshapes = {shape_fg.get_name()}
        console.debug("Found Shapes Object")
        return
    }}

    setTimeout(waitForShapes, 100)
}}

function waitForStations() {{
     if (typeof {stations.get_name()} !== "undefined") {{
         window.stations = {stations.get_name()}
         console.debug("Found Stations Object")
         return
     }}

     setTimeout(waitForStations, 100)
}}

setInterval(function() {{
  if(!following_bus || !following_bus_lastloc || !transportmap) {{ return }}
  if(following_bus.getLatLng() === following_bus_lastloc) {{ return  }}
  transportmap.panTo(following_bus.getLatLng(), {{animate: false}})
  window.following_bus_lastloc = following_bus.getLatLng()

}}, 500)


waitForMap();
waitForShapes();
waitForStations();
"""

transit_map.get_root().script.add_child(Element(init_code))

transit_map.add_js_link("MovingMarker", "https://ewoken.github.io/Leaflet.MovingMarker/MovingMarker.js")
transit_map.add_js_link("UsefullUtilsLogger", "https://cdn.jsdelivr.net/gh/Darren-project/useful-utils@main/javascript/logger.js")

print("Importing all leaflet Draw sdks")

leaflet_draw_imports = [
    {"name": "Base", "dest": "src/Leaflet.draw.js"},
    {"name": "Events", "dest": "src/Leaflet.Draw.Event.js"},
    {"name": "Toolbar", "dest": "src/Toolbar.js"},

    {"name": "GeometryUtil", "dest": "src/ext/GeometryUtil.js"},
    {"name": "LatLngUtil", "dest": "src/ext/LatLngUtil.js"},
    {"name": "LineUtil.Intersect", "dest": "src/ext/LineUtil.Intersect.js"},
    {"name": "Polygon.Intersect", "dest": "src/ext/Polygon.Intersect.js"},
    {"name": "Polyline.Intersect", "dest": "src/ext/Polyline.Intersect.js"},
    {"name": "TouchEvents", "dest": "src/ext/TouchEvents.js"},

    {"name": "DrawToolbar", "dest": "src/draw/DrawToolbar.js"},
    {"name": "Draw.Feature", "dest": "src/draw/handler/Draw.Feature.js"},
    {"name": "Draw.SimpleShape", "dest": "src/draw/handler/Draw.SimpleShape.js"},
    {"name": "Draw.Polyline", "dest": "src/draw/handler/Draw.Polyline.js"},
    {"name": "Draw.Marker", "dest": "src/draw/handler/Draw.Marker.js"},
    {"name": "Draw.Circle", "dest": "src/draw/handler/Draw.Circle.js"},
    {"name": "Draw.CircleMarker", "dest": "src/draw/handler/Draw.CircleMarker.js"},
    {"name": "Draw.Polygon", "dest": "src/draw/handler/Draw.Polygon.js"},
    {"name": "Draw.Rectangle", "dest": "src/draw/handler/Draw.Rectangle.js"},

    {"name": "EditToolbar", "dest": "src/edit/EditToolbar.js"},
    {"name": "EditToolbar.Edit", "dest": "src/edit/handler/EditToolbar.Edit.js"},
    {"name": "EditToolbar.Delete", "dest": "src/edit/handler/EditToolbar.Delete.js"},

    {"name": "Control.Draw", "dest": "src/Control.Draw.js"},

    {"name": "Edit.Poly", "dest": "src/edit/handler/Edit.Poly.js"},
    {"name": "Edit.SimpleShape", "dest": "src/edit/handler/Edit.SimpleShape.js"},
    {"name": "Edit.Rectangle", "dest": "src/edit/handler/Edit.Rectangle.js"},
    {"name": "Edit.Marker", "dest": "src/edit/handler/Edit.Marker.js"},
    {"name": "Edit.CircleMarker", "dest": "src/edit/handler/Edit.CircleMarker.js"},
    {"name": "Edit.Circle", "dest": "src/edit/handler/Edit.Circle.js"},
]

for sdk in leaflet_draw_imports:
    transit_map.add_js_link("LeafletDraw" + sdk["name"], "https://cdn.jsdelivr.net/gh/Leaflet/Leaflet.draw@master/" + sdk["dest"])
    print("Added ", sdk["dest"])

transit_map.add_js_link("LeafletGeoUtil", "https://cdn.jsdelivr.net/gh/makinacorpus/Leaflet.GeometryUtil@master/src/leaflet.geometryutil.js")

bus_rt_pt_layer_code = f"""
function(feature, latlng) {{
    //console.log(feature)
    let route = transportinfo.routes[feature.properties.route_id]
    if(!route) {{ route = 'not in service' }} else {{ route = route["route_name"] }}
    let marker = L.Marker.movingMarker([latlng], [1000], {{
      busLabel: feature.properties.tooltip + " " + route
    }}).bindTooltip('<div>' + feature.properties.tooltip + '</div>' + '<br>' + 'Route ' + route)
        .setIcon(L.AwesomeMarkers.icon({{'markerColor': 'blue','iconColor': 'white','icon': 'bus','prefix': 'fa','extraClasses': 'fa-rotate-0'}}))
        .on("click", function () {{
           if(following_bus === this){{
                let oldcssclasses = following_bus._icon.className
                let oldchangedcss = oldcssclasses.replace('awesome-marker-icon-red', 'awesome-marker-icon-blue')
                following_bus._icon.className = oldchangedcss
                following_bus = undefined
                following_bus_lastloc = undefined
           }} else {{
                if(following_bus) {{
                    let oldcssclasses = following_bus._icon.className
                    let oldchangedcss = oldcssclasses.replace('awesome-marker-icon-red', 'awesome-marker-icon-blue')
                    following_bus._icon.className = oldchangedcss
                    following_bus = undefined
                    following_bus_lastloc = undefined
                }}
                following_bus = this
                let cssclasses = following_bus._icon.className
                let changedcss = cssclasses.replace('awesome-marker-icon-blue', 'awesome-marker-icon-red')
                following_bus._icon.className = changedcss
                let currentzoom = transportmap.getZoom()
                let zoom = 16
                if (currentzoom > 16) {{
                    zoom = currentzoom
                }}
                transportmap.setView(following_bus.getLatLng(), zoom)
                following_bus_lastloc = following_bus.getLatLng()
          }}
        }});
        return marker
    }}
"""

bus_rt_up_code = f"""
function(feature, old) {{
   if(!old){{
     return
   }}
   let route = transportinfo.routes[feature.properties.route_id]
   if(!route) {{ route = 'not in service' }} else {{ route = route["route_name"] }}
   old.options.busLabel = feature.properties.tooltip + " " + route
   old.feature.properties = feature.properties
   old._tooltip._content = '<div>' + feature.properties.tooltip + '</div>' + '<br>' + 'Route ' + route
   let targetLng = feature.geometry.coordinates[0]
   let targetLat = feature.geometry.coordinates[1]
   let pos = old.getLatLng()
   let oldLat = pos.lat
   let oldLng = pos.lng
   if(oldLat === targetLat && oldLng === targetLng) {{
     return old
   }}
   let distance = pos.distanceTo([targetLat, targetLng])
   let speed = feature.properties.speed
   if(speed===0){{
    speed = 1
   }}
   let duration = (distance / speed) * 1000
   duration = Math.max(500, Math.min(duration, 5000))

   let trip_id = old.feature.properties.trip_id

   if(!transportinfo.trips[trip_id]) {{
    old.moveTo([targetLat, targetLng], [duration])
    return old
   }}

   let shapeId = transportinfo.trips[trip_id].shape_id
   let routeSection = null
   if(shapeId) {{
       let oldPosition = old.getLatLng();

       let shape = window[shape_id_to_leaflet_ids[shapeId]];

       let newPosition = L.latLng([targetLat, targetLng]);

       let from = L.GeometryUtil.locateOnLine(
            transportmap,
            shape,
            oldPosition
       );

        let to = L.GeometryUtil.locateOnLine(
            transportmap,
            shape,
            newPosition
        );

        routeSection = L.GeometryUtil.extract(
            transportmap,
            shape,
            from,
            to
        );
    }} else {{
        old.moveTo([targetLat, targetLng], [duration])
        return old
    }}
    let eachSetDuration = duration / routeSection.length
    let moves = []
    for(let set in routeSection) {{
        moves.push({{"duration": eachSetDuration, "move": routeSection[set]}})
    }}
    setTimeout(() => {{
        for(let move in moves) {{
            let actMove = moves[move]
            old.moveTo(actMove.move, actMove.duration)
        }}
    }}, 1)
   //console.log(duration)
   return old
}}
"""

buses = folium.map.FeatureGroup("Buses")

buses.add_to(transit_map)

bus_rt = Realtime(server_url + "/bus",
              container=buses,
              point_to_layer=JsCode(bus_rt_pt_layer_code),
              get_feature_id=JsCode("(f) => { return f.properties.id; }"),
              update_feature=JsCode(bus_rt_up_code),
              interval=5000)



bus_rt.add_to(transit_map)

bus_stand_search = Search(
    stations,
    geom_type="Point",
    placeholder="Search for a bus stand",
    search_label="stopName",
    search_zoom=16,
    collapsed=True
)

bus_stand_search.add_to(transit_map)

buses_search = Search(
     buses,
     geom_type="Point",
     placeholder="Search for a bus",
     search_label="busLabel",
     search_zoom=16,
     collapsed=True
)

buses_search.add_to(transit_map)

LocateControl().add_to(transit_map)

print("Saving map...")
transit_map.save("transit_map.html")
