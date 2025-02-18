import pandas as pd

# Load the CSV files
bikestations_df = pd.read_csv('/home/alvcantu/cdmx/stg_area_bikestations_percolonia.csv')
parking_df = pd.read_csv('/home/alvcantu/cdmx/stg_parking_percolonia.csv')

# Merge the dataframes on the 'colonia' column
merged_df = pd.merge(bikestations_df, parking_df, on='colonia')

# Adjust area_km2 column to two decimal places
merged_df['area_km2'] = merged_df['area_km2'].round(2)

# Save the merged dataframe to a new CSV file
merged_df.to_csv('/home/alvcantu/cdmx/final_bikestations_parking_percolonia.csv', index=False)