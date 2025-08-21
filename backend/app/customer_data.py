import pandas as pd
from typing import List
from .models import Customer
import os
from .google_sheets_service import GoogleSheetsService
from datetime import datetime, timedelta
import random
import math

def load_west_la_ice_customers() -> List[Customer]:
    """
    Load West LA Ice customers using hybrid approach:
    - Excel file for real business names
    - Google Sheets for coordinates
    """
    print(f"Loading customers with hybrid approach, DEFAULT_SHEET_ID: {os.getenv('DEFAULT_SHEET_ID')}")
    
    excel_customers = []
    excel_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'deinjjee.xlsx')
    
    if os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path, header=None)
            print(f"Excel file loaded with {len(df)} rows")
            
            for i, row in df.iterrows():
                try:
                    row_str = str(row.iloc[0])
                    if pd.isna(row.iloc[0]) or row_str.strip() == '' or row_str == 'Customer,Address,Main Phone,Depot,Truck,Day':
                        continue
                    
                    fields = [field.strip() for field in row_str.split(',')]
                    
                    if len(fields) >= 2:
                        customer_name = fields[0] if len(fields) > 0 else f'Customer {i}'
                        address = fields[1] if len(fields) > 1 else ''
                        phone = fields[2] if len(fields) > 2 else ""
                        depot = fields[3] if len(fields) > 3 else ""
                        
                        if customer_name and address:
                            excel_customers.append({
                                'name': customer_name,
                                'address': address,
                                'phone': phone,
                                'depot': depot
                            })
                            
                except Exception as e:
                    print(f'Error parsing Excel row {i}: {e}')
                    continue
            
            print(f"Loaded {len(excel_customers)} customers from Excel with real names")
        except Exception as e:
            print(f'Error loading Excel file: {e}')
    
    coordinates_map = {}
    sheet_id = os.getenv("DEFAULT_SHEET_ID")
    if sheet_id:
        try:
            sheets_service = GoogleSheetsService()
            sheet_data = sheets_service.sync_from_sheets(sheet_id)
            
            if "customers" in sheet_data and not isinstance(sheet_data.get("error", None), str):
                for depot, depot_customers in sheet_data["customers"].items():
                    for customer_data in depot_customers:
                        if customer_data.get("address") and customer_data.get("latitude") and customer_data.get("longitude"):
                            address_key = customer_data["address"].lower().replace(" ", "").replace(",", "")
                            coordinates_map[address_key] = {
                                'latitude': float(customer_data["latitude"]),
                                'longitude': float(customer_data["longitude"])
                            }
                
                print(f"Loaded coordinates for {len(coordinates_map)} addresses from Google Sheets")
        except Exception as e:
            print(f"Error loading coordinates from Google Sheets: {e}")
    
    customers = []
    depot_mapping = {
        'Leesville': 'Leesville',
        'Lake Charles': 'Lake Charles', 
        'Lufkin': 'Lufkin'
    }
    
    for i, excel_customer in enumerate(excel_customers):
        try:
            depot = ''
            if excel_customer['depot'] in depot_mapping:
                depot = excel_customer['depot']
            else:
                address = excel_customer['address']
                address_key = address.lower().replace(" ", "").replace(",", "")
                if address_key in coordinates_map:
                    customer_lat = coordinates_map[address_key]['latitude']
                    customer_lng = coordinates_map[address_key]['longitude']
                    depot = assign_depot_by_pattern_with_proximity_fallback(address, customer_lat, customer_lng)
                else:
                    depot = assign_depot_by_pattern_with_proximity_fallback(address)
            
            latitude = None
            longitude = None
            address_key = excel_customer['address'].lower().replace(" ", "").replace(",", "")
            
            if address_key in coordinates_map:
                latitude = coordinates_map[address_key]['latitude']
                longitude = coordinates_map[address_key]['longitude']
            
            last_visit = datetime.now() - timedelta(days=random.randint(0, 10))
            days_since = (datetime.now() - last_visit).days
            
            customer = Customer(
                id=i + 1,
                name=excel_customer['name'],
                address=excel_customer['address'],
                depot=depot,
                truck=f"Truck {(i % 8) + 1}",
                day="Monday",
                phone=excel_customer['phone'],
                last_visit_date=last_visit,
                visited_this_week=random.choice([True, False]),
                days_since_last_visit=days_since,
                priority_level="URGENT" if days_since > 7 else "HIGH" if days_since > 5 else "STANDARD",
                weekly_visit_required=True
            )
            customers.append(customer)
            
        except Exception as e:
            print(f'Error creating customer {i}: {e}')
            continue
    
    print(f"Created {len(customers)} customers with hybrid approach (names from Excel, coordinates from Google Sheets)")
    
    if customers:
        return customers
    
    sheet_id = os.getenv("DEFAULT_SHEET_ID")
    if sheet_id:
        try:
            sheets_service = GoogleSheetsService()
            sheet_data = sheets_service.sync_from_sheets(sheet_id)
            
            print(f"Google Sheets response: {type(sheet_data)}, keys: {sheet_data.keys() if isinstance(sheet_data, dict) else 'Not a dict'}")
            
            if "customers" in sheet_data and not isinstance(sheet_data.get("error", None), str):
                all_customers = []
                for depot, depot_customers in sheet_data["customers"].items():
                    print(f"Processing depot '{depot}' with {len(depot_customers)} customers")
                    for i, customer_data in enumerate(depot_customers):
                        if customer_data.get("name") and customer_data.get("address"):
                            last_visit = datetime.now() - timedelta(days=random.randint(0, 10))
                            days_since = (datetime.now() - last_visit).days
                            
                            assigned_depot = customer_data.get("depot", depot)
                            if assigned_depot == "all":
                                address = customer_data["address"]
                                customer_lat = customer_data.get("latitude")
                                customer_lng = customer_data.get("longitude")
                                if customer_lat is not None and customer_lng is not None:
                                    assigned_depot = assign_depot_by_pattern_with_proximity_fallback(address, float(customer_lat), float(customer_lng))
                                else:
                                    assigned_depot = assign_depot_by_pattern_with_proximity_fallback(address)
                            
                            customer = Customer(
                                id=len(all_customers) + 1,
                                name=customer_data["name"],
                                address=customer_data["address"],
                                depot=assigned_depot,
                                truck=f"Truck {(i % 8) + 1}",
                                day="Monday",
                                phone=customer_data.get("phone", ""),
                                last_visit_date=last_visit,
                                visited_this_week=random.choice([True, False]),
                                days_since_last_visit=days_since,
                                priority_level="URGENT" if days_since > 7 else "HIGH" if days_since > 5 else "STANDARD",
                                weekly_visit_required=True
                            )
                            all_customers.append(customer)
                
                print(f"Loaded {len(all_customers)} customers from Google Sheets")
                if all_customers:
                    return all_customers
            else:
                print(f"Google Sheets error or no customers: {sheet_data.get('error', 'No customers found')}")
        except Exception as e:
            print(f"Error loading from Google Sheets: {e}")
    
    return []

