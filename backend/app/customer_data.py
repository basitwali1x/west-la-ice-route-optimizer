import pandas as pd
from typing import List
from .models import Customer
import os
import csv
from .google_sheets_service import GoogleSheetsService
from .depot_assignment import assign_depot_by_distance, reset_depot_counts, get_depot_assignment_counts

def load_customers_from_csv() -> List[Customer]:
    """Load customers from the reference CSV files provided by the user"""
    csv_files = [
        "/home/ubuntu/attachments/c263ce9f-10e6-4723-87f0-351d46a14b89/google_maps_lake_charles_route_581+1.csv",
        "/home/ubuntu/attachments/e8f3dbd4-95c8-4ae9-8faf-271b40553d4b/google_maps_leesville_route_581.csv", 
        "/home/ubuntu/attachments/1c1f438c-bb34-45d0-99df-bbc2b2dfa016/google_maps_lufkin_route_581.csv"
    ]
    
    customers = []
    customer_id = 1
    
    for csv_file in csv_files:
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('type') == 'customer' and row.get('address'):
                        address = row['address'].strip()
                        name = row.get('name', f'Customer {customer_id}').strip()
                        
                        assigned_depot = assign_depot_by_distance(address)
                        
                        customer = Customer(
                            id=customer_id,
                            name=name,
                            address=address,
                            depot=assigned_depot,
                            truck=f"Truck {((customer_id - 1) % 8) + 1}",
                            day="Monday"
                        )
                        customers.append(customer)
                        customer_id += 1
                        
        except Exception as e:
            print(f"Error reading CSV file {csv_file}: {e}")
            continue
    
    return customers

def load_west_la_ice_customers() -> List[Customer]:
    """
    Load the West LA Ice customers from the provided CSV files.
    If Google Sheets sync has been performed, use that data instead.
    """
    reset_depot_counts()
    sheet_id = os.getenv("DEFAULT_SHEET_ID")
    if sheet_id:
        try:
            sheets_service = GoogleSheetsService()
            sheet_data = sheets_service.sync_from_sheets(sheet_id)
            
            if "customers" in sheet_data and not isinstance(sheet_data.get("error", None), str):
                all_customers = []
                for depot, depot_customers in sheet_data["customers"].items():
                    for i, customer_data in enumerate(depot_customers):
                        if customer_data.get("name") and customer_data.get("address"):
                            assigned_depot = assign_depot_by_distance(customer_data["address"])
                            
                            customer = Customer(
                                id=f"{assigned_depot}_{i}",
                                name=customer_data["name"],
                                address=customer_data["address"],
                                depot=assigned_depot,
                                truck=f"Truck {(i % 8) + 1}",
                                day="Monday",
                                phone=customer_data.get("phone", "")
                            )
                            all_customers.append(customer)
                
                if all_customers:
                    counts = get_depot_assignment_counts()
                    print(f"Loaded {len(all_customers)} customers from Google Sheets")
                    print(f"Final depot distribution: Lufkin: {counts['Lufkin']}, Lake Charles: {counts['Lake Charles']}, Leesville: {counts['Leesville']}")
                    return all_customers
        except Exception as e:
            print(f"Error loading from Google Sheets: {e}")
    
    customers = load_customers_from_csv()
    if customers:
        counts = get_depot_assignment_counts()
        print(f"Loaded {len(customers)} customers from CSV files")
        print(f"Final depot distribution: Lufkin: {counts['Lufkin']}, Lake Charles: {counts['Lake Charles']}, Leesville: {counts['Leesville']}")
        return customers
    
    excel_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'deinjjee.xlsx')
    
    try:
        df = pd.read_excel(excel_path, header=None)
        
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
                    
                    depot = assign_depot_by_distance(address)
                    
                    customer = Customer(
                        id=len(customers) + 1,
                        name=customer_name,
                        address=address,
                        depot=depot,
                        truck=f"Truck {((len(customers)) % 8) + 1}",
                        day="Monday"
                    )
                    customers.append(customer)
                    
            except Exception as e:
                print(f'Error parsing row {i}: {e}')
                continue
        
        counts = get_depot_assignment_counts()
        print(f"Loaded {len(customers)} customers from Excel file")
        print(f"Final depot distribution: Lufkin: {counts['Lufkin']}, Lake Charles: {counts['Lake Charles']}, Leesville: {counts['Leesville']}")
        return customers
        
    except Exception as e:
        print(f'Error loading Excel file: {e}')
        return []

def get_customer_count() -> int:
    """Return the total number of customers"""
    customers = load_west_la_ice_customers()
    return len(customers)
