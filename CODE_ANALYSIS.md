# CdA Analyzer - Complete Code Analysis

> **Last updated: Session 4**  
> All bugs from Sessions 1–3 plus the new Session 4 findings have been implemented.  
> See `BUG_REPORT.md` for the full bug history and per-session fix log.

---

## Session 4 Change Summary
| File | Change |
|------|--------|
| `analyzer.py` | `_calculate_air_density` converted to `@staticmethod`; no longer creates `WeatherService` per segment |
| `analyzer.py` | `analyze_ride`: `if summary and ride_info` prevents KeyError in GUI when 0 segments |
| `analyzer.py` | `_calculate_acceleration`: `pd.Series(acceleration, index=df.index)` prevents silent NaN on non-default-indexed DataFrames |
| `analyzer.py` | `_prepare_averaged_data`: fallback acceleration Series gets `index=segment_df.index` |
| `qt_gui.py` | `_calculate_simulation_results`: `try/finally` ensures `wind_effect_factor` is always restored |
| `qt_gui.py` | `_generate_plots` + `_generate_simulation_plots`: `np.polyfit` guarded with `len(set(wind_angles)) > 2` |
| `qt_gui.py` | `resource_path`, `_set_window_icon`, `_generate_simulation_plots`: `print()` → `_logger.warning()` |
| `qt_gui.py` | `_display_analysis_results`: NaN/None weather values display as `N/A` instead of `nan` |

---

## Project Overview
**CdA Analyzer** is a Python application that analyzes cycling data from FIT files to calculate the coefficient of drag (CdA) and frontal area. It processes bike ride data, identifies steady-state segments, calculates aerodynamic properties, and provides both CLI and GUI interfaces for analysis.

**Purpose**: Determine cyclist aerodynamic efficiency by analyzing power, speed, and environmental conditions during steady bike rides.

---

## Architecture Overview

### High-Level Data Flow
```
FIT File → Parser → Analyzer → Weather Service → Results
         ↓
      GUI/CLI ←────────────────────────────────┘
```

### Core Components
1. **FIT Parser** (`fit_parser.py`) - Reads Garmin FIT bike files
2. **Analyzer** (`analyzer.py`) - Main CdA calculation engine
3. **Weather Service** (`weather.py`) - Retrieves environmental data via Open-Meteo API
4. **Configuration** (`config.py`) - Parameter definitions and defaults
5. **Utilities** (`utils.py`) - Helper functions
6. **Interfaces** - GUI (`qt_gui.py`, `gui.py`) and CLI (`cli.py`)
7. **Scripts** - Standalone tools for estimation and data conversion

---

## File-by-File Analysis

### 1. `main.py` (Entry Point)
**Lines**: ~30  
**Purpose**: Application entry point with interface selection

**Key Functions**:
- `main()` - Parses command-line arguments to select between GUI and CLI
  - First checks for `--gui` or `--cli` flags
  - Falls back to GUI if available, otherwise CLI
  - Passes remaining arguments to CLI if selected

**Logic**:
- Uses `argparse` with `parse_known_args()` to allow flexible argument passing
- Dynamically imports GUI or CLI modules based on user choice
- If GUI fails to import, gracefully falls back to CLI

**Error Handling**: Basic try-except for import failures

---

### 2. `config.py` (Configuration)
**Lines**: ~120+

**Main Element**: DEFAULT_PARAMETERS dictionary with cyclist-specific profiles

**Key Parameters**:
```python
- min_segment_length: 200m (minimum steady segment)
- min_duration: 30s
- min_speed: 8.3 m/s (~30 km/h)
- max_speed: 20.0 m/s
- speed_steady_threshold: 0.35 m/s (variability tolerance)
- power_steady_threshold: 500W
- slope_steady_threshold: 5.0°
- rider_mass: 75 kg (default)
- bike_mass: 10 kg
- rolling_resistance: 0.003
- drivetrain_loss: 2.5%
- wind_effect_factor: 0.06
```

**Notes**:
- Contains extensive documentation with per-rider/per-route configurations (Jorik, Sam, Lars, Xiano)
- Stores actual CdA results from real rides for reference
- Contains analysis of tire differences and power variations
- API URLs for Open-Meteo weather service (forecast and archive)

