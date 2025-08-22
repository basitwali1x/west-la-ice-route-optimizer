#!/usr/bin/env python3
"""
Validation script to identify misassigned Texas customers
"""
import sys
sys.path.append('.')
from app.customer_data import load_west_la_ice_customers, is_in_texas

def validate_texas_assignments():
    """Test the coordinate-based assignment to ensure no Texas customers in Leesville"""
    print("Loading customers with coordinate-based assignment...")
    customers = load_west_la_ice_customers()
    
    print(f"Total customers loaded: {len(customers)}")
    
    texas_pattern_customers = [c for c in customers if 'tx' in c.address.lower() or 'texas' in c.address.lower()]
    print(f"Customers with TX/Texas in address: {len(texas_pattern_customers)}")
    
    jasper_customers = [c for c in customers if 'jasper' in c.address.lower()]
    print(f"Jasper customers found: {len(jasper_customers)}")
    
    texas_geo_customers = []
    for customer in customers:
        if hasattr(customer, 'latitude') and hasattr(customer, 'longitude'):
            if customer.latitude is not None and customer.longitude is not None:
                if is_in_texas(customer.latitude, customer.longitude):
                    texas_geo_customers.append(customer)
    
    print(f"Customers within Texas geographic boundary: {len(texas_geo_customers)}")
    
    texas_in_leesville_pattern = [c for c in texas_pattern_customers if c.depot == 'Leesville']
    texas_in_leesville_geo = [c for c in texas_geo_customers if c.depot == 'Leesville']
    jasper_in_leesville = [c for c in jasper_customers if c.depot == 'Leesville']
    
    print(f"\n=== VALIDATION RESULTS ===")
    print(f"Texas customers (by address pattern) in Leesville: {len(texas_in_leesville_pattern)}")
    print(f"Texas customers (by geography) in Leesville: {len(texas_in_leesville_geo)}")
    print(f"Jasper customers in Leesville: {len(jasper_in_leesville)}")
    
    jasper_by_depot = {}
    for customer in jasper_customers:
        depot = customer.depot
        if depot not in jasper_by_depot:
            jasper_by_depot[depot] = 0
        jasper_by_depot[depot] += 1
    
    print(f"\nJasper customers by depot: {jasper_by_depot}")
    
    if texas_in_leesville_pattern:
        print(f"\nERROR: Found {len(texas_in_leesville_pattern)} Texas customers assigned to Leesville:")
        for customer in texas_in_leesville_pattern[:5]:  # Show first 5
            print(f"  {customer.name} - {customer.address} - Depot: {customer.depot}")
    
    if jasper_in_leesville:
        print(f"\nERROR: Found {len(jasper_in_leesville)} jasper customers assigned to Leesville:")
        for customer in jasper_in_leesville:
            print(f"  {customer.name} - {customer.address} - Depot: {customer.depot}")
    
    total_texas_in_leesville = len(texas_in_leesville_pattern) + len(texas_in_leesville_geo)
    if total_texas_in_leesville == 0 and len(jasper_in_leesville) == 0:
        print(f"\n✅ SUCCESS: No Texas customers assigned to Leesville depot!")
        print(f"✅ SUCCESS: All jasper addresses correctly assigned to non-Leesville depots!")
        return True
    else:
        print(f"\n❌ FAILURE: {total_texas_in_leesville} Texas customers still assigned to Leesville")
        print(f"❌ FAILURE: {len(jasper_in_leesville)} jasper customers still assigned to Leesville")
        return False

if __name__ == "__main__":
    success = validate_texas_assignments()
    sys.exit(0 if success else 1)
