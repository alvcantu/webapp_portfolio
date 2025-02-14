import json
import csv
from collections import defaultdict
from math import radians, sin, cos, sqrt, atan2 

# Paths to the input files
bike_csv_path = '/home/alvcantu/cdmx/estaciones_ecobici_sist_anterior.csv'
output_csv_path = "cdmx/stg_area_bikestations_percolonia.csv"

# Function to count bike stations by colonia
def count_bike_stations(csv_path):
    bike_stations = defaultdict(int)
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            colonia = row['colonia'].upper()  # Ensure consistency in case
            bike_stations[colonia] += 1
    return bike_stations

# Haversine formula to calculate distance between two lat-long points
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in kilometers
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# Function to calculate the area of each colonia based on coordinates
def calculate_colonia_area(csv_path):
    colonia_coords = defaultdict(list)
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            colonia = row['colonia'].upper()
            lat = float(row['latitud'])
            lon = float(row['longitud'])
            colonia_coords[colonia].append((lat, lon))

    colonia_areas = {}
    for colonia, coords in colonia_coords.items():
        if len(coords) < 2:
            colonia_areas[colonia] = 0.0  # No area can be calculated with less than 2 points
            continue

        # Calculate the perimeter of the colonia using consecutive points
        area = 0.0
        for i in range(len(coords)):
            lat1, lon1 = coords[i]
            lat2, lon2 = coords[(i + 1) % len(coords)]  # Wrap around to the first point
            area += haversine(lat1, lon1, lat2, lon2)

        colonia_areas[colonia] = area  # Approximate area in km^2

    return colonia_areas

bike_stations_per_colonia = count_bike_stations(bike_csv_path)
colonia_area = calculate_colonia_area(bike_csv_path)

# Write results to a CSV file
with open(output_csv_path, 'w', encoding='utf-8', newline='') as csvfile:
    csvwriter = csv.writer(csvfile)
    # Write header
    csvwriter.writerow(['colonia', 'area_km2', 'bike_stations'])
    # Write data rows
    for colonia in bike_stations_per_colonia:
        area = colonia_area.get(colonia, 0.0)
        stations = bike_stations_per_colonia[colonia]
        csvwriter.writerow([colonia, area, stations])

print(f"Output written to {output_csv_path}")

