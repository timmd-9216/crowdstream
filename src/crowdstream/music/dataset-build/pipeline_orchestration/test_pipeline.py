#!/usr/bin/env python3
"""
Test script for CrowdStream Music Dataset Pipeline

This script validates the pipeline setup and runs basic functionality tests.
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import logging

# Add pipeline to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all pipeline modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        from config import PipelineConfig, get_config
        from resources import SpotifyResource, AudioProcessingResource, DataPathsResource
        from assets import (
            stage_1_spotify_download,
            stage_2_rekordbox_processing,
            stage_3_spleeter_processing,
            stage_4_metadata_building,
            stage_5_audio_segmentation,
            stage_6_final_metadata
        )
        from monitoring import MetricsCollector, AlertManager
        from cli import PipelineCLI
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_configuration():
    """Test configuration management."""
    print("🧪 Testing configuration...")
    
    try:
        from config import PipelineConfig, get_config
        
        # Test default configuration
        config = PipelineConfig()
        assert config.base_data_dir == "data/music"
        assert config.min_bpm == 80.0
        assert config.max_bpm == 145.0
        
        # Test configuration validation
        errors = config.validate()
        assert isinstance(errors, list)
        
        # Test data paths
        paths = config.get_data_paths()
        assert 'base' in paths
        assert 'artist_catalogue' in paths
        
        print("✅ Configuration tests passed")
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_resources():
    """Test resource initialization."""
    print("🧪 Testing resources...")
    
    try:
        from resources import SpotifyResource, AudioProcessingResource, DataPathsResource
        
        # Test DataPathsResource
        data_paths = DataPathsResource(base_data_dir="test_data")
        base_path = data_paths.get_base_path()
        assert base_path == Path("test_data")
        
        # Test AudioProcessingResource
        audio_processor = AudioProcessingResource()
        assert audio_processor.default_sample_rate == 44100
        
        # Test audio info calculation
        bpm_segments = audio_processor.calculate_bpm_segments(120.0, 30000)
        assert 'segments' in bpm_segments
        assert bpm_segments['bpm'] == 120.0
        
        print("✅ Resource tests passed")
        return True
    except Exception as e:
        print(f"❌ Resource test failed: {e}")
        return False

def test_monitoring():
    """Test monitoring components."""
    print("🧪 Testing monitoring...")
    
    try:
        from monitoring import MetricsCollector, AlertManager, PipelineMetrics
        
        # Test metrics collector with temporary file
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            metrics_file = f.name
        
        collector = MetricsCollector(metrics_file)
        
        # Test run metrics
        metrics = collector.start_run("test_run_123")
        assert metrics.run_id == "test_run_123"
        assert metrics.status == "running"
        
        # Test asset result update
        collector.update_asset_result("test_asset", True, {"total_tracks": 10})
        assert collector.current_run_metrics.assets_succeeded == 1
        assert collector.current_run_metrics.total_tracks_processed == 10
        
        # Test end run
        collector.end_run("success")
        assert collector.current_run_metrics.status == "success"
        
        # Test alert manager
        alert_manager = AlertManager()
        assert isinstance(alert_manager.email_enabled, bool)
        
        # Cleanup
        Path(metrics_file).unlink(missing_ok=True)
        
        print("✅ Monitoring tests passed")
        return True
    except Exception as e:
        print(f"❌ Monitoring test failed: {e}")
        return False

def test_cli():
    """Test CLI functionality."""
    print("🧪 Testing CLI...")
    
    try:
        from cli import PipelineCLI
        
        # Create CLI instance
        cli = PipelineCLI()
        assert cli.config is not None
        assert len(cli.all_assets) == 6
        assert len(cli.stage_mapping) == 6
        
        # Test resource setup with mock credentials
        import os
        original_env = os.environ.copy()
        try:
            os.environ['SPOTIPY_CLIENT_ID'] = 'test_id'
            os.environ['SPOTIPY_CLIENT_SECRET'] = 'test_secret'
            
            # Recreate CLI with new environment
            cli = PipelineCLI()
            resources = cli.setup_resources()
            assert 'spotify' in resources
            assert 'audio_processor' in resources
            assert 'data_paths' in resources
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)
        
        print("✅ CLI tests passed")
        return True
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False

def test_asset_structure():
    """Test asset structure and dependencies."""
    print("🧪 Testing asset structure...")
    
    try:
        from assets import (
            stage_1_spotify_download,
            stage_2_rekordbox_processing,
            stage_3_spleeter_processing,
            stage_4_metadata_building,
            stage_5_audio_segmentation,
            stage_6_final_metadata
        )
        
        # Test that assets have required attributes
        assets = [
            stage_1_spotify_download,
            stage_2_rekordbox_processing,
            stage_3_spleeter_processing,
            stage_4_metadata_building,
            stage_5_audio_segmentation,
            stage_6_final_metadata
        ]
        
        for asset in assets:
            # Dagster assets are AssetsDefinition objects, not regular functions
            assert hasattr(asset, 'key'), f"Asset {asset} missing key attribute"
            assert hasattr(asset, 'node_def'), f"Asset {asset} missing node_def attribute"
            # Assets should have op definitions
            assert asset.node_def is not None, f"Asset {asset} missing node definition"
        
        print("✅ Asset structure tests passed")
        return True
    except Exception as e:
        print(f"❌ Asset structure test failed: {e}")
        return False

def test_pipeline_definitions():
    """Test pipeline definitions."""
    print("🧪 Testing pipeline definitions...")
    
    try:
        from pipeline_definitions import defs
        from dagster import Definitions
        
        assert isinstance(defs, Definitions)
        assert len(defs.assets) > 0
        assert len(defs.resources) > 0
        
        print("✅ Pipeline definitions tests passed")
        return True
    except Exception as e:
        print(f"❌ Pipeline definitions test failed: {e}")
        return False

def test_data_flow():
    """Test basic data flow logic."""
    print("🧪 Testing data flow...")
    
    try:
        # Test artist catalogue structure
        test_catalogue = {
            "Test Artist": "spotify:artist:test123",
            "Another Artist": "spotify:artist:test456"
        }
        
        # Test that catalogue is valid JSON
        json_str = json.dumps(test_catalogue)
        parsed = json.loads(json_str)
        assert len(parsed) == 2
        
        # Test BPM filtering logic
        from config import PipelineConfig
        config = PipelineConfig(min_bpm=80, max_bpm=145)
        
        test_bpms = [75, 90, 120, 150, 160]
        valid_bpms = [bpm for bpm in test_bpms if config.min_bpm <= bpm <= config.max_bpm]
        assert valid_bpms == [90, 120]
        
        print("✅ Data flow tests passed")
        return True
    except Exception as e:
        print(f"❌ Data flow test failed: {e}")
        return False

def test_file_structure():
    """Test that required files and directories can be created."""
    print("🧪 Testing file structure...")
    
    try:
        from config import PipelineConfig
        
        # Use temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            config = PipelineConfig(base_data_dir=temp_dir, generate_spectrograms=False)
            
            # Test directory creation
            config.ensure_directories()
            
            # Verify main directories exist
            data_paths = config.get_data_paths()
            main_dirs = ['base', 'track_data', 'sample_audio', 'stems', 'loops', 'metadata']
            
            for dir_name in main_dirs:
                if dir_name in data_paths:
                    path = data_paths[dir_name]
                    if isinstance(path, Path):
                        assert path.exists(), f"Directory not created: {path}"
        
        print("✅ File structure tests passed")
        return True
    except Exception as e:
        print(f"❌ File structure test failed: {e}")
        return False

def run_all_tests():
    """Run all tests and return overall result."""
    print("🚀 CrowdStream Pipeline Test Suite")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("Resources", test_resources),
        ("Monitoring", test_monitoring),
        ("CLI", test_cli),
        ("Asset Structure", test_asset_structure),
        ("Pipeline Definitions", test_pipeline_definitions),
        ("Data Flow", test_data_flow),
        ("File Structure", test_file_structure)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            failed += 1
        print()  # Add spacing between tests
    
    print("=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Pipeline is ready to use.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False

def main():
    """Main test runner."""
    success = run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()