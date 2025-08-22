import pandas as pd
from typing import List
from .models import Customer
import os
from .google_sheets_service import GoogleSheetsService
from datetime import datetime, timedelta
import random

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
                if ('Lufkin' in address or 'TX' in address or 'Huntington' in address or 
                    'Zavalla' in address or 'Ratcliff' in address or 'TX 759' in address or
                    'Hwy 69' in address or 'TX-7' in address or 'Palestine' in address or
                    'Jacksonville' in address or 'Henderson' in address or 'Kilgore' in address or
                    'Nacogdoches' in address or 'Longview' in address or 'Gladewater' in address or
                    'White Oak' in address or 'Hallsville' in address or 'Tatum' in address):
                    depot = 'Lufkin'
                elif 'Lake Charles' in address or 'LA 706' in address:
                    depot = 'Lake Charles'
                else:
                    depot = 'Leesville'
            
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
                                if ('Lufkin' in address or 'TX' in address or 'Huntington' in address or 
                                    'Zavalla' in address or 'Ratcliff' in address or 'TX 759' in address or
                                    'Hwy 69' in address or 'TX-7' in address or 'Palestine' in address or
                                    'Jacksonville' in address or 'Henderson' in address or 'Kilgore' in address or
                                    'Nacogdoches' in address or 'Longview' in address or 'Gladewater' in address or
                                    'White Oak' in address or 'Hallsville' in address or 'Tatum' in address):
                                    assigned_depot = 'Lufkin'
                                elif 'Lake Charles' in address or 'LA 706' in address:
                                    assigned_depot = 'Lake Charles'
                                else:
                                    assigned_depot = 'Leesville'
                            
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

def get_customer_count() -> int:
    """Return the total number of customers"""
    customers = load_west_la_ice_customers()
    return len(customers)
