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
                                day=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"][i % 5],
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
        df = pd.read_excel(excel_path, sheet_name='all', header=0)
        
        customers = []
        depot_mapping = {
            'Leesville': 'Leesville',
            'Lake Charles': 'Lake Charles', 
            'Lufkin': 'Lufkin'
        }
        
        for i, row in df.iterrows():
            try:
                if pd.isna(row.iloc[0]) or str(row.iloc[0]).strip() == '':
                    continue
                
                customer_name = str(row.iloc[0]).strip() if not pd.isna(row.iloc[0]) else f'Customer {i}'
                address = str(row.iloc[1]).strip() if len(row) > 1 and not pd.isna(row.iloc[1]) else ''
                phone = str(row.iloc[2]).strip() if len(row) > 2 and not pd.isna(row.iloc[2]) else ''
                
                depot = 'Leesville'  # Default
                address_upper = address.upper()
                
                lufkin_keywords = ['LUFKIN', 'TX 759', 'HEMPHILL', 'JASPER', 'ZAVALLA', 'DIBOLL', 'NACOGDOCHES', 
                                 'HUNTINGTON', 'CORRIGAN', 'COLMESNEIL', 'WOODVILLE', 'NEWTON', 'KIRBYVILLE', 
                                 'BUNA', 'SPURGER', 'WARREN', 'CHESTER', 'TYLER', 'CARTHAGE', 'MARSHALL']
                
                lake_charles_keywords = ['LAKE CHARLES', 'LA 706', 'SULPHUR', 'VINTON', 'WESTLAKE', 'MOSS BLUFF',
                                       'IOWA', 'WELSH', 'JENNINGS', 'CAMERON', 'HACKBERRY', 'GRAND CHENIER',
                                       'CREOLE', 'BELL CITY', 'RAGLEY', 'DEQUINCY']
                
                if any(keyword in address_upper for keyword in lufkin_keywords):
                    depot = 'Lufkin'
                elif any(keyword in address_upper for keyword in lake_charles_keywords):
                    depot = 'Lake Charles'
                
                last_visit = datetime.now() - timedelta(days=random.randint(0, 10))
                days_since = (datetime.now() - last_visit).days
                customer = Customer(
                    id=len(customers) + 1,
                    name=customer_name,
                    address=address,
                    depot=depot,
                    truck=f"Truck {((len(customers)) % 8) + 1}",
                    day=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"][len(customers) % 5],
                    phone=phone,
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
