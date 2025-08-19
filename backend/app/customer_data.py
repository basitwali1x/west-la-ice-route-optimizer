import pandas as pd
from typing import List
from .models import Customer
import os
from .google_sheets_service import GoogleSheetsService
from datetime import datetime, timedelta
import random

def load_west_la_ice_customers() -> List[Customer]:
    """
    Load the West LA Ice customers from the provided Excel file.
    If Google Sheets sync has been performed, use that data instead.
    """
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
                            last_visit = datetime.now() - timedelta(days=random.randint(0, 10))
                            days_since = (datetime.now() - last_visit).days
                            customer = Customer(
                                id=f"{depot}_{i}",
                                name=customer_data["name"],
                                address=customer_data["address"],
                                depot=depot,
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
                
                if all_customers:
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
        
        return customers
        
    except Exception as e:
        print(f'Error loading Excel file: {e}')
        return []

def get_customer_count() -> int:
    """Return the total number of customers"""
    customers = load_west_la_ice_customers()
    return len(customers)
