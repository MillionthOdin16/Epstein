#!/usr/bin/env python3
"""
Script to compare and analyze data from Hugging Face and Google Drive sources.

This script helps understand the relationship between:
1. Text files (OCR'd) from Hugging Face
2. Image files (original scans) from Google Drive
"""

import csv
import sys
from pathlib import Path
from collections import defaultdict


def analyze_data():
    """Analyze and compare data from both sources."""
    
    print("="*60)
    print("Epstein Files Dataset Analysis")
    print("="*60)
    
    # Analyze CSV data
    csv_path = Path("data/raw/EPS_FILES_20K_NOV2025.csv")
    print(f"\n1. Hugging Face CSV Data: {csv_path}")
    
    if csv_path.exists():
        csv.field_size_limit(sys.maxsize)
        
        text_files = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                text_files.append(row['filename'])
        
        print(f"   Total text files: {len(text_files)}")
        
        # Analyze by category
        categories = defaultdict(int)
        for filename in text_files:
            parts = filename.split('-')
            if len(parts) >= 1:
                category = parts[0]
                categories[category] += 1
        
        print(f"   Categories:")
        for cat, count in sorted(categories.items()):
            print(f"     - {cat}: {count} files")
    else:
        print(f"   ✗ Not found. Run: python3 scripts/download_data.py")
        text_files = []
    
    # Analyze organized text files
    processed_path = Path("data/processed/files")
    print(f"\n2. Organized Text Files: {processed_path}")
    
    if processed_path.exists():
        processed_count = sum(1 for _ in processed_path.rglob('*.txt'))
        print(f"   Total organized files: {processed_count}")
    else:
        print(f"   ✗ Not found. Run: python3 scripts/organize_data.py")
    
    # Analyze Google Drive images
    gdrive_path = Path("data/images/gdrive_images")
    gdrive_alt_path = Path("data/images/Epstein Estate Documents - Seventh Production/IMAGES")
    
    print(f"\n3. Google Drive Images: {gdrive_path}")
    
    # Check both possible locations
    if gdrive_path.exists():
        image_files = list(gdrive_path.rglob('*.jpg'))
        print(f"   Total image files: {len(image_files)}")
    elif gdrive_alt_path.exists():
        image_files = list(gdrive_alt_path.rglob('*.jpg'))
        print(f"   Found in alternative location: {gdrive_alt_path}")
        print(f"   Total image files: {len(image_files)}")
        print(f"   💡 Tip: Reorganize by moving to {gdrive_path}")
    else:
        print(f"   ✗ Not found. Run: python3 scripts/download_images.py")
        image_files = []
    
    if image_files:
        
        # Organize by source
        by_source = defaultdict(int)
        for img in image_files:
            source = img.parent.name
            by_source[source] += 1
        
        print(f"   By source:")
        for source, count in sorted(by_source.items()):
            print(f"     - {source}: {count} files")
        
        # Check correspondence with text files
        if text_files:
            print(f"\n4. Correspondence Analysis:")
            
            # Extract base names from text files
            text_basenames = set()
            for filename in text_files:
                # Remove extension and prefix to get base name
                # e.g., "IMAGES-001-HOUSE_OVERSIGHT_010477.txt" -> "HOUSE_OVERSIGHT_010477"
                parts = filename.rsplit('.', 1)[0].split('-')
                if len(parts) >= 3:
                    basename = '-'.join(parts[2:])
                    text_basenames.add(basename)
            
            # Extract base names from image files
            image_basenames = set()
            for img in image_files:
                basename = img.stem  # filename without extension
                image_basenames.add(basename)
            
            # Find matches
            matches = text_basenames & image_basenames
            text_only = text_basenames - image_basenames
            image_only = image_basenames - text_basenames
            
            print(f"   Files with both text and images: {len(matches)}")
            print(f"   Files with text only: {len(text_only)}")
            print(f"   Files with images only: {len(image_only)}")
            
            if len(matches) > 0:
                print(f"\n   Example matches:")
                for basename in sorted(matches)[:3]:
                    print(f"     - {basename}")
    
    # Check for additional data files
    gdrive_data_path = Path("data/images/gdrive_data")
    gdrive_alt_data_path = Path("data/images/Epstein Estate Documents - Seventh Production/DATA")
    
    print(f"\n4. Additional Data Files: {gdrive_data_path}")
    
    # Check both possible locations
    if gdrive_data_path.exists():
        data_files = list(gdrive_data_path.rglob('*.*'))
        print(f"   Total data files: {len(data_files)}")
        for df in data_files:
            size_mb = df.stat().st_size / (1024 * 1024)
            print(f"     - {df.name} ({size_mb:.2f} MB)")
    elif gdrive_alt_data_path.exists():
        data_files = list(gdrive_alt_data_path.rglob('*.*'))
        print(f"   Found in alternative location: {gdrive_alt_data_path}")
        print(f"   Total data files: {len(data_files)}")
        for df in data_files:
            size_mb = df.stat().st_size / (1024 * 1024)
            print(f"     - {df.name} ({size_mb:.2f} MB)")
        print(f"   💡 Tip: Reorganize by moving to {gdrive_data_path}")
    else:
        print(f"   ✗ Not found")
    
    print(f"\n{'='*60}")
    print("Analysis complete!")
    print("="*60)


if __name__ == '__main__':
    analyze_data()
