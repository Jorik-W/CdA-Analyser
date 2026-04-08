#!/usr/bin/env python3
"""Test elevation API fix - simulate user workflow"""

import sys
sys.path.insert(0, 'src')

from fit_parser import FITParser
from analyzer import CDAAnalyzer
from config import DEFAULT_PARAMETERS
from weather import WeatherService
import logging

logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("=" * 70)
print("TEST: Elevation API fetching during simulation")
print("=" * 70)

# Load FIT file WITHOUT API (simulating user who forgot to enable)
print("\n[STEP 1] Loading file WITHOUT elevation API enabled...")
print("-" * 70)
fit_file = 'data/Hulst2025.fit'
parser = FITParser()
ride_data = parser.parse_fit_file(fit_file, use_open_elevation_api=False)
print(f"Loaded {len(ride_data)} points")
print(f"Has altitude_api column: {'altitude_api' in ride_data.columns}")

# Analyze ride (creates segments)
print("\n[STEP 2] Analyzing ride without API data...")
print("-" * 70)
analyzer = CDAAnalyzer(DEFAULT_PARAMETERS)
analyzer.elevation_source = parser.elevation_source
weather_service = WeatherService()

preprocessed_segments = analyzer.preprocess_ride_data(ride_data, weather_service)
print(f"Created {len(preprocessed_segments)} preprocessed segments")
print(f"First segment has altitude_api: {'altitude_api' in preprocessed_segments[0].columns}")

# Now simulate user enabling API flag and running simulation
print("\n[STEP 3] Simulation starts with API flag enabled...")
print("-" * 70)

# This simulates the _fetch_missing_elevation_data logic
from elevation import ElevationService
import numpy as np

use_api = True  # User now enables this

if use_api and 'altitude_api' not in preprocessed_segments[0].columns:
    print("Detected missing altitude_api - fetching from Open-Elevation API...")
    
    try:
        # Collect all unique GPS coordinates
        all_coords = []
        for segment_df in preprocessed_segments:
            if 'latitude' in segment_df.columns and 'longitude' in segment_df.columns:
                coords = segment_df[['latitude', 'longitude']].dropna()
                all_coords.extend(zip(coords['latitude'], coords['longitude']))
        
        print(f"Total GPS points to lookup: {len(all_coords)}")
        unique_coords = list(dict.fromkeys(all_coords))
        print(f"Unique coordinates: {len(unique_coords)}")
        
        # Fetch elevations
        elevation_service = ElevationService()
        elevation_map = elevation_service.get_elevations_batch(unique_coords)
        
        if elevation_map:
            print(f"Successfully fetched {len(elevation_map)} elevations")
            
            # Add altitude_api to each segment
            for i, segment_df in enumerate(preprocessed_segments):
                if 'latitude' in segment_df.columns and 'longitude' in segment_df.columns:
                    def get_elevation(row):
                        key = (row['latitude'], row['longitude'])
                        fit_alt = row.get('altitude_fit', row.get('altitude', np.nan))
                        return elevation_map.get(key, fit_alt)
                    
                    segment_df['altitude_api'] = segment_df.apply(get_elevation, axis=1)
                    api_valid = segment_df['altitude_api'].notna().sum()
                    print(f"  Segment {i}: {api_valid}/{len(segment_df)} points have API elevation")
            
            analyzer.elevation_source = 'Open-Elevation API (fetched during simulation)'
        else:
            print("ERROR: Failed to fetch elevation data from API!")
    except Exception as e:
        print(f"ERROR during elevation fetch: {e}")
        import traceback
        traceback.print_exc()

# Verify segments now have altitude_api
print("\n[STEP 4] Verifying altitude_api column in segments...")
print("-" * 70)
for i, segment_df in enumerate(preprocessed_segments[:3]):  # Check first 3
    has_col = 'altitude_api' in segment_df.columns
    if has_col:
        valid = segment_df['altitude_api'].notna().sum()
        print(f"Segment {i}: Has altitude_api column with {valid}/{len(segment_df)} valid values")
    else:
        print(f"Segment {i}: NO altitude_api column  <-- PROBLEM!")

print("\n[STEP 5] Testing simulation result extraction...")
print("-" * 70)

# Simulate the part where we extract start_elevation_api for display
for i, segment_df in enumerate(preprocessed_segments[:3]):
    start_elev_fit = float(segment_df['altitude_fit'].iloc[0]) if 'altitude_fit' in segment_df.columns and not segment_df['altitude_fit'].isna().all() else None
    start_elev_api = float(segment_df['altitude_api'].iloc[0]) if 'altitude_api' in segment_df.columns and not segment_df['altitude_api'].isna().all() else None
    print(f"Segment {i}:")
    print(f"  Start Elev (FIT): {start_elev_fit:.1f}m" if start_elev_fit else "  Start Elev (FIT): None")
    print(f"  Start Elev (API): {start_elev_api:.1f}m" if start_elev_api else "  Start Elev (API): N/A")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
