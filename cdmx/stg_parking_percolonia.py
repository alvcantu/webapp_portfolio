import json
import csv
from collections import defaultdict
from math import radians, sin, cos, sqrt, atan2

# Paths to the input files
parking_geojson_path = '/home/alvcantu/cdmx/infraestructura-de-parquimetros.json'
bikes_path = '/home/alvcantu/cdmx/estaciones_ecobici_sist_anterior.csv'
output_csv_path = '/home/alvcantu/cdmx/stg_parking_percolonia.csv'

# Haversine formula to calculate distance between two lat-long points
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in kilometers
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# Load bike station data and group by colonia
def load_bike_stations(csv_path):
    bike_stations = defaultdict(list)
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            colonia = row['colonia'].upper()
            lat = float(row['latitud'])
            lon = float(row['longitud'])
            bike_stations[colonia].append((lat, lon))
    return bike_stations

# Find the closest colonia for given coordinates
def find_closest_colonia(lat, lon, bike_stations):
    min_distance = float('inf')
    closest_colonia = None
    for colonia, coords in bike_stations.items():
        for coord_lat, coord_lon in coords:
            distance = haversine(lat, lon, coord_lat, coord_lon)
            if distance < min_distance:
                min_distance = distance
                closest_colonia = colonia
    return closest_colonia

# Count rows per colonia from GeoJSON data
def count_colonia_rows(parking_geojson_path, bike_stations):
    parking_counts = defaultdict(int)
    with open(parking_geojson_path, 'r', encoding='utf-8') as geojson_file:
        data = json.load(geojson_file)
        for feature in data['features']:
            lat = float(feature['geometry']['coordinates'][1])
            lon = float(feature['geometry']['coordinates'][0])
            closest_colonia = find_closest_colonia(lat, lon, bike_stations)
            if closest_colonia:
                parking_counts[closest_colonia] += 1
    return parking_counts

# Load data and perform the counts
bike_stations = load_bike_stations(bikes_path)
parking_counts = count_colonia_rows(parking_geojson_path, bike_stations)

# Write results to a CSV file
with open(output_csv_path, 'w', encoding='utf-8', newline='') as csvfile:
    csvwriter = csv.writer(csvfile)
    # Write header
    csvwriter.writerow(['colonia', 'parking_count'])
    # Write data rows
    for colonia, parking_count in parking_counts.items():
        csvwriter.writerow([colonia, parking_count])

print(f"Output written to {output_csv_path}")
