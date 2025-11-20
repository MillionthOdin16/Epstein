#!/usr/bin/env python3
"""
Script to download the Epstein Files images from Google Drive.

This script downloads the original JPG scanned documents from the Google Drive
archive. Note: Due to Google Drive API rate limits, downloads may be interrupted.
The script can be run multiple times to resume downloading.
"""

import os
import sys
from pathlib import Path


def download_from_gdrive():
    """
    Download files from Google Drive folder.
    """
    try:
        import gdown
    except ImportError:
        print("Error: gdown package not found.")
        print("Please install it with: pip install gdown")
        sys.exit(1)
    
    # Configuration
    folder_id = "1hTNH5woIRio578onLGElkTWofUSWRoH_"
    folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
    output_dir = Path("data/images/gdrive_download")
    
    print("="*60)
    print("Epstein Files - Google Drive Image Downloader")
    print("="*60)
    print(f"\nSource: {folder_url}")
    print(f"Destination: {output_dir}")
    print("\nNote: Due to Google Drive API rate limits, the download may be")
    print("interrupted after downloading many files. You can run this script")
    print("multiple times to resume downloading.")
    print("\nStarting download...\n")
    
    try:
        # Download the folder
        gdown.download_folder(
            url=folder_url, 
            quiet=False, 
            use_cookies=False, 
            remaining_ok=True,
            output=str(output_dir)
        )
        
        print("\n" + "="*60)
        print("Download completed successfully!")
        print("="*60)
        
        # Count downloaded files
        file_count = sum(1 for _ in output_dir.rglob('*') if _.is_file())
        print(f"\nTotal files downloaded: {file_count}")
        print(f"Files saved to: {output_dir}")
        
    except Exception as e:
        print(f"\n{'='*60}")
        print("Download interrupted or completed")
        print("="*60)
        print(f"\nReason: {e}")
        
        if output_dir.exists():
            file_count = sum(1 for _ in output_dir.rglob('*') if _.is_file())
            print(f"\nFiles downloaded so far: {file_count}")
            print(f"Files saved to: {output_dir}")
            print("\nYou can run this script again to attempt downloading more files.")
        
        # Don't exit with error if we got some files
        if output_dir.exists() and any(output_dir.rglob('*')):
            print("\nPartial download successful.")
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == '__main__':
    download_from_gdrive()