**Profiles Listed**:
- Eeklo ride (multiple riders)
- Kappelle ride  
- Damme ride
- Lievegem ride
- kappelle2023 variations

---

### 3. `fit_parser.py` (FIT File Parsing)
**Lines**: ~85  
**Purpose**: Extract data from Garmin FIT binary files

**Class**: `FITParser`
- **`parse_fit_file(file_path)`** - Main entry point
  - Uses `fitparse.FitFile` library to read binary FIT files
  - Extracts all 'record' messages
  - Returns Pandas DataFrame

- **`_process_data(df)`** - Data cleaning and transformation
  - Converts position from semicircles to decimal degrees
  - Converts speed from mm/s to m/s if needed
  - Calls `_calculate_distance()` if 'distance' column is absent
  - `df.ffill().bfill()` fills missing values in ALL columns
    - ⚠️ NOTE: this includes `power` — if power drops out, gaps are filled with the
      last valid reading rather than staying NaN. Steady-segment filtering may
      subsequently fail to detect those gaps.

- **`_calculate_distance(df)`** — Vectorized numpy haversine  
  - All coordinates are broadcast to numpy arrays simultaneously
  - Computes great-circle distance in a single vectorized operation
  - No more O(n) Python loop or `geopy` dependency

**Output DataFrame Columns**:
- `timestamp`, `latitude`, `longitude`, `altitude`
- `speed` (m/s), `power` (W), `heart_rate` (bpm)
- `cadence` (rpm), `distance` (m)

**Error Handling**: Wrapped in try-except with logging

---

### 4. `analyzer.py` (Core Analysis Engine)
**Lines**: ~1000+ (largest file)

**Purpose**: Calculate CdA through power component analysis

**Class**: `CDAAnalyzer`

#### Major Methods:

**Initialization & Setup**:
- `__init__(parameters)` - Initialize with parameters, calculate total mass, drivetrain efficiency
- `update_parameters(new_parameters)` - Update and recalculate derived values
- `_extract_ride_info(df)` - Extract basic ride metadata (duration, distance, elevation)

**Main Analysis Flow**:
- `analyze_ride(df, weather_service, preprocessed_segments)` - Orchestrates complete analysis
  - Calls `preprocess_ride_data()` if segments not preprocessed
  - Calls `_analyze_segments()` for per-segment analysis
  - Calls `_calculate_summary()` for aggregated results

**Data Preprocessing**:
- `preprocess_ride_data(df, weather_service)` - Preprocessing pipeline
  - Identifies steady segments
  - Fetches weather data for each segment
  - Caches weather for later use

- `identify_steady_segments(df)` - Segment detection
  1. Calculate derived metrics (slope, acceleration)
  2. Create steady-state mask using filters
  3. Group consecutive steady points into segments
  4. Filter by duration/distance criteria

**Steady State Detection**:
- `_create_steady_mask(df)` - Boolean mask for valid data points
- `_apply_speed_filter(df, mask)` - Filter for min/max speed
- `_apply_stability_filters(df, mask)` - Check rolling std for power/speed/slope
- `_group_into_segments(df, steady_mask)` - Group consecutive steady points
- `_filter_segments_by_criteria(segments)` - Minimum duration/distance check

**CdA Calculation Process**:
- `calculate_cda_for_segment(segment_df, weather_data)` - Per-segment analysis
  1. Prepare averaged data with rolling window (5-point window)
  2. Get environmental conditions (air density, wind)
  3. Calculate power components (rolling, gradient, inertial, aero)
  4. Calculate CdA values from aerodynamic power
  5. Compile results with statistics

- `_prepare_averaged_data(segment_df, window_size=5)` - Smooth data
  - Applies rolling average to speed, power, acceleration, slope
  - Filters to valid data points (speed > 0, no NaN)
  - Returns rolling-averaged data dictionary

**Derived Metrics Calculation**:
- `_calculate_slope(df)` - From altitude/distance using arctan2
- `_calculate_acceleration(df)` - From speed/time
- `_rolling_average(series, window_size)` - Rolling mean

