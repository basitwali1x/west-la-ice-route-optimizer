import pandas as pd
from typing import List
from .models import Customer
import os

def load_west_la_ice_customers() -> List[Customer]:
    """
    Load the 447 West LA Ice customers from the provided Excel file.
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
        
        return customers
        
    except Exception as e:
        print(f'Error loading Excel file: {e}')
        return []

def get_customer_count() -> int:
    """Return the total number of customers"""
    customers = load_west_la_ice_customers()
    return len(customers)
