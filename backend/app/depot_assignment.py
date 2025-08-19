import math
from typing import Tuple
from .google_maps_service import GoogleMapsService

DEPOT_CONSTRAINTS = {
    "Lufkin": {
        "lat_range": (31.3271, 32.6977),
        "lng_range": (-95.6588, -94.0909),
        "max_distance": 100,
        "max_stores": 190,
        "priority_cities": ["Nacogdoches", "Lufkin", "Diboll", "Jacksonville", "Henderson", "Marshall"],
        "coordinates": (31.3279, -94.7323)
    },
    "Leesville": {
        "lat_range": (30.7240, 32.0708),
        "lng_range": (-93.7330, -92.4080),
        "max_distance": 100,
        "max_stores": 190,
        "priority_cities": ["Leesville", "DeRidder", "Alexandria", "Many", "Pineville", "Hornbeck"],
        "coordinates": (31.1436, -93.2577)
    },
    "Lake Charles": {
        "lat_range": (29.8394, 30.5514),
        "lng_range": (-94.3892, -91.7954),
        "max_distance": 100,
        "max_stores": 189,
        "priority_cities": ["Lake Charles", "Sulphur", "Vinton", "Orange", "Jennings", "Lafayette"],
        "coordinates": (30.2266, -93.2174)
    }
}

def _calculate_haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """Calculate distance between two coordinates in miles"""
    lat1, lng1 = coord1
    lat2, lng2 = coord2
    
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat/2) * math.sin(dlat/2) + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dlng/2) * math.sin(dlng/2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return 3959 * c

depot_assignment_counts = {"Lufkin": 0, "Leesville": 0, "Lake Charles": 0}

def reset_depot_counts():
    """Reset depot assignment counts"""
    global depot_assignment_counts
    depot_assignment_counts = {"Lufkin": 0, "Leesville": 0, "Lake Charles": 0}

def assign_depot_by_distance(address: str) -> str:
    """Assign depot based on geographic boundaries, capacity limits, and distance constraints"""
    try:
        maps_service = GoogleMapsService()
        coords = maps_service._generate_realistic_coordinates(address)
        if not coords:
            print(f"DEBUG: No coords for {address}, defaulting to Leesville")
            depot_assignment_counts['Leesville'] += 1
            return 'Leesville'
        
        customer_lat, customer_lng = coords
        
        for depot_name, constraints in DEPOT_CONSTRAINTS.items():
            for city in constraints['priority_cities']:
                if city.lower() in address.lower():
                    if depot_assignment_counts[depot_name] < constraints['max_stores']:
                        depot_assignment_counts[depot_name] += 1
                        print(f"DEBUG: Priority city {city} -> {depot_name} (count: {depot_assignment_counts[depot_name]})")
                        return depot_name
                    else:
                        print(f"DEBUG: Priority city {city} -> {depot_name} FULL (count: {depot_assignment_counts[depot_name]})")
        
        for depot_name, constraints in DEPOT_CONSTRAINTS.items():
            if (constraints["lat_range"][0] <= customer_lat <= constraints["lat_range"][1] and
                constraints["lng_range"][0] <= customer_lng <= constraints["lng_range"][1] and
                depot_assignment_counts[depot_name] < constraints["max_stores"]):
                
                depot_coords = constraints['coordinates']
                distance = _calculate_haversine_distance(depot_coords, (customer_lat, customer_lng))
                
                if distance <= constraints['max_distance']:
                    depot_assignment_counts[depot_name] += 1
                    print(f"DEBUG: Geographic match {depot_name} for ({customer_lat:.4f}, {customer_lng:.4f}) dist={distance:.1f}mi (count: {depot_assignment_counts[depot_name]})")
                    return depot_name
        
        best_depot = None
        min_distance = float('inf')
        
        for depot_name, constraints in DEPOT_CONSTRAINTS.items():
            if depot_assignment_counts[depot_name] < constraints['max_stores']:
                depot_coords = constraints['coordinates']
                distance = _calculate_haversine_distance(depot_coords, (customer_lat, customer_lng))
                
                if distance < min_distance:
                    best_depot = depot_name
                    min_distance = distance
        
        if best_depot:
            depot_assignment_counts[best_depot] += 1
            print(f"DEBUG: Distance fallback {best_depot} for ({customer_lat:.4f}, {customer_lng:.4f}) dist={min_distance:.1f}mi (count: {depot_assignment_counts[best_depot]})")
            return best_depot
        
        min_count_depot = min(depot_assignment_counts.keys(), key=lambda k: depot_assignment_counts[k])
        depot_assignment_counts[min_count_depot] += 1
        print(f"DEBUG: Last resort {min_count_depot} for ({customer_lat:.4f}, {customer_lng:.4f}) (count: {depot_assignment_counts[min_count_depot]})")
        return min_count_depot
        
    except Exception as e:
        print(f'Error geocoding address {address}: {e}')
        depot_assignment_counts['Leesville'] += 1
        return 'Leesville'

def get_depot_assignment_counts():
    """Get current depot assignment counts"""
    return depot_assignment_counts.copy()
