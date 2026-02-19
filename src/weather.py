"""Weather data retrieval module"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import logging
from config import OPEN_METEO_URL_FORCAST, OPEN_METEO_URL_ARCIVE

class WeatherService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_weather_data(self, latitude, longitude, timestamp):
        """
        Get weather data for a specific location and time
        
        Args:
            latitude (float): Latitude in degrees
            longitude (float): Longitude in degrees
            timestamp (datetime): UTC timestamp
            
        Returns:
            dict: Weather data including temperature, wind speed, etc.
        """
        try:
            # Format date for API request
            date_str = timestamp.strftime('%Y-%m-%d')

            # Determine which API endpoint to use based on the timestamp
            # The archive API is for data older than ~1 month.
            one_month_ago = datetime.now().date() - timedelta(days=30)
            if timestamp.date() >= one_month_ago:
                OPEN_METEO_URL = OPEN_METEO_URL_FORCAST
            else:
                OPEN_METEO_URL = OPEN_METEO_URL_ARCIVE

            params = {
                'latitude': latitude,
                'longitude': longitude,
                'hourly': ','.join([
                    'temperature_2m',
                    'wind_speed_10m',
                    'wind_direction_10m',
                    'pressure_msl'
                ]),
                'start_date': date_str,
                'end_date': date_str,
                'timezone': 'UTC'
            }
            
            response = requests.get(OPEN_METEO_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract hourly data
            hourly_data = data['hourly']
            timestamps = pd.to_datetime(hourly_data['time'])
            
            # Find closest hour to our timestamp
            target_hour = timestamp.hour
            closest_idx = min(range(len(timestamps)), 
                            key=lambda i: abs(timestamps[i].hour - target_hour))
            
            weather_data = {
                'temperature': hourly_data['temperature_2m'][closest_idx],
                'wind_speed': hourly_data['wind_speed_10m'][closest_idx],
                'wind_direction': hourly_data['wind_direction_10m'][closest_idx],
                'pressure': hourly_data['pressure_msl'][closest_idx] if 'pressure_msl' in hourly_data else 1013.25
            }
            
            return weather_data
            
        except Exception as e:
            self.logger.warning(f"Could not retrieve weather data: {e}")
            # Return default values
            return {
                'temperature': 20.0,  # Celsius
                'wind_speed': 0.0,    # m/s
                'wind_direction': 0.0, # degrees
                'pressure': 1013.25   # hPa
            }
    
    def calculate_air_density(self, temperature, pressure, humidity=50):
        """
        Calculate air density based on temperature and pressure
        
        Args:
            temperature (float): Temperature in Celsius
            pressure (float): Pressure in hPa
            humidity (float): Relative humidity in %
            
        Returns:
            float: Air density in kg/m³
        """
        if temperature is None:
            temperature = 20.0
            print("temperature fix")
        
        if pressure is None:
            pressure = 1013.25
            print("pressure fix")
        
        if humidity is None:
            humidity = 50
            print("humidity fix")
        
        # Convert to Kelvin
        temp_kelvin = temperature + 273.15
        
        # Simplified air density calculation
        # More accurate would require humidity data
        air_density = (pressure * 100) / (287.05 * temp_kelvin)  # kg/m³
        
        return air_density