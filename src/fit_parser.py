"""FIT file parser for bike ride data"""

import numpy as np
import pandas as pd
from fitparse import FitFile
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
        
        # Handle missing values only for non-critical channels.
        # Keep power/speed gaps explicit so dropout periods are not smeared.
        safe_fill_columns = [
            col for col in ['altitude', 'heart_rate', 'cadence', 'distance', 'temperature']
            if col in df.columns
        ]
        if safe_fill_columns:
            df[safe_fill_columns] = df[safe_fill_columns].ffill().bfill()
        
        return df
    
    def _calculate_distance(self, df):
        """Calculate cumulative distance from GPS coordinates using vectorized haversine formula"""
        if 'latitude' not in df.columns or 'longitude' not in df.columns:
            self.logger.warning("No GPS coordinates available for distance calculation")
            return [0.0] * len(df)

        lat = np.radians(df['latitude'].values.astype(float))
        lon = np.radians(df['longitude'].values.astype(float))

        dlat = np.diff(lat)
        dlon = np.diff(lon)

        # Haversine formula
        a = np.sin(dlat / 2.0) ** 2 + np.cos(lat[:-1]) * np.cos(lat[1:]) * np.sin(dlon / 2.0) ** 2
        a = np.clip(a, 0.0, 1.0)  # Numerical safety clamp
        segment_distances = 6371000.0 * 2.0 * np.arcsin(np.sqrt(a))  # Earth radius in meters

        # Zero out segments where either endpoint has NaN coordinates
        valid = np.isfinite(lat[:-1]) & np.isfinite(lon[:-1]) & np.isfinite(lat[1:]) & np.isfinite(lon[1:])
        segment_distances = np.where(valid, segment_distances, 0.0)

        return np.concatenate([[0.0], np.cumsum(segment_distances)]).tolist()