**Power Component Calculation** (Physics Model):
- `_calculate_power_components()` - Master method
  - Rolling power: `mass * g * Crr * speed`
  - Gradient power: `mass * g * sin(slope) * speed`
  - Inertial power: `mass * acceleration * speed`
  - Aero power: Total power - other components (clamped to 0)
  - Adjusts for drivetrain efficiency losses

**Environmental Conditions**:
- `_get_environmental_conditions(weather_data)` — Air density + wind data assembly
- `_calculate_air_density(weather_data)` — **Static method** (no longer uses WeatherService)  
  - Formula inlined: `(P * 100) / (287.05 * (T + 273.15))`  
  - No HTTP session or WeatherService instantiation per segment

**Wind Effects Calculation**:
- `_calculate_wind_effects(segment_df, wind_speed, wind_direction, bike_speed)`
  - Calculates GPS bearing of segment direction
  - Converts wind direction to effective head/tailwind component
  - Uses `wind_effect_factor` to scale wind impact
  - Returns effective wind speed and air speed

- `_calculate_wind_from_coordinates(...)` - GPS-based bearing calculation
  - Uses proper bearing formula (atan2, normalized to -180/180)
  - Calculates wind angle relative to travel direction
  - Falls back if insufficient coordinates

- `_calculate_segment_direction(segment_df)` - Initial/final bearing
  - Converts to radians, uses atan2 for bearing
  - Handles normalization to 0-360°

**CdA Calculation**:
- `_calculate_cda_values(averaged_data, power_components, env_conditions)`
  - Calls `_calculate_single_cda()` for each point
  - Filters to reasonable range (0.0 - 1.0)

- `_calculate_single_cda(speed, aero_power, effective_wind, air_density)`
  - Formula: `CdA = (2 * aero_power) / (air_density * air_speed³)`
  - Avoids division by very small speeds

- `_calculate_estimated_power(segment_df, fixed_cda, weather_data)`
  - Inverse calculation: estimate power given CdA
  - Used for validation/simulation

**Outlier Handling**:
- `_filter_cda_outliers(cda_values)` - IQR-based removal
  - Calculates Q75, Q25
  - Removes values outside (Q25 - 1.5*IQR, Q75 + 1.5*IQR)

**Result Compilation**:
- `_compile_segment_result()` - Package final segment result
- `_calculate_segment_averages()` - Mean values for segment
- `_calculate_residual()` - Power difference metric
- `_get_segment_duration()` and `_get_segment_distance()`

**Summary Calculation**:
- `_calculate_summary(segment_results)` - Aggregate statistics
  - Weighted average CdA (weighted by segment duration)
  - Standard deviation, min/max CdA
  - Wind angle coefficients (2nd order polynomial fit)
  - Average weather, wind, acceleration metrics
  - Ride info from segment data

- `_calculate_wind_angle_coefficients(segment_results)`
  - Fits 2nd order polynomial: `CdA = a*θ² + b*θ + c`
  - Normalizes wind angles to -180 to 180 range
  - Uses `np.polyfit()` to find coefficients

**Weather Data Management**:
- `_store_weather_data()` - Cache weather by segment
- `_get_weather_data_for_segment()` - Fetch or retrieve cached
- `weather_cache` - Dictionary for storing weather data

**Logging**: Extensive debug/info logging throughout

#### Key Physics Formulas:
```
Total Power = Rolling Power + Gradient Power + Inertial Power + Aero Power

Rolling Power = mass * g * Crr * v
Gradient Power = mass * g * sin(slope) * v
Inertial Power = mass * acceleration * v
Aero Power = 0.5 * ρ * CdA * v_air³

Where v_air = v_bike + wind_effect

CdA = (2 * Aero Power) / (ρ * v_air³)
```

