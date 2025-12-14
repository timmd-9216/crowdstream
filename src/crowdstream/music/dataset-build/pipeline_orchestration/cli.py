#!/usr/bin/env python3
"""
CrowdStream Music Dataset Pipeline CLI

Command-line interface for running and managing the Dagster pipeline
for music dataset building.

Usage:
    python cli.py run --stage all
    python cli.py run --stage 1,2,3
    python cli.py status
    python cli.py report --days 7
    python cli.py validate
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Optional
import time
from datetime import datetime

# Add the pipeline orchestration directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from dagster import materialize, DagsterInstance
from config import get_config, load_config_from_env, PipelineConfig
from monitoring import metrics_collector, alert_manager
from resources import SpotifyResource, AudioProcessingResource, DataPathsResource
from assets import (
    stage_1_spotify_download,
    stage_2_rekordbox_processing,
    stage_3_spleeter_processing,
    stage_4_metadata_building,
    stage_5_audio_segmentation,
    stage_6_final_metadata
)

class PipelineCLI:
    """Command-line interface for the CrowdStream pipeline."""
    
    def __init__(self):
        self.config = load_config_from_env()
        self.all_assets = [
            stage_1_spotify_download,
            stage_2_rekordbox_processing,
            stage_3_spleeter_processing,
            stage_4_metadata_building,
            stage_5_audio_segmentation,
            stage_6_final_metadata
        ]
        
        # Asset mapping for selective execution
        self.stage_mapping = {
            1: stage_1_spotify_download,
            2: stage_2_rekordbox_processing,
            3: stage_3_spleeter_processing,
            4: stage_4_metadata_building,
            5: stage_5_audio_segmentation,
            6: stage_6_final_metadata
        }
    
    def setup_resources(self):
        """Setup Dagster resources."""
        return {
            "spotify": SpotifyResource(
                client_id=self.config.spotify_client_id,
                client_secret=self.config.spotify_client_secret
            ),
            "audio_processor": AudioProcessingResource(
                default_sample_rate=self.config.default_sample_rate,
                crossfade_duration=self.config.crossfade_duration,
                segment_beats=self.config.segment_beats
            ),
            "data_paths": DataPathsResource(
                base_data_dir=self.config.base_data_dir
            )
        }
    
    def run_pipeline(self, stages: Optional[List[int]] = None, dry_run: bool = False):
        """Run the pipeline with specified stages."""
        print("🎵 CrowdStream Music Dataset Pipeline")
        print("=" * 50)
        
        # Validate configuration
        validation_errors = self.config.validate()
        if validation_errors:
            print("❌ Configuration validation failed:")
            for error in validation_errors:
                print(f"   - {error}")
            return False
        
        # Ensure directories exist
        self.config.ensure_directories()
        
        # Determine which assets to run
        if stages is None or 'all' in [str(s).lower() for s in stages]:
            assets_to_run = self.all_assets
            print("📋 Running all pipeline stages (1-6)")
        else:
            assets_to_run = []
            for stage in sorted(stages):
                if stage in self.stage_mapping:
                    assets_to_run.append(self.stage_mapping[stage])
                    asset_name = self.stage_mapping[stage].key.path[-1] if hasattr(self.stage_mapping[stage], 'key') else f"stage_{stage}"
                    print(f"📋 Including Stage {stage}: {asset_name}")
                else:
                    print(f"⚠️  Unknown stage: {stage}")
                    return False
        
        if dry_run:
            print("\n🧪 DRY RUN - No actual processing will occur")
            print(f"Would execute {len(assets_to_run)} assets:")
            for asset in assets_to_run:
                asset_name = asset.key.path[-1] if hasattr(asset, 'key') else str(asset)
                print(f"   - {asset_name}")
            return True
        
        print(f"\n🚀 Starting pipeline execution...")
        print(f"Configuration: {self.config.base_data_dir}")
        
        # Initialize metrics
        run_id = f"cli_run_{int(time.time())}"
        metrics_collector.start_run(run_id)
        
        start_time = time.time()
        
        try:
            # Setup resources
            resources = self.setup_resources()
            
            # Execute pipeline
            result = materialize(
                assets=assets_to_run,
                resources=resources,
                instance=DagsterInstance.ephemeral()
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if result.success:
                print(f"\n✅ Pipeline completed successfully!")
                print(f"⏱️  Duration: {duration:.2f} seconds")
                
                # Print summary statistics
                self._print_execution_summary(result)
                
                metrics_collector.end_run("success")
                return True
            else:
                print(f"\n❌ Pipeline failed!")
                print(f"⏱️  Duration: {duration:.2f} seconds")
                
                metrics_collector.end_run("failed")
                return False
                
        except KeyboardInterrupt:
            print(f"\n⏹️  Pipeline interrupted by user")
            metrics_collector.end_run("interrupted")
            return False
        except Exception as e:
            print(f"\n💥 Pipeline failed with error: {e}")
            metrics_collector.add_error(str(e))
            metrics_collector.end_run("failed")
            return False
    
    def _print_execution_summary(self, result):
        """Print summary of pipeline execution."""
        print("\n📊 Execution Summary:")
        
        if hasattr(result, 'asset_materializations'):
            for materialization in result.asset_materializations:
                asset_name = materialization.asset_key.path[-1]
                print(f"   ✓ {asset_name}")
                
                if materialization.metadata:
                    for key, value in materialization.metadata.items():
                        print(f"      {key}: {value}")
    
    def show_status(self):
        """Show current pipeline status."""
        print("📊 Pipeline Status")
        print("=" * 30)
        
        # Check configuration
        validation_errors = self.config.validate()
        if validation_errors:
            print("❌ Configuration Issues:")
            for error in validation_errors:
                print(f"   - {error}")
        else:
            print("✅ Configuration valid")
        
        # Check data directories
        data_paths = self.config.get_data_paths()
        print(f"\n📁 Data Paths:")
        for name, path in data_paths.items():
            status = "✅" if path.exists() else "❌"
            print(f"   {status} {name}: {path}")
        
        # Check credentials
        print(f"\n🔐 Credentials:")
        spotify_configured = bool(self.config.spotify_client_id and self.config.spotify_client_secret)
        print(f"   {'✅' if spotify_configured else '❌'} Spotify API")
        
        # Recent runs
        recent_metrics = metrics_collector.get_recent_metrics(days=7)
        if recent_metrics:
            print(f"\n📈 Recent Runs (last 7 days): {len(recent_metrics)}")
            for i, metrics in enumerate(recent_metrics[-5:]):  # Show last 5
                status_emoji = "✅" if metrics.status == "success" else "❌"
                duration = f"{metrics.duration_seconds:.1f}s" if metrics.duration_seconds else "ongoing"
                timestamp = datetime.fromtimestamp(metrics.start_time).strftime("%Y-%m-%d %H:%M")
                print(f"   {status_emoji} {timestamp} ({duration}) - {metrics.total_tracks_processed} tracks")
        else:
            print(f"\n📈 No recent runs found")
        
        # Dataset status
        metadata_dir = Path(self.config.base_data_dir) / "metadata"
        final_dataset = metadata_dir / "final_dataset.csv"
        
        if final_dataset.exists():
            import pandas as pd
            try:
                df = pd.read_csv(final_dataset)
                print(f"\n🎵 Current Dataset:")
                print(f"   📻 Total tracks: {len(df)}")
                print(f"   🎤 With samples: {df['has_sample'].sum()} ({(df['has_sample'].sum()/len(df)*100):.1f}%)")
                print(f"   🎸 With stems: {df['has_stems'].sum()} ({(df['has_stems'].sum()/len(df)*100):.1f}%)")
                print(f"   🎹 Mixable tracks: {df['suitable_for_mixing'].sum()}")
            except Exception as e:
                print(f"   ❌ Error reading dataset: {e}")
        else:
            print(f"\n🎵 No dataset found - run pipeline to create")
    
    def generate_report(self, days: int = 7):
        """Generate and display pipeline report."""
        print(f"📋 Pipeline Report (Last {days} days)")
        print("=" * 40)
        
        report = metrics_collector.generate_report(days)
        
        if "error" in report:
            print(f"❌ {report['error']}")
            return
        
        print(f"📊 Execution Statistics:")
        print(f"   Total runs: {report['total_runs']}")
        print(f"   Successful: {report['successful_runs']} ({report['success_rate_percent']}%)")
        print(f"   Failed: {report['failed_runs']}")
        print(f"   Avg duration: {report['average_duration_seconds']:.1f} seconds")
        
        print(f"\n🎵 Processing Statistics:")
        print(f"   Tracks processed: {report['total_tracks_processed']}")
        print(f"   Stems created: {report['total_stems_created']}")
        print(f"   Segments created: {report['total_segments_created']}")
        
        if report['most_common_errors']:
            print(f"\n❌ Most Common Errors:")
            for error, count in report['most_common_errors']:
                print(f"   {count}x: {error[:80]}...")
        
        if report['last_run_time']:
            last_run = datetime.fromtimestamp(report['last_run_time'])
            print(f"\n🕐 Last run: {last_run.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def validate_setup(self):
        """Validate complete pipeline setup."""
        print("🔍 Validating Pipeline Setup")
        print("=" * 35)
        
        all_good = True
        
        # Configuration validation
        print("1. Configuration:")
        errors = self.config.validate()
        if errors:
            all_good = False
            for error in errors:
                print(f"   ❌ {error}")
        else:
            print("   ✅ Configuration valid")
        
        # Dependencies validation
        print("\n2. Dependencies:")
        
        # Check Python packages
        required_packages = [
            'dagster', 'spotipy', 'pydub', 'pandas', 
            'librosa', 'requests', 'ultralytics'
        ]
        
        for package in required_packages:
            try:
                __import__(package)
                print(f"   ✅ {package}")
            except ImportError:
                print(f"   ❌ {package} (not installed)")
                all_good = False
        
        # Check external tools
        print("\n3. External Tools:")
        
        import subprocess
        external_tools = [
            ('spleeter', ['spleeter', '--help']),
            ('ffmpeg', ['ffmpeg', '-version'])
        ]
        
        for tool_name, command in external_tools:
            try:
                result = subprocess.run(command, capture_output=True, timeout=5)
                if result.returncode == 0:
                    print(f"   ✅ {tool_name}")
                else:
                    print(f"   ❌ {tool_name} (not working)")
                    all_good = False
            except (subprocess.TimeoutExpired, FileNotFoundError):
                print(f"   ❌ {tool_name} (not found)")
                all_good = False
        
        # Check file system access
        print("\n4. File System:")
        try:
            self.config.ensure_directories()
            print("   ✅ Can create required directories")
        except Exception as e:
            print(f"   ❌ Cannot create directories: {e}")
            all_good = False
        
        # Check Spotify API
        print("\n5. External APIs:")
        try:
            resources = self.setup_resources()
            spotify_resource = resources['spotify']
            if spotify_resource.validate_credentials():
                print("   ✅ Spotify API")
            else:
                print("   ❌ Spotify API (invalid credentials)")
                all_good = False
        except Exception as e:
            print(f"   ❌ Spotify API: {e}")
            all_good = False
        
        print(f"\n{'✅ Setup validation passed!' if all_good else '❌ Setup validation failed!'}")
        return all_good
    
    def cleanup(self, keep_samples: bool = True):
        """Clean up pipeline data."""
        print("🧹 Cleaning up pipeline data...")
        
        data_paths = self.config.get_data_paths()
        
        # Always safe to remove
        cleanup_paths = [
            data_paths['metadata'] / '*.json',
            data_paths['metadata'] / '*.csv'
        ]
        
        if not keep_samples:
            print("⚠️  Including samples and stems in cleanup")
            cleanup_paths.extend([
                data_paths['sample_audio'],
                data_paths['stems'],
                data_paths['loops']
            ])
        
        # Implement cleanup logic here
        print("🧹 Cleanup completed")

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="CrowdStream Music Dataset Pipeline CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run the pipeline')
    run_parser.add_argument(
        '--stages', 
        type=str, 
        default='all',
        help='Comma-separated stage numbers (1-6) or "all" (default: all)'
    )
    run_parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be executed without running'
    )
    
    # Status command
    subparsers.add_parser('status', help='Show pipeline status')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate pipeline report')
    report_parser.add_argument(
        '--days', 
        type=int, 
        default=7,
        help='Number of days to include in report (default: 7)'
    )
    
    # Validate command
    subparsers.add_parser('validate', help='Validate pipeline setup')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up pipeline data')
    cleanup_parser.add_argument(
        '--keep-samples',
        action='store_true', 
        default=True,
        help='Keep audio samples and stems (default: true)'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = PipelineCLI()
    
    if args.command == 'run':
        # Parse stages
        if args.stages.lower() == 'all':
            stages = None
        else:
            try:
                stages = [int(s.strip()) for s in args.stages.split(',')]
            except ValueError:
                print("❌ Invalid stages format. Use numbers 1-6 separated by commas.")
                return 1
        
        success = cli.run_pipeline(stages=stages, dry_run=args.dry_run)
        return 0 if success else 1
    
    elif args.command == 'status':
        cli.show_status()
        return 0
    
    elif args.command == 'report':
        cli.generate_report(days=args.days)
        return 0
    
    elif args.command == 'validate':
        success = cli.validate_setup()
        return 0 if success else 1
    
    elif args.command == 'cleanup':
        cli.cleanup(keep_samples=args.keep_samples)
        return 0

if __name__ == '__main__':
    sys.exit(main())