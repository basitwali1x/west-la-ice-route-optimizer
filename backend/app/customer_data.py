import pandas as pd
from typing import List
from .models import Customer
import os
from .google_sheets_service import GoogleSheetsService
from .depot_assignment import assign_depot_by_distance, reset_depot_counts, get_depot_assignment_counts

def load_west_la_ice_customers() -> List[Customer]:
    """
    Load the West LA Ice customers from the provided Excel file.
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
                    
                    depot = ''
                    if len(fields) > 3:
                        potential_depot = fields[3]
                        if potential_depot in depot_mapping:
                            depot = potential_depot
                        else:
                            depot = assign_depot_by_distance(address)
                    else:
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