#### Critical Logic Issues (Post Session-4 State)
- ✅ All print-debug statements replaced with `logger.debug()/warning()`
- ✅ Duplicate `avg_wind_speed` key fixed (single-pass pre-computation)
- ✅ Negative air_speed clamped to 0.1 minimum
- ✅ `_calculate_air_density` no longer creates a new WeatherService (and requests.Session) per segment — formula is now a pure `@staticmethod`
- ✅ Zero-segment case: `analyze_ride` guards with `if summary:` (falsy empty dict) so `ride_info` is only added to non-empty summaries, preventing KeyError in GUI
- ✅ Index-alignment bug in `_calculate_acceleration` fixed: `pd.Series(acceleration, index=df.index)`
- ✅ Same fix in `_prepare_averaged_data` fallback acceleration Series

---

### 5. `weather.py` (Environmental Data)
**Lines**: ~130  
**Class**: `WeatherService`

**Methods**:
- `get_weather_data(latitude, longitude, timestamp)` — Fetch weather from Open-Meteo API
  - Selects forecast or archive API based on date (>30 days old uses archive)
  - Uses a persistent `requests.Session()` for connection reuse
  - `timeout=10` on all HTTP calls to prevent application freeze
  - Extracts temperature, wind_speed, wind_direction, pressure
  - Finds closest hourly index to target timestamp
  - Returns default values and logs a warning on any API failure
  - ⚠️ NOTE: `wind_speed_10m` from Open-Meteo defaults to **km/h**. No `wind_speed_unit`
    parameter is set, so wind speed in returned dict is in km/h but used as m/s in the
    analyzer. Existing `wind_effect_factor` calibrations absorb this unit discrepancy.
    To fix properly: add `'wind_speed_unit': 'ms'` to `params` and multiply all
    calibrated `wind_effect_factor` values by ~3.6.

- `calculate_air_density(temperature, pressure, humidity=50%)`
  - Converts to Kelvin; uses ideal gas law: `ρ = (P × 100) / (287.05 × T_K)`
  - Returns kg/m³
  - Not called from `analyzer.py` anymore (logic is now inlined as a staticmethod there)

**Error Handling**:
- Graceful fallback to default values (20 °C, 0 m/s wind, 1013.25 hPa)
- Logs warnings with `logger.warning()` (no bare print statements)

**Dependencies**: `requests`, `pandas`

---

### 6. `cli.py` (Command Line Interface)
**Lines**: ~110

**Purpose**: Text-based interactive analysis interface

**Main Function**:
- `main()` - CLI execution loop
  - Parses FIT file argument
  - Loads/prompts for parameters
  - Runs analysis in loop (allows parameter tweaking)
  - Displays formatted results
  - Optionally saves to JSON

**Key Functions**:
- `_load_parameters(param_file)` - Load from JSON or prompt interactively
- `_display_results(results)` - Pretty-print analysis results
  - Prints parameters used
  - Prints segment table (ID, duration, distance, speeds, slopes, power, CdA)
  - Prints summary statistics
  - Prints wind angle formula if available

- `_save_results(results, output_file)` - Export to JSON
  - Converts datetime objects to ISO format strings
  - Pretty-prints with 2-space indent

**Interactive Loop**:
- Allows continuous parameter adjustment without reloading FIT file
- Press Ctrl-C to exit

---

### 7. `qt_gui.py` (PyQt5 Graphical Interface)
**Lines**: ~800+

**Purpose**: Modern GUI with multiple tabs and advanced features

**Key Classes**:
- `WorkerThread(QThread)` - Background analysis thread
  - `run()` - Preprocesses and analyzes without blocking UI
  - Emits signal with results or error

- `CustomProgress(QProgressBar)` - Custom progress bar widget
  - Animated indeterminate mode (moving blue chunk)
  - Shows percentage when determinate
  - Custom paintEvent for styling

- `GUIInterface(QMainWindow)` - Main application window

**UI Tabs**:
1. **File Selection** - Browse/load FIT file
   - Status text showing data points and columns
   - About dialog with license/credits

2. **Parameters** - Scrollable parameter list
   - QLineEdit for each parameter
   - Run Analysis button

3. **Results & Analysis** - Primary results display
   - Summary text (formatted segment table + statistics)
   - Map tab (QWebEngineView showing ride with segment colors)
   - Plots tab (matplotlib integration)
   - Wind effect factor slider (0.0 - 1.0)

