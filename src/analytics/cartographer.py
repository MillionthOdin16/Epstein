"""
Cartographer Module - Geospatial Correlation

This module links flight logs to meetings by:
1. Extracting airport codes (ICAO/IATA) and city names
2. Cross-referencing locations with dates
3. Generating interactive map visualization
"""

import re
import csv
import sqlite3
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from pathlib import Path
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time

from .database import get_db_connection


class Cartographer:
    """
    Analyzes geospatial correlations in documents.
    """
    
    # Common airport codes (IATA)
    AIRPORT_CODES = {
        'JFK': ('John F. Kennedy International Airport', 40.6413, -73.7781),
        'LAX': ('Los Angeles International Airport', 33.9416, -118.4085),
        'KTEB': ('Teterboro Airport', 40.8501, -74.0608),
        'TJSJ': ('Luis Muñoz Marín International Airport', 18.4394, -66.0018),
        'PBI': ('Palm Beach International Airport', 26.6832, -80.0956),
        'LGA': ('LaGuardia Airport', 40.7769, -73.8740),
        'MIA': ('Miami International Airport', 25.7959, -80.2870),
        'ORD': ('O\'Hare International Airport', 41.9742, -87.9073),
        'ATL': ('Hartsfield-Jackson Atlanta International Airport', 33.6407, -84.4277),
        'DFW': ('Dallas/Fort Worth International Airport', 32.8998, -97.0403),
        'LHR': ('London Heathrow Airport', 51.4700, -0.4543),
        'CDG': ('Charles de Gaulle Airport', 49.0097, 2.5479),
        'NRT': ('Narita International Airport', 35.7720, 140.3929),
        'SFO': ('San Francisco International Airport', 37.6213, -122.3790),
        'BOS': ('Boston Logan International Airport', 42.3656, -71.0096),
    }
    
    def __init__(self, db_path: str = "data/epstein_analysis.db"):
        """
        Initialize the Cartographer.
        
        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        self.locations = []  # List of (location, date, doc_id, doc_hash, page, filename)
        self.geolocator = Nominatim(user_agent="epstein_cartographer")
        self.geocode_cache = {}
    
    def extract_airport_codes(self, text: str) -> List[str]:
        """
        Extract airport codes (ICAO/IATA) from text.
        
        Args:
            text: Document text
            
        Returns:
            List of airport codes
        """
        codes = []
        
        # Pattern for IATA codes (3 letters) and ICAO codes (4 letters)
        patterns = [
            r'\b([A-Z]{4})\b',  # ICAO (e.g., KTEB, TJSJ)
            r'\b([A-Z]{3})\b',  # IATA (e.g., JFK, LAX)
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Check if it's a known airport code
                if match in self.AIRPORT_CODES:
                    codes.append(match)
        
        return list(set(codes))
    
    def extract_city_names(self, text: str) -> List[str]:
        """
        Extract city names from text (simplified version).
        
        Args:
            text: Document text
            
        Returns:
            List of city names
        """
        # Common cities in Epstein case
        cities = [
            'New York', 'Manhattan', 'Palm Beach', 'Miami', 'London',
            'Paris', 'Los Angeles', 'Las Vegas', 'Santa Fe', 'Virgin Islands',
            'Little St. James', 'Great St. James', 'St. Thomas'
        ]
        
        found_cities = []
        text_upper = text.upper()
        
        for city in cities:
            if city.upper() in text_upper:
                found_cities.append(city)
        
        return list(set(found_cities))
    
    def extract_dates(self, text: str) -> List[str]:
        """
        Extract dates from text.
        
        Args:
            text: Document text
            
        Returns:
            List of date strings
        """
        dates = []
        
        # Various date patterns
        patterns = [
            r'\b(\d{1,2}/\d{1,2}/\d{4})\b',  # MM/DD/YYYY
            r'\b(\d{1,2}-\d{1,2}-\d{4})\b',  # MM-DD-YYYY
            r'\b([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})\b',  # Month DD, YYYY
            r'\b(\d{4}-\d{2}-\d{2})\b',  # YYYY-MM-DD
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            dates.extend(matches)
        
        return dates
    
    def geocode_location(self, location: str) -> Optional[Tuple[float, float]]:
        """
        Geocode a location name to coordinates.
        
        Args:
            location: Location name
            
        Returns:
            Tuple of (latitude, longitude) or None
        """
        # Check cache first
        if location in self.geocode_cache:
            return self.geocode_cache[location]
        
        # Check if it's a known airport
        if location in self.AIRPORT_CODES:
            coords = (self.AIRPORT_CODES[location][1], self.AIRPORT_CODES[location][2])
            self.geocode_cache[location] = coords
            return coords
        
        # Try geocoding
        try:
            time.sleep(1)  # Rate limiting
            location_data = self.geolocator.geocode(location)
            if location_data:
                coords = (location_data.latitude, location_data.longitude)
                self.geocode_cache[location] = coords
                return coords
        except (GeocoderTimedOut, GeocoderServiceError):
            pass
        
        self.geocode_cache[location] = None
        return None
    
    def extract_location_data(self, limit: int = None) -> None:
        """
        Extract location and date data from documents.
        
        Args:
            limit: Optional limit on documents to process
        """
        print("Extracting locations and dates from documents...")
        
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        
        # Get all documents
        if limit:
            cursor.execute("SELECT id, filename, source_document_hash, text, page_number FROM documents LIMIT ?", (limit,))
        else:
            cursor.execute("SELECT id, filename, source_document_hash, text, page_number FROM documents")
        
        doc_count = 0
        location_count = 0
        
        for row in cursor.fetchall():
            doc_id = row[0]
            filename = row[1]
            doc_hash = row[2]
            text = row[3]
            page_number = row[4]
            
            # Extract airport codes and city names
            airports = self.extract_airport_codes(text)
            cities = self.extract_city_names(text)
            all_locations = airports + cities
            
            # Extract dates
            dates = self.extract_dates(text)
            
            # Create location-date associations
            if all_locations and dates:
                for location in all_locations:
                    for date in dates:
                        self.locations.append((location, date, doc_id, doc_hash, page_number, filename))
                        location_count += 1
            elif all_locations:
                # Location without specific date
                for location in all_locations:
                    self.locations.append((location, None, doc_id, doc_hash, page_number, filename))
                    location_count += 1
            
            doc_count += 1
            if doc_count % 100 == 0:
                print(f"Processed {doc_count} documents, found {location_count} location mentions")
        
        conn.close()
        
        print(f"\nExtracted {location_count} location mentions from {doc_count} documents")
    
    def generate_map(self, output_path: str = "flight_map.html") -> None:
        """
        Generate interactive map with location pins.
        
        Args:
            output_path: Path to output HTML file
        """
        print(f"\nGenerating interactive map...")
        
        if not self.locations:
            print("Warning: No locations to map")
            return
        
        # Create base map centered on USA
        map_center = [40.0, -95.0]
        flight_map = folium.Map(location=map_center, zoom_start=4)
        
        # Group locations by coordinates
        location_groups = {}
        geocoded_count = 0
        
        for location, date, doc_id, doc_hash, page_number, filename in self.locations:
            coords = self.geocode_location(location)
            if coords:
                key = coords
                if key not in location_groups:
                    location_groups[key] = []
                location_groups[key].append((location, date, doc_id, doc_hash, page_number, filename))
                geocoded_count += 1
        
        print(f"  Geocoded {geocoded_count} locations")
        
        # Add markers for each location
        for coords, mentions in location_groups.items():
            lat, lon = coords
            
            # Create popup text
            location_name = mentions[0][0]
            popup_text = f"<b>{location_name}</b><br>"
            popup_text += f"<b>Mentions: {len(mentions)}</b><br><br>"
            
            # Add up to 10 mentions with dates and sources
            for i, (loc, date, doc_id, doc_hash, page_num, filename) in enumerate(mentions[:10]):
                date_str = date if date else "No date"
                popup_text += f"{i+1}. {date_str}<br>"
                popup_text += f"   Doc: {doc_hash[:12]}..., Page {page_num}<br>"
                popup_text += f"   File: {filename[:30]}...<br>"
            
            if len(mentions) > 10:
                popup_text += f"<br>...and {len(mentions) - 10} more mentions"
            
            # Add marker
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_text, max_width=400),
                tooltip=f"{location_name} ({len(mentions)} mentions)",
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(flight_map)
        
        # Save map
        flight_map.save(output_path)
        print(f"  Map saved with {len(location_groups)} unique locations")
    
    def export_location_report(self, output_path: str = "location_report.csv") -> None:
        """
        Export location data to CSV with source citations.
        
        Args:
            output_path: Path to output CSV file
        """
        print(f"\nExporting location report to: {output_path}")
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Location', 'Date', 'Source Document Hash', 'Page Number', 'Filename'])
            
            for location, date, doc_id, doc_hash, page_number, filename in self.locations:
                date_str = date if date else ''
                writer.writerow([location, date_str, doc_hash, page_number, filename])
        
        print(f"Exported {len(self.locations)} location mentions")
    
    def run_analysis(self, limit: int = None, output_dir: str = ".") -> None:
        """
        Run complete geospatial analysis.
        
        Args:
            limit: Optional limit on documents to process
            output_dir: Directory for output files
        """
        print("="*60)
        print("CARTOGRAPHER - Geospatial Correlation")
        print("="*60)
        
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Extract location data
        self.extract_location_data(limit=limit)
        
        if not self.locations:
            print("\nWARNING: No locations found. Skipping map generation.")
        else:
            # Generate map
            map_path = Path(output_dir) / "flight_map.html"
            self.generate_map(str(map_path))
        
        # Export location report
        report_path = Path(output_dir) / "location_report.csv"
        self.export_location_report(str(report_path))
        
        print("\n" + "="*60)
        print("Geospatial analysis complete!")
        print("="*60)


def main():
    """Main function for running geospatial analysis."""
    cartographer = Cartographer()
    cartographer.run_analysis(output_dir="data/analysis_output")


if __name__ == "__main__":
    main()
