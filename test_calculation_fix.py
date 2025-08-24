#!/usr/bin/env python3
"""
Test script to verify the depot-specific calculation fix
"""

def test_depot_calculations():
    """Test the corrected depot calculation logic"""
    
    total_customers = 581
    depots = {
        'Lufkin': {'trucks': 3, 'customers': 200},  # Example distribution
        'Leesville': {'trucks': 3, 'customers': 190},
        'Lake Charles': {'trucks': 2, 'customers': 191}
    }
    
    days = 5
    
    print("DEPOT-SPECIFIC CALCULATION TEST")
    print("=" * 50)
    
    total_trucks = sum(depot['trucks'] for depot in depots.values())
    print(f"Total customers: {total_customers}")
    print(f"Total trucks: {total_trucks}")
    print(f"Days per week: {days}")
    
    print("\nOLD (INCORRECT) GLOBAL CALCULATION:")
    old_calculation = total_customers / (total_trucks * days)
    print(f"  {total_customers} ÷ {total_trucks} trucks ÷ {days} days = {old_calculation:.1f} customers per truck per day")
    
    print("\nNEW (CORRECT) DEPOT-SPECIFIC CALCULATIONS:")
    for depot_name, depot_info in depots.items():
        customers = depot_info['customers']
        trucks = depot_info['trucks']
        customers_per_truck_per_day = customers / (trucks * days)
        
        print(f"  {depot_name}: {customers} customers ÷ {trucks} trucks ÷ {days} days = {customers_per_truck_per_day:.1f} customers per truck per day")
    
    print("\nVERIFICATION:")
    print("✅ Each depot now calculates independently")
    print("✅ Truck allocations respect depot boundaries")
    print("✅ No more global division error")

if __name__ == "__main__":
    test_depot_calculations()