4. **Simulation** - Weather scenario testing
   - Wind speed slider (0-20 m/s)
   - Wind angle slider (-180 to 180°)
   - Simulation plot showing CdA vs wind angle

**Key Methods**:
- `_setup_ui()` - Initialize 4 tabs
- `_setup_file_tab()` - File selection interface
- `_setup_parameters_tab()` - Parameter entry form
- `_setup_results_tab()` - Results display with sub-tabs
- `_setup_simulation_tab()` - Weather simulation interface

- `_browse_fit_file()` - File dialog
- `_load_fit_file()` - Parse and preview FIT data
- `_save_parameters()` - Extract values from UI entries
- `_run_analysis()` - Start background analysis thread
- `_run_analysis_worker()` - Worker thread target (runs in background)
- `_on_analysis_complete(results, error)` - Callback when analysis done

- `_display_analysis_results()` - Show summary and detailed results
- `_create_segment_mapping()` - Map segment IDs to data indices

- `_generate_map()` - Create interactive map with Folium
  - Colors segments using distinct color scheme (tab20/tab20b/tab20c)
  - Marks segment start/end points
  - Shows weather data popups
  - Saves to HTML temp file
  - Opens in browser

- `_generate_plots()` - Create matplotlib plots
  - CdA vs wind angle scatter plot
  - CdA distribution histogram
  - Power vs speed scatter
  - Wind angle polynomial fit visualization

- `_on_wind_effect_slider_moved()` - Update slider value display
- `_on_wind_effect_changed()` - Rerun analysis with new wind factor
- `_on_simulation_params_changed()` - Update simulation display

- `_cleanup_results()` - Cleanup matplotlib figures/canvases
- `_generate_segment_colors(n_segments)` - Color cycling algorithm
  - Uses tab20 + tab20b + tab20c (60 colors total)
  - Rotates offset for >60 segments to avoid visual repetition

**Threading Model**:
- UI runs on main thread
- Analysis runs on WorkerThread
- Results signal handler (`_on_analysis_complete`) runs on main thread via `after()`

**Error Handling**:
- Try-except blocks around file operations
- MessageBox dialogs for user-visible errors
- Traceback printing for debugging

---

### 8. `gui.py` (Legacy Tkinter GUI)
**Lines**: ~300

**Purpose**: Original Tkinter-based GUI (likely deprecated in favor of qt_gui.py)

**Key Classes**:
- `GUIInterface` - Main window (Tkinter root)

**Features**:
- Splash screen (2.5 sec) with logo and loading text
- Notebook (tabbed interface) with:
  - File Selection tab
  - Parameters tab
  - Results & Analysis tab (with sub-tabs: Summary, Map, Plots)

**Key Methods**:
- `_show_splash_and_start()` - Splash screen with image loading
- `_setup_ui()` - Initialize tabs
- `_setup_file_tab()`, `_setup_parameters_tab()`, `_setup_results_tab()`
- Similar methods to qt_gui but using Tkinter widgets

**Threading**: Uses `threading.Thread` (daemon) for background analysis

**Map/Plots**:
- Folium for interactive HTML maps
- Matplotlib with TkAgg backend for inline plots

**Status**: Appears to be legacy code kept for compatibility

---

### 9. `utils.py` (Utility Functions)
**Lines**: ~80

**Functions**:

- `calculate_distance(lat1, lon1, lat2, lon2)` - Haversine formula
  - Converts to radians
  - Calculates great-circle distance
  - Returns meters

- `interpolate_missing_data(df, columns)` - Linear interpolation
  - Fills NaN values in specified columns
  - Returns modified DataFrame

- `calculate_slope(distance, altitude)` - Slope from arrays
  - Uses arctan2 of (altitude_diff / distance_diff)
  - Returns slope in degrees

- `format_duration(seconds)` - Human-readable formatting
  - Returns seconds, minutes, or hours with appropriate units

- `validate_parameters(parameters)` - Parameter validation
  - Checks required parameters exist
  - Validates ranges (mass > 0, resistance >= 0)
  - Returns (is_valid, error_message) tuple

---

