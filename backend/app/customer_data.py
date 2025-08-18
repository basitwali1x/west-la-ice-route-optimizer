import pandas as pd
from typing import List
from .models import Customer
import os

def load_west_la_ice_customers() -> List[Customer]:
    """
    Load customers from the cleaned CSV file with proper depot assignments.
    """
    csv_path = '/home/ubuntu/attachments/7a9f0714-850a-4dca-96d7-4dfa388e10df/Cleaned_Customer_Data.csv'
    
    try:
        df = pd.read_csv(csv_path)
        customers = []
        
        for i, row in df.iterrows():
            try:
                if pd.isna(row['Customer']) or str(row['Customer']).strip() == '':
                    continue
                
                customer_name = str(row['Customer']).strip()
                address = str(row['Full Address']).strip() if not pd.isna(row['Full Address']) else ''
                csv_depot = str(row['Depot']).strip() if not pd.isna(row['Depot']) else 'Truck 1'
                truck = str(row['Truck']).strip() if not pd.isna(row['Truck']) else 'Monday'
                day = str(row['Day']).strip() if not pd.isna(row['Day']) else ''
                
                if csv_depot.startswith('Truck'):
                    truck = csv_depot
                    day = truck if not truck.startswith('Truck') else 'Monday'
                
                if truck == 'Truck 1' or 'Lufkin' in address or 'TX' in address:
                    depot = 'Lufkin'
                elif truck in ['Truck 2', 'Truck 3'] or 'Lake Charles' in address or any(lc_indicator in address for lc_indicator in ['LC', 'Sulphur', 'Moss Bluff', 'Westlake']):
                    depot = 'Lake Charles'
                    if truck not in ['Truck 2', 'Truck 3']:
                        truck = 'Truck 2'
                else:
                    depot = 'Leesville'
                
                customer = Customer(
                    id=len(customers) + 1,
                    name=customer_name,
                    address=address,
                    depot=depot,
                    truck=truck,
                    day=day
                )
                customers.append(customer)
                    
            except Exception as e:
                print(f'Error parsing row {i}: {e}')
                continue
        
        print(f"Loaded {len(customers)} customers from cleaned CSV")
        return customers
        
    except Exception as e:
        print(f'Error loading CSV file: {e}')
        return load_west_la_ice_customers_excel()

def load_west_la_ice_customers_excel() -> List[Customer]:
    """
    Fallback function to load customers from Excel file.
    """
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
        
        print(f"Loaded {len(customers)} customers from Excel (fallback)")
        return customers
        
    except Exception as e:
        print(f'Error loading Excel file: {e}')
        return []

def get_customer_count() -> int:
    """Return the total number of customers"""
    customers = load_west_la_ice_customers()
    return len(customers)
