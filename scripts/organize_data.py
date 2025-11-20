#!/usr/bin/env python3
"""
Script to organize the Epstein Files dataset into a structured directory format.

This script reads the EPS_FILES_20K_NOV2025.csv file and extracts each text file
into an organized directory structure based on the file naming convention.
"""

import csv
import os
import sys
from pathlib import Path


def organize_data(csv_path, output_dir):
    """
    Organize CSV data into individual text files.
    
    Args:
        csv_path: Path to the CSV file
        output_dir: Directory to output organized files
    """
    # Increase field size limit for large text fields
    csv.field_size_limit(sys.maxsize)
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Statistics
    stats = {
        'total_files': 0,
        'categories': {},
        'sources': {}
    }
    
    print(f"Reading CSV file: {csv_path}")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            filename = row['filename']
            text = row['text']
            
            # Parse filename to extract category and source
            # Format: CATEGORY-SOURCE-IDENTIFIER.txt
            parts = filename.rsplit('.', 1)[0].split('-')
            
            if len(parts) >= 2:
                category = parts[0]  # e.g., IMAGES, TEXT
                source = parts[1]    # e.g., 001, 005
                
                # Track statistics
                stats['categories'][category] = stats['categories'].get(category, 0) + 1
                stats['sources'][source] = stats['sources'].get(source, 0) + 1
                
                # Create directory structure
                category_dir = output_path / category / source
                category_dir.mkdir(parents=True, exist_ok=True)
                
                # Write file
                file_path = category_dir / filename
            else:
                # If filename doesn't match expected pattern, put in 'uncategorized'
                category_dir = output_path / 'uncategorized'
                category_dir.mkdir(parents=True, exist_ok=True)
                file_path = category_dir / filename
            
            with open(file_path, 'w', encoding='utf-8') as out_file:
                out_file.write(text)
            
            stats['total_files'] += 1
            
            if stats['total_files'] % 1000 == 0:
                print(f"Processed {stats['total_files']} files...")
    
    # Print statistics
    print(f"\n{'='*60}")
    print(f"Organization complete!")
    print(f"{'='*60}")
    print(f"Total files: {stats['total_files']}")
    print(f"\nCategories:")
    for category, count in sorted(stats['categories'].items()):
        print(f"  {category}: {count} files")
    
    print(f"\nSources:")
    for source, count in sorted(stats['sources'].items()):
        print(f"  {source}: {count} files")
    
    print(f"\nFiles organized in: {output_path}")


if __name__ == '__main__':
    # Default paths
    csv_path = 'data/raw/EPS_FILES_20K_NOV2025.csv'
    output_dir = 'data/processed/files'
    
    # Check if CSV file exists
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        print("Please ensure the data has been downloaded first.")
        sys.exit(1)
    
    organize_data(csv_path, output_dir)
    print("\nDone!")