### 10. `scripts/estimate_power_speed_or_cda.py` (Calculation Utility)
**Lines**: ~70

**Purpose**: Standalone calculator for power/speed/CdA relationships

**Functions**:
- `power_required(v, cda, crr, mass, air_density, gravity)`
  - Calculates power for given speed and CdA
  - Includes 3% drivetrain loss factor

- `speed_from_power(power, cda, crr, mass, air_density, gravity)`
  - Solves cubic equation: `a*v³ + b*v - power = 0`
  - Uses `scipy.optimize.fsolve()` with initial guess
  - Accounts for 3% drivetrain loss

- `cda_from_power_speed(power, speed, crr, mass, air_density, gravity)`
  - Reverse calculation: get CdA from power and speed
  - Subtracts rolling resistance power
  - Formula: `CdA = (2 * aero_power) / (ρ * v³)`

**Main Menu**: Interactive console for selecting calculation type

**Defaults**:
- mass: 86 kg
- gravity: 9.81 m/s²
- air_density: 1.225 kg/m³

---

### 11. `scripts/bestbikesplit_to_intervals.py` (Data Converter)
**Lines**: ~150

**Purpose**: Convert BestBikeSplit race plan to training interval format

**Functions**:
- `parse_time_to_seconds(time_str)` - Convert "HH:MM:SS" to seconds
- `format_seconds_to_minsec_dash(total_seconds)` - Convert to "-XmYs" format
- `convert_distance_based(line, watt_delta)` - Extract distance + power range
- `convert_time_based(line, watt_delta, time_percent)` - Extract time + power range

**Command Line Arguments**:
- `input_file` - Required TXT export from BestBikeSplit
- `--mode [distance|time]` - Export format (default: distance)
- `--watt-delta` - ±W adjustment (default: 10)
- `--time-percent` - % increase to interval time (time mode only)

**Output Filename Convention**:
- `{basename}_{mode}_{options}_{delta}w.txt`
- Examples:
  - `intervals_distance_10w.txt`
  - `intervals_time_5pct_15w.txt`

**File Format**:
- Input: BestBikeSplit TSV export with columns including distance, time, power
- Output: Interval format like "- 2.5 km 185-205W" or "-4m30s 180-200W"

---

### 12. `scripts/generate_icon.py` (Icon Builder)
**Lines**: ~15

**Purpose**: Build icon.py from binary .ico file

**Process**:
1. Read `logo_blue.ico` binary file
2. Encode to base64
3. Write to `icon.py` as `LOGO_BASE64` string variable

**Usage**: Run once to update icon, embeds in `icon.py` for distribution

---

## Key Data Structures

### Segment DataFrame Format
```python
{
    'timestamp': pd.Timestamp,
    'latitude': float (degrees),
    'longitude': float (degrees),
    'altitude': float (meters),
    'speed': float (m/s),
    'power': float (watts),
    'heart_rate': float (bpm),
    'cadence': float (rpm),
    'distance': float (meters),
    'slope_degrees': float (calculated),
    'acceleration': float (calculated),
}
```

### Analysis Result Structure
```python
{
    'segments': [
        {
            'segment_id': int,
            'cda': float,
            'cda_std': float,
            'cda_points': int,
            'duration': float (seconds),
            'distance': float (meters),
            'speed': float (m/s avg),
            'air_speed': float (m/s avg),
            'power': float (watts avg),
            'effective_wind': float (m/s),
            'wind_angle': float (degrees),
            'slope': float (degrees),
            'temperature': float (°C) or None,
            'pressure': float (hPa) or None,
            'wind_speed': float (m/s) or None,
            'wind_direction': float (degrees) or None,
            'start_time': pd.Timestamp,
            'end_time': pd.Timestamp,
            ...
        }
    ],
    'summary': {
        'total_segments': int,
        'weighted_cda': float,
        'average_cda': float,
        'cda_std': float,
        'min_cda': float,
        'max_cda': float,
        'wind_coefficients': [a, b, c] or None,
        'total_duration': float (seconds),
        'total_distance': float (meters),
        'avg_wind_speed': float (m/s),
        'avg_air_speed': float (m/s),
        'avg_acceleration': float (m/s²),
        'avg_temp': float (°C),
        'avg_press': float (hPa),
        'avg_wind_direction': float (degrees),
    },
    'parameters': dict (copy of DEFAULT_PARAMETERS used),
    'ride_info': {
        'date': datetime.date,
        'start_time': pd.Timestamp,
        'end_time': pd.Timestamp,
        'duration_seconds': int,
        'duration_hms': str,
        'total_distance_m': float,
        'average_speed_mps': float,
        'average_speed_kmh': float,
        'elevation_gain_m': float,
    }
}
```

