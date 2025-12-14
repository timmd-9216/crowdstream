from dagster import Definitions, load_assets_from_modules, EnvVar

# Import the new comprehensive pipeline
from .pipeline_definitions import defs as new_pipeline_defs

# Keep the old modular approach as backup
from . import spotify_assets, metadata_assets, segment_assets, final_assets

# Load legacy assets
legacy_assets = load_assets_from_modules([spotify_assets, metadata_assets, segment_assets, final_assets])

# Use the new comprehensive pipeline by default
defs = new_pipeline_defs

# Alternative: Use legacy modular approach
legacy_defs = Definitions(
    assets=legacy_assets,
)
