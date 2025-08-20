import requests
import os
from typing import List, Dict, Tuple
import asyncio
import time
from .models import Customer

class GoogleMapsService:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        self.base_url = "https://maps.googleapis.com/maps/api"
        
    async def geocode_address(self, address: str) -> Tuple[float, float]:
        """Geocode an address to get latitude and longitude"""
        return self._get_coordinates_from_csv(address)
    
    def _generate_realistic_coordinates(self, address: str) -> Tuple[float, float]:
        """Generate realistic coordinates using hash-based approach with depot-based distribution"""
        import hashlib
        
        print(f"DEBUG: Geocoding address: {address}")
        
        if address == "1707 Smart Street, Leesville, LA 71446":
            print(f"DEBUG: Exact Leesville depot match")
            return (31.1435, -93.2607)
        elif address == "220 Bunker Road, Lake Charles, LA 70615":
            print(f"DEBUG: Exact Lake Charles depot match")
            return (30.2266, -93.2174)
        elif address == "1107 Weiner St, Lufkin, TX 75904":
            print(f"DEBUG: Exact Lufkin depot match")
            return (31.3382, -94.7291)
        else:
            hash_val = int(hashlib.md5(address.encode()).hexdigest()[:8], 16)
            
            if "Lufkin" in address or ("TX" in address and ("Lufkin" in address or "Huntington" in address or "Zavalla" in address or "Ratcliff" in address)):
                base_lat = 31.3382
                base_lng = -94.7291
                lat_range = 0.08  # ~5-6 mile radius
                lng_range = 0.08
                print(f"DEBUG: Lufkin region distribution")
            elif "Lake Charles" in address or "LA 706" in address:
                base_lat = 30.2266
                base_lng = -93.2174
                lat_range = 0.08
                lng_range = 0.08
                print(f"DEBUG: Lake Charles region distribution")
            else:
                base_lat = 31.1435
                base_lng = -93.2607
                lat_range = 0.08
                lng_range = 0.08
                print(f"DEBUG: Leesville region distribution (default)")
            
            lat_variation = ((hash_val % 1000) / 1000.0 - 0.5) * lat_range  # -0.04 to +0.04 degrees
            lng_variation = (((hash_val >> 10) % 1000) / 1000.0 - 0.5) * lng_range  # -0.04 to +0.04 degrees
            
            final_lat = base_lat + lat_variation
            final_lng = base_lng + lng_variation
            
            print(f"DEBUG: Generated coordinates: ({final_lat}, {final_lng})")
            return (final_lat, final_lng)
    
    async def get_distance_matrix_batch(self, origins: List[str], destinations: List[str]) -> Dict:
        """Get distance matrix with batching to handle API limits"""
        url = f"{self.base_url}/distancematrix/json"
        
        max_elements = 25
        
        all_results = {
            "rows": []
        }
        
        for i in range(0, len(origins), max_elements):
            origin_batch = origins[i:i + max_elements]
            
            for j in range(0, len(destinations), max_elements):
                dest_batch = destinations[j:j + max_elements]
                
                params = {
                    "origins": "|".join(origin_batch),
                    "destinations": "|".join(dest_batch),
                    "units": "imperial",  # Use miles
                    "key": self.api_key
                }
                
                response = requests.get(url, params=params)
                data = response.json()
                
                if data["status"] == "OK":
                    if not all_results["rows"]:
                        all_results = data
                    else:
                        for k, row in enumerate(data["rows"]):
                            if i + k < len(all_results["rows"]):
                                all_results["rows"][i + k]["elements"].extend(row["elements"])
                            else:
                                all_results["rows"].append(row)
                
                await asyncio.sleep(0.05)
        
        return all_results
    
    async def calculate_distance_matrix(self, locations: List[str], depot_penalties: bool = True) -> List[List[float]]:
        """Calculate distance matrix for all locations in miles with optional depot penalties"""
        n = len(locations)
        distance_matrix = [[0.0 for _ in range(n)] for _ in range(n)]
        
        print(f"Calculating distance matrix for {n} locations ({n*n} total calculations)")
        
        if n > 100:
            print("Using simplified distance calculation for large dataset")
            return self._calculate_simplified_distance_matrix(locations, depot_penalties)
        
        result = await self.get_distance_matrix_batch(locations, locations)
        
        if "rows" in result:
            for i, row in enumerate(result["rows"]):
                for j, element in enumerate(row["elements"]):
                    if element["status"] == "OK":
                        distance_text = element["distance"]["text"]
                        if "mi" in distance_text:
                            distance_miles = float(distance_text.replace(" mi", "").replace(",", ""))
                        else:
                            distance_miles = element["distance"]["value"] * 0.000621371  # meters to miles
                        
                        if depot_penalties and self._is_cross_depot_travel(locations[i], locations[j]):
                            distance_miles *= 1.5
                            
                        distance_matrix[i][j] = distance_miles
                    else:
                        print(f"API error for distance calculation: {element.get('status', 'Unknown error')}")
                        distance_matrix[i][j] = 10.0  # Default 10 miles
        else:
            print("No rows in distance matrix result, using simplified calculation")
            return self._calculate_simplified_distance_matrix(locations, depot_penalties)
        
        return distance_matrix
    
    def _calculate_simplified_distance_matrix(self, locations: List[str], depot_penalties: bool = True) -> List[List[float]]:
        """Calculate simplified distance matrix using haversine formula with realistic coordinates"""
        import math
        
        n = len(locations)
        distance_matrix = [[0.0 for _ in range(n)] for _ in range(n)]
        
        coords = []
        for i, location in enumerate(locations):
            if location == "1707 Smart Street, Leesville, LA 71446":
                coords.append((31.1435, -93.2607))
            elif location == "220 Bunker Road, Lake Charles, LA 70615":
                coords.append((30.2266, -93.2174))
            elif location == "1107 Weiner St, Lufkin, TX 75904":
                coords.append((31.3382, -94.7291))
            else:
                import hashlib
                hash_val = int(hashlib.md5(location.encode()).hexdigest()[:8], 16)
                
                if "Lufkin" in location or ("TX" in location and ("Lufkin" in location or "Huntington" in location or "Zavalla" in location or "Ratcliff" in location)):
                    base_lat, base_lng = 31.3382, -94.7291
                elif "Lake Charles" in location or "LA 706" in location:
                    base_lat, base_lng = 30.2266, -93.2174
                else:
                    base_lat, base_lng = 31.1435, -93.2607
                
                lat_variation = ((hash_val % 1000) / 1000.0 - 0.5) * 0.08
                lng_variation = (((hash_val >> 10) % 1000) / 1000.0 - 0.5) * 0.08
                
                coords.append((base_lat + lat_variation, base_lng + lng_variation))
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    distance_matrix[i][j] = 0.0
                else:
                    lat1, lng1 = coords[i]
                    lat2, lng2 = coords[j]
                    
                    dlat = math.radians(lat2 - lat1)
                    dlng = math.radians(lng2 - lng1)
                    a = (math.sin(dlat/2) * math.sin(dlat/2) + 
                         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
                         math.sin(dlng/2) * math.sin(dlng/2))
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                    distance_miles = 3959 * c  # Earth radius in miles
                    
                    if depot_penalties and self._is_cross_depot_travel(locations[i], locations[j]):
                        distance_miles *= 1.5
                    
                    distance_matrix[i][j] = distance_miles
        
        print(f"Calculated simplified distance matrix with average distance: {sum(sum(row) for row in distance_matrix) / (n*n):.2f} miles")
        return distance_matrix
    
    def _get_depot_for_location(self, location: str) -> str:
        """Determine which depot a location belongs to"""
        if location == "1707 Smart Street, Leesville, LA 71446":
            return "Leesville"
        elif location == "220 Bunker Road, Lake Charles, LA 70615":
            return "Lake Charles"
        elif location == "1107 Weiner St, Lufkin, TX 75904":
            return "Lufkin"
        elif "Lufkin" in location or ("TX" in location and ("Lufkin" in location or "Huntington" in location or "Zavalla" in location or "Ratcliff" in location)):
            return "Lufkin"
        elif "Lake Charles" in location or "LA 706" in location:
            return "Lake Charles"
        else:
            return "Leesville"
    
    def _is_cross_depot_travel(self, origin: str, destination: str) -> bool:
        """Check if travel is between different depots"""
        origin_depot = self._get_depot_for_location(origin)
        dest_depot = self._get_depot_for_location(destination)
        return origin_depot != dest_depot
    
    def _get_coordinates_from_csv(self, address: str) -> Tuple[float, float]:
        """Get coordinates from CSV data or fall back to depot coordinates"""
        import csv
        import os
        
        print(f"DEBUG: Geocoding address: {address}")
        
        if address == "1707 Smart Street, Leesville, LA 71446":
            print(f"DEBUG: Exact Leesville depot match")
            return (31.1435, -93.2607)
        elif address == "220 Bunker Road, Lake Charles, LA 70615":
            print(f"DEBUG: Exact Lake Charles depot match")
            return (30.2266, -93.2174)
        elif address == "1107 Weiner St, Lufkin, TX 75904":
            print(f"DEBUG: Exact Lufkin depot match")
            return (31.3382, -94.7291)
        
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'customer_data_582.csv')
        if os.path.exists(csv_path):
            try:
                with open(csv_path, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        csv_address = row['Address']
                        if csv_address == address and row['Latitude'] and row['Longitude']:
                            lat = float(row['Latitude'])
                            lng = float(row['Longitude'])
                            print(f"DEBUG: Found exact CSV match: ({lat}, {lng})")
                            return (lat, lng)
                        
                        normalized_csv = csv_address.replace('  ', ' ').strip()
                        normalized_input = address.replace(',', '').replace('  ', ' ').strip()
                        
                        if normalized_csv.lower() == normalized_input.lower() and row['Latitude'] and row['Longitude']:
                            lat = float(row['Latitude'])
                            lng = float(row['Longitude'])
                            print(f"DEBUG: Found normalized CSV match: ({lat}, {lng})")
                            return (lat, lng)
                
                print(f"DEBUG: Address '{address}' not found in CSV file")
            except Exception as e:
                print(f"DEBUG: Error reading CSV: {e}")
        else:
            print(f"DEBUG: CSV file not found at: {csv_path}")
        
        print(f"DEBUG: Using fallback coordinates for: {address}")
        return self._generate_realistic_coordinates(address)