### Weather Data Structure
```python
{
    'temperature': float (°C),
    'wind_speed': float (m/s),
    'wind_direction': float (degrees 0-360),
    'pressure': float (hPa),
}
```

---

## Important Design Patterns

### 1. Threading Model (PyQt5 GUI)
- Main UI thread launches `WorkerThread` for analysis
- Worker emits signal with results
- Main thread handles signal and updates UI
- Prevents UI freezing during analysis

### 2. Rolling Average Smoothing
- 5-point centered rolling average on all metrics
- Filters NaN values after smoothing
- Reduces noise in power and speed data

### 3. Physics-Based Calculation
- Decompose power into physical components
- Calculate residual power (aerodynamic)
- Derive CdA from aerodynamic power and air speed
- Account for drivetrain losses

### 4. Weather Caching
- Cache weather data per segment in `weather_cache` dict
- Avoid redundant API calls during reanalysis
- Cache stored in memory (not persistent)

### 5. Steady State Detection (Multi-Stage Filtering)
1. Apply speed range filter
2. Apply rolling std filters (power, speed, slope stability)
3. Group consecutive steady points
4. Filter by minimum duration/distance
5. Calculate metrics on remaining segments

### 6. Parameter Profiles
- Store test-specific configurations in `config.py`
- Different riders/bikes have different optimal parameters
- CdA results vary significantly with rider mass and rolling resistance

---

## Critical Code Issues & Debugging Notes

### Issue #1: None Type Handling (analyzer.py)
**Location**: Multiple lines throughout analyzer.py
**Problem**: Debug print statements left in production code
```python
if speed is None:
    speed = 0.0
    print("speed fix")
```
**Solution**: Replace with proper error handling/logging

### Issue #2: Duplicate Summary Key
**Location**: `analyzer.py`, `_calculate_summary()`
**Problem**: 'avg_wind_speed' assigned twice (overwrites first value)
```python
'avg_wind_speed': np.mean([s.get('wind_speed', 0) for s in segment_results]),
...
'avg_wind_speed': np.mean([s['wind_speed'] for s in segment_results if 'wind_speed' in s]),
```

### Issue #3: Missing Weather Data Handling
**Location**: Various methods in analyzer.py
**Problem**: Weather data may be None but calculations continue
**Impact**: Could produce invalid results in areas without weather API coverage

### Issue #4: GUI Memory Management
**Location**: qt_gui.py, GUI plotting
**Problem**: Matplotlib figures created but cleanup may leak memory with many reanalysis operations

### Issue #5: API Timeout Risk
**Location**: weather.py, `get_weather_data()`
**Problem**: `requests.get()` could hang indefinitely
**Solution**: Add timeout parameter

---

## Performance Characteristics

### Typical Analysis Time
- Small ride (1 hour): < 5 seconds
- Medium ride (2-3 hours): 10-30 seconds
- Depends on segment count and weather API responsiveness

### Memory Usage
- FIT file parsing: ~50-200 MB depending on ride length
- Weather cache: ~1 KB per segment
- GUI with plots: ~100-300 MB

### API Rate Limits
- Open-Meteo: No documented rate limit for free tier
- Archive API: Same limit as forecast

---

## Dependencies & Libraries

### Core Libraries
- `pandas` - Data manipulation and analysis
- `numpy` - Numerical computing
- `scipy` - Scientific computing (optimization)
- `fitparse` - FIT file parsing

### GUI Libraries
- `PyQt5` - Modern GUI framework
- `matplotlib` - Plotting
- `folium` - Interactive maps (generates HTML)

