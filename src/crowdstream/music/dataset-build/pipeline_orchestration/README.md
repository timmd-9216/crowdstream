# CrowdStream Music Dataset Pipeline

A comprehensive Dagster-based pipeline for building music datasets with AI-powered audio separation, harmonic analysis, and intelligent playlist generation.

## 🎯 Overview

This pipeline processes music from Spotify to create rich datasets suitable for DJ applications, music AI research, and intelligent streaming platforms. It combines traditional music analysis with modern machine learning techniques.

### Pipeline Stages

1. **📻 Spotify Sample Download** - Download 30-second previews and metadata
2. **🎚️ Rekordbox Processing** - Extract BPM, key, and phrase analysis  
3. **🎸 Spleeter Audio Separation** - Separate tracks into instrumental stems
4. **📊 Metadata Building** - Combine all data sources into comprehensive metadata
5. **✂️ Audio Segmentation** - Create BPM-synchronized loops and segments
6. **🎵 Final Dataset Generation** - Generate harmonic relationships and playlist algorithms

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.8+
pip install dagster dagster-pandas spotipy pydub librosa pandas

# External tools
pip install spleeter
# OR use Docker: docker pull researchdeezer/spleeter:3.8-5stems

# Optional: FFmpeg for audio processing
brew install ffmpeg  # macOS
# apt-get install ffmpeg  # Ubuntu
```

### Environment Setup

Create a `.env` file or set environment variables:

```bash
# Required
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret

# Optional configuration
CROWDSTREAM_DATA_DIR=data/music
CROWDSTREAM_MIN_BPM=80
CROWDSTREAM_MAX_BPM=145
CROWDSTREAM_USE_DOCKER=false
```

### Installation and Setup

```bash
# Install the pipeline package
pip install -e ".[dev]"

# Validate setup
python cli.py validate

# Run complete pipeline
python cli.py run --stages all

# Check status
python cli.py status
```

## 📋 Usage Options

### Option 1: CLI Interface (Recommended)

```bash
# Show help
python cli.py --help

# Run pipeline stages
python cli.py run --stages all          # All stages
python cli.py run --stages 1,2,3        # Specific stages
python cli.py run --stages 1,2,3 --dry-run  # Preview execution

# Monitor pipeline
python cli.py status                     # Current status
python cli.py report --days 30          # 30-day report

# Validate setup
python cli.py validate
```

### Option 2: Dagster UI

```bash
# Start Dagster UI
dagster dev -f pipeline_definitions.py

# Open browser to http://localhost:3000
# View assets, runs, and monitoring data
```

### Option 3: Programmatic Usage

```python
from dagster import materialize
from assets import stage_1_spotify_download
from resources import SpotifyResource, DataPathsResource

# Setup resources
resources = {
    "spotify": SpotifyResource(
        client_id="your_client_id", 
        client_secret="your_client_secret"
    ),
    "data_paths": DataPathsResource(base_data_dir="data/music")
}

# Run specific stages
result = materialize(
    assets=[stage_1_spotify_download],
    resources=resources
)
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SPOTIPY_CLIENT_ID` | Spotify API Client ID | Required |
| `SPOTIPY_CLIENT_SECRET` | Spotify API Client Secret | Required |
| `CROWDSTREAM_DATA_DIR` | Base data directory | `data/music` |
| `CROWDSTREAM_MIN_BPM` | Minimum BPM for filtering | `80` |
| `CROWDSTREAM_MAX_BPM` | Maximum BPM for filtering | `145` |
| `CROWDSTREAM_USE_DOCKER` | Use Docker for Spleeter | `false` |
| `CROWDSTREAM_MAX_PROCESSES` | Max concurrent processes | `4` |

### Data Structure

```
data/music/
├── artist_catalogue.json          # Artist Spotify URIs
├── track_data/                     # Individual track metadata
├── sample_audio/                   # 30-second samples  
├── sample_audio/stems/             # Separated audio stems
├── sample_audio/loops/             # BPM-synchronized segments
├── rekordbox/collection.xml        # Rekordbox export
├── metadata/                       # Processed metadata
└── metrics/                        # Pipeline metrics
```

## 📊 Pipeline Stages Detail

### Stage 1: Spotify Download
- Requires `artist_catalogue.json` with Spotify URIs
- Downloads 30-second previews and metadata
- Organizes by artist directories

### Stage 2: Rekordbox Processing
- Manual step: Import samples into Rekordbox, analyze, export XML
- Extracts BPM, key, and phrase analysis
- Creates `rekordbox_processed.json`

### Stage 3: Spleeter Separation
- Separates audio into stems (vocals, drums, bass, piano, other)
- Supports local or Docker execution
- Creates high-quality WAV files

### Stage 4: Metadata Building  
- Combines Spotify, Rekordbox, and file system data
- Validates stem generation completeness
- Creates `track_metadata_complete.csv`

### Stage 5: Audio Segmentation
- Creates BPM-synchronized segments (default: 48 beats)
- Applies crossfading for seamless looping
- Filters by BPM range for mixing suitability

### Stage 6: Final Dataset
- Generates harmonic key relationships (Circle of Fifths)
- Creates intelligent playlist recommendations
- Produces final dataset and summary statistics

## 🎛️ Monitoring & Alerts

### Built-in Monitoring
- Execution metrics and success rates
- Data quality validation  
- Error tracking and frequency analysis
- Performance metrics

### Alert Configuration
```bash
# Email alerts
export CROWDSTREAM_SMTP_SERVER=smtp.gmail.com
export CROWDSTREAM_EMAIL_USER=your-email@gmail.com
export CROWDSTREAM_EMAIL_PASSWORD=your-password
export CROWDSTREAM_ALERT_RECIPIENTS=admin@company.com

# Webhook alerts (Slack, Discord, etc.)
export CROWDSTREAM_WEBHOOK_URL=https://hooks.slack.com/services/...
```

## 🚀 Production Deployment

### Docker
```bash
docker build -t crowdstream-pipeline .
docker run -e SPOTIPY_CLIENT_ID=xxx -e SPOTIPY_CLIENT_SECRET=xxx crowdstream-pipeline
```

### Kubernetes CronJob
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: crowdstream-pipeline
spec:
  schedule: "0 2 * * 0"  # Weekly
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: pipeline
            image: crowdstream-pipeline:latest
            env:
            - name: SPOTIPY_CLIENT_ID
              valueFrom:
                secretKeyRef:
                  name: spotify-credentials
                  key: client-id
```

## 🔧 Development

### Adding Dependencies
Add to `setup.py` or `pyproject.toml`

### Testing
```bash
pytest pipeline_orchestration_tests/
```

### Code Quality
```bash
black src/
flake8 src/
```

## 🔍 Troubleshooting

### Common Issues
1. **Spotify Rate Limiting** - Reduce `CROWDSTREAM_MAX_PROCESSES`
2. **Spleeter Memory Issues** - Use Docker mode or reduce concurrency
3. **Missing Dependencies** - Run `python cli.py validate`

### Debug Mode
```bash
export DAGSTER_LOG_LEVEL=DEBUG
python cli.py run --dry-run
```

## 📚 API Reference

### Resources
- `SpotifyResource` - Spotify API client
- `AudioProcessingResource` - Audio utilities
- `DataPathsResource` - Path management
- `SpleeterResource` - Spleeter configuration

### Assets
- `stage_1_spotify_download` through `stage_6_final_metadata`

### Monitoring
- `MetricsCollector` - Pipeline metrics
- `AlertManager` - Error notifications

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.
