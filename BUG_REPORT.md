# CdA Analyzer - Bug Report

## Fixed History Summary

### Session 3 (resolved)
- Duplicate `avg_wind_speed` summary key fixed in `analyzer.py`.
- Debug `print()` statements replaced by logging.
- Defensive None checks moved/cleaned where needed.
- Weather API timeout added.
- Distance calculation migrated to vectorized haversine in `fit_parser.py`.
- Negative/very small air speed handling clamped for stability.
- Summary pre-computation optimized to single pass.

### Session 4 (resolved)
- Zero-segment GUI crash (`KeyError`) fixed by guarding empty summary in `analyze_ride()`.
- `_calculate_air_density()` no longer instantiates `WeatherService` per segment.
- Index alignment fixed in `_calculate_acceleration()` and fallback acceleration series.
- Simulation `wind_effect_factor` now always restored via `try/finally`.
- `np.polyfit` guarded in GUI plotting when too few distinct wind angles exist.
- Remaining GUI `print()` calls replaced with logger usage.
- NaN weather display in GUI summary now shows `N/A`.

## Current Open Issues

None from this report. All previously listed open issues were fixed:
- `weather.py`: added `wind_speed_unit='ms'` to Open-Meteo request parameters.
- `fit_parser.py`: replaced global fill with selective fill on safe columns only.
- `cli.py`: analysis-loop failure now retries (`continue`) instead of exiting.
