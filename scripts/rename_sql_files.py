#!/usr/bin/env python3
"""
Rename SQL files to follow the layered naming convention.
Pattern: {layer}{sequence}_{layer_name}_{description}.sql
"""
import os
import re
from pathlib import Path

# Define layer mappings
LAYERS = {
    "10_raw": {"prefix": "10", "name": "raw"},
    "20_staging": {"prefix": "20", "name": "stg"},
    "30_core": {"prefix": "30", "name": "core"},
    "40_bridge": {"prefix": "40", "name": "bridge"},
    "50_features": {"prefix": "50", "name": "features"},
    "60_models": {"prefix": "60", "name": "models"},
    "70_serving": {"prefix": "70", "name": "serving"},
    "80_quality": {"prefix": "80", "name": "quality"},
}

def clean_filename(filename):
    """Remove numeric prefixes and clean up the filename."""
    # Remove .sql extension for processing
    base = filename.replace('.sql', '')
    # Remove leading numeric prefixes (001_, 200_, etc.)
    base = re.sub(r'^[0-9]+_', '', base)
    # Remove redundant layer indicators
    base = re.sub(r'^(raw_|external_|stg_|core_|bridge_|features_|models_|serving_|quality_)', '', base)
    return base

def rename_files_in_layer(layer_dir, dry_run=True):
    """Rename files in a layer directory."""
    sql_path = Path("/home/cbwinslow/workspace/retrosheet/sql")
    layer_path = sql_path / layer_dir
    
    if not layer_path.exists():
        print(f"Layer {layer_dir} does not exist, skipping...")
        return
    
    config = LAYERS[layer_dir]
    files = sorted([f for f in layer_path.iterdir() if f.is_file() and f.suffix == '.sql'])
    
    print(f"\n=== {layer_dir} ({len(files)} files) ===")
    
    for i, filepath in enumerate(files, 1):
        old_name = filepath.name
        clean_base = clean_filename(old_name)
        new_name = f"{config['prefix']}{i:02d}_{config['name']}_{clean_base}.sql"
        
        if old_name != new_name:
            print(f"  {old_name}")
            print(f"    -> {new_name}")
            if not dry_run:
                filepath.rename(layer_path / new_name)
        else:
            print(f"  {old_name} (no change)")

def main():
    import sys
    dry_run = "--execute" not in sys.argv
    
    print(f"SQL File Renamer {'(DRY RUN - add --execute to apply)' if dry_run else '(EXECUTING)'}")
    print("=" * 60)
    
    for layer_dir in LAYERS.keys():
        rename_files_in_layer(layer_dir, dry_run)
    
    if dry_run:
        print("\n" + "=" * 60)
        print("This was a dry run. Add --execute to apply changes.")

if __name__ == "__main__":
    main()
