import pandas as pd
from typing import List
from .models import Customer

def load_west_la_ice_customers() -> List[Customer]:
    """
    Load the 581 West LA Ice customers.
    For now, creating sample data structure that matches the Excel format.
    In production, this would load from the actual Excel file.
    """
    
    customers = []
    
    west_la_addresses = [
        "1234 Wilshire Blvd, Los Angeles, CA 90025",
        "5678 Santa Monica Blvd, West Hollywood, CA 90069",
        "9012 Sunset Blvd, West Hollywood, CA 90069",
        "3456 Beverly Blvd, Los Angeles, CA 90048",
        "7890 Melrose Ave, West Hollywood, CA 90046",
        "2345 Olympic Blvd, Santa Monica, CA 90404",
        "6789 Pico Blvd, Los Angeles, CA 90035",
        "1357 La Cienega Blvd, West Hollywood, CA 90069",
        "2468 Robertson Blvd, Los Angeles, CA 90048",
        "8024 Third Street, Los Angeles, CA 90048",
        "4680 Fairfax Ave, Los Angeles, CA 90036",
        "1122 Doheny Dr, West Hollywood, CA 90069",
        "3344 San Vicente Blvd, Los Angeles, CA 90048",
        "5566 La Brea Ave, Los Angeles, CA 90036",
        "7788 Highland Ave, Los Angeles, CA 90038",
        "9900 Vine St, Los Angeles, CA 90038",
        "1212 Cahuenga Blvd, Los Angeles, CA 90038",
        "3434 Fountain Ave, West Hollywood, CA 90046",
        "5656 Hollywood Blvd, Los Angeles, CA 90028",
        "7878 Franklin Ave, Los Angeles, CA 90046",
        "2020 Vermont Ave, Los Angeles, CA 90027",
        "4242 Western Ave, Los Angeles, CA 90027",
        "6464 Normandie Ave, Los Angeles, CA 90027",
        "8686 Hoover St, Los Angeles, CA 90027",
        "1010 Figueroa St, Los Angeles, CA 90015"
    ]
    
    for i in range(581):
        base_address = west_la_addresses[i % len(west_la_addresses)]
        building_num = 1000 + (i * 10)
        address_parts = base_address.split(' ', 1)
        unique_address = f"{building_num} {address_parts[1]}"
        
        depot_options = ["Leesville", "Lake Charles", "Lufkin"]
        depot_assignment = depot_options[i % 3]
        
        customer = Customer(
            id=i + 1,
            name=f"Customer {i + 1}",
            address=unique_address,
            depot=depot_assignment,
            truck=f"Truck {(i % 8) + 1}",
            day="Monday"
        )
        customers.append(customer)
    
    return customers

def get_customer_count() -> int:
    """Return the total number of customers"""
    return 581
