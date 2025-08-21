#!/usr/bin/env python3
"""
Validation script to check for Texas customers incorrectly assigned to Leesville
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.customer_data import load_west_la_ice_customers, haversine_distance

def validate_texas_assignments():
    """Check for Texas customers incorrectly assigned to Leesville"""
    print("Loading customers...")
    customers = load_west_la_ice_customers()
    print(f"Loaded {len(customers)} customers")
    
    depot_coordinates = {
        "Lufkin": (31.3382, -94.7291),
        "Leesville": (31.1435, -93.2609), 
        "Lake Charles": (30.2266, -93.2174)
    }
    
    texas_in_leesville = []
    texas_customers = []
    assignment_summary = {"Lufkin": 0, "Leesville": 0, "Lake Charles": 0}
    
    for customer in customers:
        assignment_summary[customer.depot] += 1
        
        if "tx" in customer.address.lower() or "texas" in customer.address.lower():
            texas_customers.append(customer)
            
            if customer.depot == "Leesville":
                if customer.latitude is not None and customer.longitude is not None:
                    distances = {}
                    for depot, (depot_lat, depot_lng) in depot_coordinates.items():
                        distances[depot] = haversine_distance(customer.latitude, customer.longitude, depot_lat, depot_lng)
                    
                    closest_depot = min(distances, key=distances.get)
                    if closest_depot != "Leesville":
                        texas_in_leesville.append({
                            'customer': customer,
                            'distances': distances,
                            'closest_depot': closest_depot
                        })
                else:
                    texas_in_leesville.append({
                        'customer': customer,
                        'distances': None,
                        'closest_depot': 'Unknown (no coordinates)'
                    })
    
    print(f"\n=== DEPOT ASSIGNMENT SUMMARY ===")
    for depot, count in assignment_summary.items():
        print(f"{depot}: {count} customers")
    
    print(f"\n=== TEXAS CUSTOMER ANALYSIS ===")
    print(f"Total Texas customers found: {len(texas_customers)}")
    
    texas_by_depot = {}
    for customer in texas_customers:
        if customer.depot not in texas_by_depot:
            texas_by_depot[customer.depot] = []
        texas_by_depot[customer.depot].append(customer)
    
    for depot, customers_list in texas_by_depot.items():
        print(f"Texas customers assigned to {depot}: {len(customers_list)}")
    
    print(f"\n=== MISASSIGNED TEXAS CUSTOMERS ===")
    print(f"Texas customers incorrectly assigned to Leesville: {len(texas_in_leesville)}")
    
    if texas_in_leesville:
        print("\nDetails of misassigned customers:")
        for i, item in enumerate(texas_in_leesville[:10]):  # Show first 10
            customer = item['customer']
            distances = item['distances']
            closest = item['closest_depot']
            
            print(f"\n{i+1}. {customer.name}")
            print(f"   Address: {customer.address}")
            print(f"   Current assignment: {customer.depot}")
            print(f"   Closest depot: {closest}")
            if distances:
                print(f"   Distances: Lufkin={distances['Lufkin']:.1f}mi, Leesville={distances['Leesville']:.1f}mi, Lake Charles={distances['Lake Charles']:.1f}mi")
            print(f"   Coordinates: ({customer.latitude}, {customer.longitude})")
        
        if len(texas_in_leesville) > 10:
            print(f"\n... and {len(texas_in_leesville) - 10} more")
    
    return texas_in_leesville

if __name__ == "__main__":
    misassigned = validate_texas_assignments()
    print(f"\n=== VALIDATION RESULT ===")
    if misassigned:
        print(f"❌ Found {len(misassigned)} Texas customers incorrectly assigned to Leesville")
        sys.exit(1)
    else:
        print("✅ All Texas customers are correctly assigned based on geographic proximity")
        sys.exit(0)