def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate the great circle distance between two points on Earth in miles"""
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat/2) * math.sin(dlat/2) + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dlng/2) * math.sin(dlng/2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return 3959 * c  # Earth radius in miles

def assign_depot_by_proximity(customer_lat: float, customer_lng: float) -> str:
    """Assign depot based on closest geographic distance"""
    depot_coordinates = {
        "Lufkin": (31.3382, -94.7291),
        "Leesville": (31.1435, -93.2609), 
        "Lake Charles": (30.2266, -93.2174)
    }
    
    closest_depot = None
    min_distance = float('inf')
    
    for depot, (depot_lat, depot_lng) in depot_coordinates.items():
        distance = haversine_distance(customer_lat, customer_lng, depot_lat, depot_lng)
        if distance < min_distance:
            min_distance = distance
            closest_depot = depot
    
    return closest_depot

def assign_depot_by_pattern_with_proximity_fallback(address: str, customer_lat: float = None, customer_lng: float = None) -> str:
    """Assign depot using geographic proximity when coordinates available, fallback to improved pattern matching"""
    if customer_lat is not None and customer_lng is not None:
        assigned_depot = assign_depot_by_proximity(customer_lat, customer_lng)
        print(f"DEBUG: Geographic assignment for {address}: {assigned_depot}")
        return assigned_depot
    
    address_lower = address.lower()
    
    texas_indicators = [
        'tx-', 'texas', 'zavalla', 'ratcliff', 'hemphill', 'newton', 
        'huntington', 'tx 759', 'lufkin', 'jasper', 'angelina', 
        'nacogdoches', 'polk', 'tyler', 'texas highway', 'texas hwy',
        ' tx ', 'burkville'
    ]
    
    lake_charles_indicators = ['lake charles', 'la 706']
    
    if any(indicator in address_lower for indicator in texas_indicators):
        print(f"DEBUG: Texas indicator detected in {address}, assigning to Lufkin")
        return 'Lufkin'
    
    elif any(indicator in address_lower for indicator in lake_charles_indicators):
        print(f"DEBUG: Lake Charles indicator detected in {address}, assigning to Lake Charles")
        return 'Lake Charles'
    
    else:
        print(f"DEBUG: Pattern fallback assignment for {address}: Leesville")
        return 'Leesville'

def get_customer_count() -> int:
    """Return the total number of customers"""
    customers = load_west_la_ice_customers()
    return len(customers)
