#!/usr/bin/env python3
"""
Script to download the Epstein Files dataset from Hugging Face.

This script downloads the EPS_FILES_20K_NOV2025.csv file from the
tensonaut/EPSTEIN_FILES_20K dataset on Hugging Face.
"""

import os
import sys
import urllib.request
from pathlib import Path


def download_with_progress(url, output_path):
    """
    Download a file with progress reporting.
    
    Args:
        url: URL to download from
        output_path: Path to save the downloaded file
    """
    def report_progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(downloaded * 100.0 / total_size, 100.0)
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            print(f"\rDownloading: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end='')
    
    try:
        print(f"Downloading from: {url}")
        urllib.request.urlretrieve(url, output_path, reporthook=report_progress)
        print("\nDownload complete!")
        return True
    except Exception as e:
        print(f"\nError downloading file: {e}")
        return False


def main():
    """Main function to download the dataset."""
    # Configuration
    dataset_url = "https://huggingface.co/datasets/tensonaut/EPSTEIN_FILES_20K/resolve/main/EPS_FILES_20K_NOV2025.csv"
    output_dir = Path("data/raw")
    output_file = output_dir / "EPS_FILES_20K_NOV2025.csv"
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if file already exists
    if output_file.exists():
        response = input(f"File already exists at {output_file}. Overwrite? (y/n): ")
        if response.lower() != 'y':
            print("Download cancelled.")
            return
    
    # Download the file
    print("Starting download of Epstein Files dataset...")
    print(f"Output: {output_file}")
    print("")
    
    success = download_with_progress(dataset_url, output_file)
    
    if success:
        # Verify the download
        file_size = os.path.getsize(output_file)
        print(f"\nFile saved to: {output_file}")
        print(f"File size: {file_size / (1024*1024):.2f} MB")
        print("\nNext steps:")
        print("1. Run 'python3 scripts/organize_data.py' to organize the data")
        print("2. Explore the organized files in 'data/processed/files/'")
    else:
        print("\nDownload failed. Please check your internet connection and try again.")
        sys.exit(1)


if __name__ == '__main__':
    main()
