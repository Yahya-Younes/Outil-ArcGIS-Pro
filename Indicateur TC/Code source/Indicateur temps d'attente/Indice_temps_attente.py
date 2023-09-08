# Importation des bibliothèque
import pandas as pd
import arcpy
from datetime import datetime, timedelta
!pip install geopandas
!pip install gtfs_functions
from gtfs_functions import Feed, map_gdf
import datetime
from gtfs_functions import Feed, map_gdf

def preprocess_data (input_GTFS_folder):

    # Load GTFS data into DataFrames
    path_to_gtfs = arcpy.Describe(f"{input_GTFS_folder}").catalogPath
    feed = Feed(r'C:\Users\sd\OneDrive\Indicateur TC\GTFS_recent.zip',time_windows=[0, 6, 9, 15, 19, 22, 24], busiest_date= False) 
    calendar_df = feed.calendar_dates
    stop_times_df = feed.stop_times
    routes_df = feed.routes

    # Merge the data to have the dates on it
    merged_data = pd.merge(stop_times_df, calendar_df, on='service_id')

    # Convert all dates to a consistent format (e.g., YYYY-MM-DD)
    merged_data['date'] = pd.to_datetime(merged_data['date'], format='%Y%m%d', errors='coerce')
    return (merged_data)

def calculate_indicator (date_fin, date_debut,merged_data) :

    All_Stops = merged_data[['parent_station','stop_name','date','trip_id']].groupby(['parent_station','date','stop_name']).count().reset_index()
    
    # Filter to have only trips from date_debut to date_fin
    Trips_per_week7 = All_Stops[(All_Stops['date']>= date_debut) & (All_Stops['date']<= date_fin)]


    # Count how many trips per parent_station which is the count of trip_id
    Weekly_trips_total = Trips_per_week7.groupby(['parent_station','stop_name'])['trip_id'].sum().reset_index()

    # Calculate the indicator base on Marc's formula
    Weekly_trips_total['Indicateur_Temps_Attente'] = (Weekly_trips_total['trip_id'] / 7 / 240) * 100

    # Renaming columns
    Weekly_trips_total.rename(columns={'trip_id': 'Number of Trips'}, inplace=True)

    # Nomalized grades base on the min max value of the city

    # Find the minimum and maximum values in the column
    min_value = Weekly_trips_total['Indicateur_Temps_Attente'].min()
    max_value = Weekly_trips_total['Indicateur_Temps_Attente'].max()

    # Normalize the column using the formula
    Weekly_trips_total['Indicateur_1_Normalise'] = ((Weekly_trips_total['Indicateur_Temps_Attente'] - min_value) / (max_value - min_value)) * 100

    # Drop the original column if needed
    Weekly_trips_total = Weekly_trips_total.drop(columns=['Indicateur_Temps_Attente'])

    return (Weekly_trips_total)

if __name__ == '__main__':
    # Parameteres su ArcGIS tool
    input_GTFS_folder = arcpy.GetParameterAsText(0)   # it should be zipped folder
    date_debut = arcpy.GetParameterAsText(1)
    date_fin = arcpy.GetParameterAsText(2)

    # Call the functions 
    
    preprocess_data (input_GTFS_folder)
    calculate_indicator (date_fin, date_debut)
