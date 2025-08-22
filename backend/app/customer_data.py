import pandas as pd
from typing import List
from .models import Customer
import os
from .google_sheets_service import GoogleSheetsService
from datetime import datetime, timedelta
import random
import math

def calculate_haversine(lat1, lng1, lat2, lng2):
    """Calculate the great circle distance between two points on earth (in miles)"""
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    r = 3956
    return c * r

def assign_depot_by_coordinates(lat, lng):
    """Assign depot based on closest geographic distance"""
    if lat is None or lng is None:
        return 'Leesville'  # Fallback for missing coordinates
        
    depots = {
        "Lufkin": (31.3382, -94.7291),      # Lufkin coordinates
        "Leesville": (31.1435, -93.2609),   # Leesville coordinates
        "Lake Charles": (30.2266, -93.2174) # Lake Charles coordinates
    }
    
    closest_depot = None
    min_distance = float('inf')
    
    for depot, (depot_lat, depot_lng) in depots.items():
        distance = calculate_haversine(lat, lng, depot_lat, depot_lng)
        if distance < min_distance:
            min_distance = distance
            closest_depot = depot
    
    return closest_depot

TEXAS_BOUNDARY = {
    "north": 32.5, "south": 29.0, 
    "west": -95.5, "east": -93.5
}

def is_in_texas(lat, lng):
    """Check if coordinates fall within Texas boundary"""
    if lat is None or lng is None:
        return False
    return (TEXAS_BOUNDARY["south"] <= lat <= TEXAS_BOUNDARY["north"] and
            TEXAS_BOUNDARY["west"] <= lng <= TEXAS_BOUNDARY["east"])

def validate_texas_assignments(depot, address, lat, lng):
    """Ensure Texas addresses don't get assigned to Leesville"""
    address_upper = address.upper()
    is_texas_address = (
        "TX" in address_upper or "TEXAS" in address_upper or 
        "BURKVILLE" in address_upper or is_in_texas(lat, lng)
    )
    
    if is_texas_address and depot == "Leesville":
        if lat is not None and lng is not None:
            return assign_depot_by_coordinates(lat, lng)
        else:
            return 'Lufkin'
    return depot

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
                depot = validate_texas_assignments(depot, excel_customer['address'], None, None)
            else:
                address_key = excel_customer['address'].lower().replace(" ", "").replace(",", "")
                if address_key in coordinates_map:
                    lat = coordinates_map[address_key]['latitude']
                    lng = coordinates_map[address_key]['longitude']
                    depot = assign_depot_by_coordinates(lat, lng)
                    depot = validate_texas_assignments(depot, excel_customer['address'], lat, lng)
                else:
                    address = excel_customer['address'].upper()
                    if any(pattern in address for pattern in [
                        'TX-', 'TX ', 'TEXAS', 'BURKVILLE', 'LUFKIN', 'HUNTINGTON', 'ZAVALLA', 'RATCLIFF', 
                        'TX 759', 'HWY 69', 'TX-7', 'PALESTINE', 'JACKSONVILLE', 
                        'HENDERSON', 'KILGORE', 'NACOGDOCHES', 'LONGVIEW', 
                        'GLADEWATER', 'WHITE OAK', 'HALLSVILLE', 'TATUM', 'JASPER', 'HEMPHILL', 'NEWTON'
                    ]):
                        depot = 'Lufkin'
                    elif any(pattern in address for pattern in [
                        'LAKE CHARLES', 'LA 706', 'CALCASIEU', 'WESTLAKE', 'SULPHUR'
                    ]):
                        depot = 'Lake Charles'
                    else:
                        if 'TEXAS' in address:
                            depot = 'Lufkin'
                        else:
                            depot = 'Leesville'
            
            latitude = None
            longitude = None
            address_key = excel_customer['address'].lower().replace(" ", "").replace(",", "")
            
            if address_key in coordinates_map:
                latitude = coordinates_map[address_key]['latitude']
                longitude = coordinates_map[address_key]['longitude']
                
                if excel_customer['depot'] not in depot_mapping:
                    depot = assign_depot_by_coordinates(latitude, longitude)
                    depot = validate_texas_assignments(depot, excel_customer['address'], latitude, longitude)
            
            last_visit = datetime.now() - timedelta(days=random.randint(0, 10))
            days_since = (datetime.now() - last_visit).days
            
            customer = Customer(
                id=i + 1,
                name=excel_customer['name'],
                address=excel_customer['address'],
                depot=depot,
                truck=f"Truck {(i % 8) + 1}",
                day=None,
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
                                lat = customer_data.get("latitude")
                                lng = customer_data.get("longitude")
                                if lat is not None and lng is not None:
                                    assigned_depot = assign_depot_by_coordinates(float(lat), float(lng))
                                    assigned_depot = validate_texas_assignments(assigned_depot, customer_data["address"], float(lat), float(lng))
                                else:
                                    address = customer_data["address"].upper()
                                    if any(pattern in address for pattern in [
                                        'TX-', 'TX ', 'TEXAS', 'BURKVILLE', 'LUFKIN', 'HUNTINGTON', 'ZAVALLA', 'RATCLIFF', 
                                        'TX 759', 'HWY 69', 'TX-7', 'PALESTINE', 'JACKSONVILLE', 
                                        'HENDERSON', 'KILGORE', 'NACOGDOCHES', 'LONGVIEW', 
                                        'GLADEWATER', 'WHITE OAK', 'HALLSVILLE', 'TATUM', 'JASPER', 'HEMPHILL', 'NEWTON'
                                    ]):
                                        assigned_depot = 'Lufkin'  # All Texas addresses go to Lufkin
                                    elif any(pattern in address for pattern in [
                                        'LAKE CHARLES', 'LA 706', 'CALCASIEU', 'WESTLAKE', 'SULPHUR'
                                    ]):
                                        assigned_depot = 'Lake Charles'
                                    else:
                                        if 'TEXAS' in address:
                                            assigned_depot = 'Lufkin'
                                        else:
                                            assigned_depot = 'Leesville'
                            
                            customer = Customer(
                                id=len(all_customers) + 1,
                                name=customer_data["name"],
                                address=customer_data["address"],
                                depot=assigned_depot,
                                truck=f"Truck {(i % 8) + 1}",
                                day=None,
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

def get_customer_count() -> int:
    """Return the total number of customers"""
    customers = load_west_la_ice_customers()
    return len(customers)
