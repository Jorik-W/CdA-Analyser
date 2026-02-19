"""FIT file parser for bike ride data"""

import numpy as np
import pandas as pd
from fitparse import FitFile
from geopy.distance import geodesic
import logging

class FITParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse_fit_file(self, file_path):
        """
        Parse a FIT file and extract relevant ride data
        
        Returns:
            pandas.DataFrame: DataFrame with ride data including:
                - timestamp
                - latitude (degrees)
                - longitude (degrees)
                - altitude (meters)
                - speed (m/s)
                - power (watts)
                - heart_rate (bpm)
                - cadence (rpm)
                - distance (meters)
        """
        try:
            fitfile = FitFile(file_path)
            records = []
            
            # Extract data from FIT file
            for record in fitfile.get_messages('record'):
                data = {}
                for data_point in record:
                    if data_point.value is not None:
                        data[data_point.name] = data_point.value
                if data:  # Only add non-empty records
                    records.append(data)
            
            # Convert to DataFrame
            df = pd.DataFrame(records)
            
            # Process and clean data
            df = self._process_data(df)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error parsing FIT file: {e}")
            raise
    
    def _process_data(self, df):
        """Process raw FIT data into usable format"""
        # Convert units and handle missing data
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Convert position from semicircles to degrees
        if 'position_lat' in df.columns:
            df['latitude'] = df['position_lat'] * (180 / 2**31)
        if 'position_long' in df.columns:
            df['longitude'] = df['position_long'] * (180 / 2**31)
        
        # Convert speed from mm/s to m/s if needed
        if 'speed' in df.columns and df['speed'].dtype != 'object':
            if df['speed'].max() > 50:  # Likely in mm/s
                df['speed'] = df['speed'] / 1000
        
        # Calculate distance if not present
        if 'distance' not in df.columns:
            df['distance'] = self._calculate_distance(df)
        
        # Handle missing values
        df = df.ffill().bfill()
        
        return df
    
    def _calculate_distance(self, df):
        """Calculate cumulative distance from GPS coordinates"""
        distances = [0.0]
        total_distance = 0.0
        
        for i in range(1, len(df)):
            if pd.notna(df.iloc[i]['latitude']) and pd.notna(df.iloc[i]['longitude']):
                if pd.notna(df.iloc[i-1]['latitude']) and pd.notna(df.iloc[i-1]['longitude']):
                    coord1 = (df.iloc[i-1]['latitude'], df.iloc[i-1]['longitude'])
                    coord2 = (df.iloc[i]['latitude'], df.iloc[i]['longitude'])
                    segment_distance = geodesic(coord1, coord2).meters
                    total_distance += segment_distance
            distances.append(total_distance)
        
        return distances