### Utilities
- `requests` - HTTP requests (weather API)
- `geopy` - Geodesic distance calculation
- `Pillow` - Image processing (for splash screen)

### External APIs
- Open-Meteo (no API key required, free service)
  - Forecast: up to ~1 month recent data
  - Archive: historical data >30 days old

---

## Configuration & Customization

### Adding New Rider Profile
In `config.py`, add a new commented section with rider-specific parameters:
```python
"""
New Rider Name
    rider_mass: X kg
    bike_mass: Y kg
    rolling_resistance: Z
    ... other parameters
"""
```

### Changing Default Analysis Parameters
Edit `DEFAULT_PARAMETERS` dictionary in `config.py`

### Custom Parameter Files
CLI: Use `-p parameters.json`
GUI: Manually enter in Parameters tab

### Wind Effect Factor Tuning
- **Range**: 0.0 (no wind effect) to 1.0 (full wind effect)
- **Current default**: 0.06
- **Per-rider calibration**: Often 0.03-0.10 based on road orientation variation

---

## Future Enhancement Opportunities

1. **Persistent Weather Cache** - Store weather data in SQLite
2. **Batch Processing** - Analyze multiple FIT files at once
3. **Data Export** - CSV, Excel formats for further analysis
4. **Calibration** - Auto-tuning of wind_effect_factor based on ride characteristics
5. **Validation Tests** - Unit tests for physics calculations
6. **Performance Plots** - Historical CdA tracking over time
7. **Integration** - Strava/TrainingPeaks API integration
8. **Improvements**:
   - Replace print() debug statements with proper logging
   - Add timeout to weather API calls
   - Fix duplicate dictionary keys
   - Add comprehensive error handling for None types
   - Unit tests for calculation functions

---

## Testing Notes

### Manual Test Scenarios
1. **Flat course with no wind**: Should show stable CdA
2. **Hilly course**: May need adjusted slope_steady_threshold
3. **Windy route**: Wind angle distribution should be clear
4. **Short ride (<30 min)**: May not have enough steady segments
5. **API failure**: Should fall back to default weather gracefully

### Known Test Routes (from config.py)
- Eeklo 2025 (flat, multiple riders)
- Kappelle 2025 (rolling terrain)
- Damme 2025
- Lievegem 2025
- Triathlon courses (transition analysis)

---

## Deployment & Distribution

### Executable Build
- Uses PyInstaller (`CdA-Analyser.spec`)
- One-file executable: `CdA-Analyser.exe`
- Includes all dependencies

### Running from Source
```bash
pip install -r requirements.txt
python src/main.py --gui  # GUI mode
python src/main.py --cli /path/to/file.fit  # CLI mode
```

### CLI Usage
```bash
python src/cli.py test_10.-08.fit -o results.json -v
```

---

## License & Attribution
- **Project**: GNU General Public License v3.0 (GPLv3)
- **Author**: Jorik Wittevrongel
- **Key Dependencies**: fitparse (BSD), folium (MIT), pandas (BSD), numpy (BSD), scipy (BSD), matplotlib (MPLPL), PyQt5 (GPL v3)

---

## Summary Statistics for Code Maintainers

| File | Lines | Purpose | Complexity |
|------|-------|---------|-----------|
| analyzer.py | 1000+ | Core CdA calculations | HIGH |
| qt_gui.py | 800+ | PyQt5 interface | MEDIUM-HIGH |
| fit_parser.py | 80 | FIT file parsing | LOW |
| weather.py | 100 | Weather API interface | LOW-MEDIUM |
| config.py | 120+ | Configuration & profiles | LOW |
| cli.py | 110 | CLI interface | LOW |
| utils.py | 80 | Helper functions | LOW |
| gui.py | 300+ | Tkinter interface (legacy) | MEDIUM |
| main.py | 30 | Entry point | TRIVIAL |
| Scripts | ~300 | Standalone tools | LOW-MEDIUM |

**Total: ~3000+ lines of Python**

---

## End of Analysis

This document provides a comprehensive reference for AI assistants and future developers to understand the CdA Analyzer codebase structure, functionality, and interdependencies.
