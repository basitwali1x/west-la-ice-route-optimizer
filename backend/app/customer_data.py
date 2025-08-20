import pandas as pd
from typing import List
from .models import Customer
import os
from .google_sheets_service import GoogleSheetsService
from datetime import datetime, timedelta
import random

def load_west_la_ice_customers() -> List[Customer]:
    """
    Load the West LA Ice customers from the CSV file with coordinates.
    Falls back to Google Sheets sync, then Excel if CSV is not available.
    """
    print(f"Loading customers with DEFAULT_SHEET_ID: {os.getenv('DEFAULT_SHEET_ID')}")
    
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'customer_data_582.csv')
    if os.path.exists(csv_path):
        try:
            import csv
            customers = []
            
            with open(csv_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                for i, row in enumerate(csv_reader):
                    customer_name = row.get('Customer', '').strip()
                    address = row.get('Address', '').strip()
                    depot_assignment = row.get('Depot_Assignment', '').strip()
                    latitude = row.get('Latitude', '')
                    longitude = row.get('Longitude', '')
                    
                    if customer_name and address:
                        if depot_assignment in ['Lufkin', 'Lake Charles', 'Leesville']:
                            depot = depot_assignment
                        elif 'Outside Radius' in depot_assignment:
                            if 'TX' in address:
                                depot = 'Lufkin'
                            elif 'LA' in address:
                                depot = 'Leesville'
                            else:
                                depot = 'Leesville'
                        else:
                            if 'TX' in address and ('Lufkin' in address or 'TX 759' in address):
                                depot = 'Lufkin'
                            elif 'LA' in address and ('Lake Charles' in address or 'LA 706' in address):
                                depot = 'Lake Charles'
                            else:
                                depot = 'Leesville'
                        
                        last_visit = datetime.now() - timedelta(days=random.randint(0, 10))
                        days_since = (datetime.now() - last_visit).days
                        
                        customer = Customer(
                            id=i + 1,
                            name=customer_name,
                            address=address,
                            depot=depot,
                            truck=f"Truck {(i % 8) + 1}",
                            day="Monday",
                            phone="",
                            last_visit_date=last_visit,
                            visited_this_week=random.choice([True, False]),
                            days_since_last_visit=days_since,
                            priority_level="URGENT" if days_since > 7 else "HIGH" if days_since > 5 else "STANDARD",
                            weekly_visit_required=True
                        )
                        customers.append(customer)
            
            print(f"Loaded {len(customers)} customers from CSV file with coordinates")
            if customers:
                return customers
                
        except Exception as e:
            print(f"Error loading from CSV file: {e}")
    
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
                                if 'Lufkin' in address or 'TX 759' in address:
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
    
    print("Falling back to Excel file")
    excel_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'deinjjee.xlsx')
    
    try:
        df = pd.read_excel(excel_path, header=None)
        print(f"Excel file loaded with {len(df)} rows")
        
        customers = []
        depot_mapping = {
            'Leesville': 'Leesville',
            'Lake Charles': 'Lake Charles', 
            'Lufkin': 'Lufkin'
        }
        
        for i, row in df.iterrows():
            try:
                row_str = str(row.iloc[0])
                if pd.isna(row.iloc[0]) or row_str.strip() == '' or row_str == 'Customer,Address,Main Phone,Depot,Truck,Day':
                    continue
                
                fields = [field.strip() for field in row_str.split(',')]
                
                if len(fields) >= 2:
                    customer_name = fields[0] if len(fields) > 0 else f'Customer {i}'
                    address = fields[1] if len(fields) > 1 else ''
                    
                    depot = ''
                    if len(fields) > 3:
                        potential_depot = fields[3]
                        if potential_depot in depot_mapping:
                            depot = potential_depot
                        else:
                            if 'Lufkin' in address or 'TX 759' in address:
                                depot = 'Lufkin'
                            elif 'Lake Charles' in address or 'LA 706' in address:
                                depot = 'Lake Charles'
                            else:
                                depot = 'Leesville'
                    else:
                        if 'Lufkin' in address or 'TX 759' in address:
                            depot = 'Lufkin'
                        elif 'Lake Charles' in address or 'LA 706' in address:
                            depot = 'Lake Charles'
                        else:
                            depot = 'Leesville'
                    
                    last_visit = datetime.now() - timedelta(days=random.randint(0, 10))
                    days_since = (datetime.now() - last_visit).days
                    customer = Customer(
                        id=len(customers) + 1,
                        name=customer_name,
                        address=address,
                        depot=depot,
                        truck=f"Truck {((len(customers)) % 8) + 1}",
                        day="Monday",
                        last_visit_date=last_visit,
                        visited_this_week=random.choice([True, False]),
                        days_since_last_visit=days_since,
                        priority_level="URGENT" if days_since > 7 else "HIGH" if days_since > 5 else "STANDARD",
                        weekly_visit_required=True
                    )
                    customers.append(customer)
                    
            except Exception as e:
                print(f'Error parsing row {i}: {e}')
                continue
        
        print(f"Loaded {len(customers)} customers from Excel")
        return customers
        
    except Exception as e:
        print(f'Error loading Excel file: {e}')
        return []

def get_customer_count() -> int:
    """Return the total number of customers"""
    customers = load_west_la_ice_customers()
    return len(customers)
