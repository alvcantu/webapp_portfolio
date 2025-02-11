import json
import csv
from collections import defaultdict

# Paths to the input files
parking_json_path = '/home/alvcantu/cdmx/infraestructura-de-parquimetros.json'
bike_csv_path = '/home/alvcantu/cdmx/estaciones_ecobici_sist_anterior.csv'

# Function to count bike stations by alcaldia
def count_bike_stations(csv_path):
    bike_stations = defaultdict(int)
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            alcaldia = row['alcaldia'].upper()  # Ensure consistency in case
            bike_stations[alcaldia] += 1
    return bike_stations

# Function to count parking spots by alcaldia
def count_parking_spots(json_path):
    parking_spots = defaultdict(int)
    with open(json_path, 'r', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        for feature in data['features']:
            alcaldia = feature['properties']['ALCALDIA'].upper()
            parking_spots[alcaldia] += 1
    return parking_spots

# Main function to process and output data
def main():
    bike_stations = count_bike_stations(bike_csv_path)
    parking_spots = count_parking_spots(parking_json_path)

    # Calculate ratio and prepare data for output
    results = []
    for alcaldia in set(list(bike_stations.keys()) + list(parking_spots.keys())):
        bike_count = bike_stations[alcaldia]
        parking_count = parking_spots[alcaldia]
        
        # Avoid division by zero
        ratio = bike_count / parking_count if parking_count else 0
        results.append([alcaldia, bike_count, parking_count, ratio])

    # Write results to CSV
    with open('parkingperbike_analysis_output.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ALCALDIA', 'BIKE_STATIONS', 'PARKING_SPOTS', 'RATIO'])
        for row in sorted(results):
            writer.writerow(row)

if __name__ == "__main__":
    main()