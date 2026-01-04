# BPM Configuration Guide

## Overview

The audio server supports configurable BPM adjustment based on movement detection. All thresholds, BPM targets, and smoothing factors can be configured via a JSON file.

## Configuration File

The default configuration file is `bpm_config.json` in the `audio-mixer/` directory. You can specify a custom path using the `--bpm-config` command-line argument.

### File Structure

```json
{
  "movement_bpm": {
    "movement_max_value": 0.6,
    "thresholds": {
      "very_very_low": 0.02,
      "very_low": 0.05,
      "low": 0.10,
      "medium": 0.10
    },
    "bpm_targets": {
      "very_very_low": 105.0,
      "very_low": 110.0,
      "low": 115.0,
      "medium": 118.0,
      "high_max": 130.0
    },
    "smoothing": {
      "transition_time_seconds": 30.0,
      "audio_loop_rate_hz": 100.0,
      "smoothing_factor_up": 0.96,
      "smoothing_factor_down": 0.92
    }
  }
}
```

## Configuration Parameters

### Movement Thresholds

These define the movement ranges that trigger different BPM targets:

| Threshold | Value | Description |
|-----------|-------|-------------|
| `very_very_low` | 0.02 (2%) | Movement < 2% triggers very very low BPM |
| `very_low` | 0.05 (5%) | Movement 2-5% triggers very low BPM |
| `low` | 0.10 (10%) | Movement 5-10% triggers low BPM |
| `medium` | 0.10 (10%) | Movement >= 10% starts progressive BPM increase |

**Note**: The `medium` threshold is the key value. Movement above this threshold maps progressively from `bpm_targets.medium` to `bpm_targets.high_max`.

### BPM Targets

Target BPM values for each movement range:

| Target | Default | Description |
|--------|---------|-------------|
| `very_very_low` | 105.0 | BPM when movement < 2% |
| `very_low` | 110.0 | BPM when movement 2-5% |
| `low` | 115.0 | BPM when movement 5-10% |
| `medium` | 118.0 | BPM when movement 10%. Also the starting point for progressive increase |
| `high_max` | 130.0 | Maximum BPM when movement is high (>= medium threshold) |

### Progressive BPM Mapping

When movement >= `medium` threshold, BPM maps progressively:

```
movement_range = (max_expected_movement - medium_threshold)
high_movement_factor = (current_movement - medium_threshold) / movement_range
target_bpm = medium + (high_movement_factor * (high_max - medium))
```

**Example**:
- Movement: 18.6%
- Medium threshold: 10%
- Movement above threshold: 8.6%
- Movement range: 50% (60% - 10%)
- Factor: 0.172 (8.6% / 50%)
- Target BPM: 118 + (0.172 * 12) = 120.06 BPM

### Smoothing Configuration

Controls how quickly BPM transitions occur:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `transition_time_seconds` | 30.0 | Target time for transitions to complete (~99% of target) |
| `audio_loop_rate_hz` | 100.0 | Approximate audio loop update rate (used for smoothing calculation) |
| `smoothing_factor_up` | 0.96 | When BPM is decreasing (movement low) - slower decrease |
| `smoothing_factor_down` | 0.92 | When BPM is increasing (movement high) - faster increase |

**Smoothing Factor Calculation**:
```
smoothing_factor_stable = exp(-1 / (transition_time_seconds * audio_loop_rate_hz))
```

The stable factor is calculated automatically. Lower factors (like `smoothing_factor_down`) result in faster transitions.

## Usage

### Using Default Configuration

```bash
python audio_server.py
```

The server will automatically look for `bpm_config.json` in the `audio-mixer/` directory.

### Using Custom Configuration

```bash
python audio_server.py --bpm-config /path/to/custom_config.json
```

### Creating a Custom Configuration

1. Copy `bpm_config.json.example` to `bpm_config.json`
2. Edit the values as needed
3. Restart the audio server

## Example: Making BPM Increase Easier

To make it easier for BPM to increase (lower movement threshold):

```json
{
  "movement_bpm": {
    "thresholds": {
      "medium": 0.08
    }
  }
}
```

This changes the threshold from 10% to 8%, making it easier to trigger BPM increases.

## Example: Faster BPM Transitions

To make BPM changes happen faster:

```json
{
  "movement_bpm": {
    "smoothing": {
      "transition_time_seconds": 15.0,
      "smoothing_factor_down": 0.90
    }
  }
}
```

This reduces transition time to 15 seconds and makes increases even faster.

## Default Values

If the configuration file is missing or invalid, the server uses these defaults:

- `movement_max_value`: 0.6
- `threshold_very_very_low`: 0.02
- `threshold_very_low`: 0.05
- `threshold_low`: 0.10
- `threshold_medium`: 0.10
- `bpm_very_very_low`: 105.0
- `bpm_very_low`: 110.0
- `bpm_low`: 115.0
- `bpm_medium`: 118.0
- `bpm_high_max`: 130.0
- `transition_time_seconds`: 30.0
- `audio_loop_rate_hz`: 100.0
- `smoothing_factor_up`: 0.96
- `smoothing_factor_down`: 0.92

## Troubleshooting

### Configuration Not Loading

If you see "Using default values" in the logs:
1. Check that `bpm_config.json` exists in `audio-mixer/` directory
2. Verify the JSON syntax is valid
3. Check file permissions

### Configuration Changes Not Taking Effect

The configuration is loaded only at server startup. Restart the server after changing the configuration file.

