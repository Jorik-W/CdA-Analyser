#!/usr/bin/env python3
"""Debug script to test elevation API"""

import sys
sys.path.insert(0, 'src')

from elevation import ElevationService
from fit_parser import FITParser
import logging

logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

# Test 1: Direct elevation API call
print("=" * 60)
print("Test 1: Direct Elevation API call")
print("=" * 60)

coords = [(50.7134, 3.8163), (50.7135, 3.8165), (50.7136, 3.8167)]
service = ElevationService()
result = service.get_elevations_batch(coords)
print(f"Input coordinates: {coords}")
print(f"Result: {result}")
print(f"Result type: {type(result)}")

# Test 2: Parse FIT file without elevation API
print("\n" + "=" * 60)
print("Test 2: Parse FIT file WITHOUT elevation API")
print("=" * 60)

fit_file = 'data/Hulst2025.fit'  # Using first available FIT file
parser = FITParser()
df = parser.parse_fit_file(fit_file, use_open_elevation_api=False)
print(f"Loaded {len(df)} points")
print(f"Columns: {list(df.columns)}")
print(f"Has altitude: {'altitude' in df.columns}")
print(f"Has altitude_fit: {'altitude_fit' in df.columns}")
print(f"Has altitude_api: {'altitude_api' in df.columns}")
print(f"Has latitude: {'latitude' in df.columns}")
print(f"Has longitude: {'longitude' in df.columns}")

if 'latitude' in df.columns:
    valid_coords = df[['latitude', 'longitude']].dropna()
    print(f"Valid GPS coordinates: {len(valid_coords)} / {len(df)}")
    print(f"First 3 coords: {list(zip(valid_coords['latitude'].head(3), valid_coords['longitude'].head(3)))}")

# Test 3: Parse FIT file WITH elevation API
print("\n" + "=" * 60)
print("Test 3: Parse FIT file WITH elevation API")
print("=" * 60)

parser2 = FITParser()
df2 = parser2.parse_fit_file(fit_file, use_open_elevation_api=True)
print(f"Loaded {len(df2)} points")
print(f"Columns: {list(df2.columns)}")
print(f"Has altitude: {'altitude' in df2.columns}")
print(f"Has altitude_fit: {'altitude_fit' in df2.columns}")
print(f"Has altitude_api: {'altitude_api' in df2.columns}")
print(f"Elevation source: {parser2.elevation_source}")

if 'altitude_api' in df2.columns:
    api_valid = df2['altitude_api'].notna().sum()
    print(f"altitude_api valid values: {api_valid} / {len(df2)}")
    print(f"altitude_api min/max: {df2['altitude_api'].min():.2f} / {df2['altitude_api'].max():.2f}")
    print(f"First 5 altitude_api values:\n{df2['altitude_api'].head()}")

print("\n" + "=" * 60)
print("Debug complete!")
print("=" * 60)
