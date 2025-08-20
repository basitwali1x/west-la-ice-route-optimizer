#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

from app.route_optimizer import RouteOptimizer
from app.models import Customer
from datetime import datetime

def test_fallback_route_constraints():
    """Test that fallback routes respect the 25-stop constraint"""
    optimizer = RouteOptimizer()
    
    customers = []
    for i in range(100):
        customer = Customer(
            id=i + 1,
            name=f"Test Customer {i + 1}",
            address=f"123 Test St {i + 1}, Leesville, LA",
            depot="Leesville",
            truck="L1",
            day="Monday",
            latitude=31.1435 + (i * 0.001),
            longitude=-93.2607 + (i * 0.001),
            last_visit_date=datetime.now(),
            visited_this_week=False,
            days_since_last_visit=1,
            priority_level="STANDARD",
            weekly_visit_required=True
        )
        customers.append(customer)
    
    geocoded_locations = [(31.1435, -93.2607)]  # Depot
    for customer in customers:
        geocoded_locations.append((customer.latitude, customer.longitude))
    
    routes = optimizer._create_fallback_routes(customers, geocoded_locations, 5, "Leesville")
    
    print(f"Created {len(routes)} routes for {len(customers)} customers")
    
    max_stops = 0
    total_customers_assigned = 0
    
    for i, route in enumerate(routes):
        stops = len(route.route_points)
        total_customers_assigned += stops
        max_stops = max(max_stops, stops)
        print(f"Route {i + 1}: {stops} stops")
        
        assert stops <= 25, f"Route {i + 1} has {stops} stops, exceeding 25-stop limit"
    
    print(f"Maximum stops per route: {max_stops}")
    print(f"Total customers assigned: {total_customers_assigned}/{len(customers)}")
    
    assert max_stops <= 25, f"Maximum stops {max_stops} exceeds 25-stop constraint"
    
    print("✅ All fallback routes respect the 25-stop constraint")
    return True

def test_simple_route_constraints():
    """Test that simple routes respect the 25-stop constraint"""
    optimizer = RouteOptimizer()
    
    customers = []
    for i in range(80):
        customer = Customer(
            id=i + 1,
            name=f"Test Customer {i + 1}",
            address=f"123 Test St {i + 1}, Lake Charles, LA",
            depot="Lake Charles",
            truck="LC1",
            day="Monday",
            latitude=30.2266 + (i * 0.001),
            longitude=-93.2174 + (i * 0.001),
            last_visit_date=datetime.now(),
            visited_this_week=False,
            days_since_last_visit=1,
            priority_level="STANDARD",
            weekly_visit_required=True
        )
        customers.append(customer)
    
    routes = optimizer._create_simple_routes(customers, 2, "Lake Charles")
    
    print(f"Created {len(routes)} simple routes for {len(customers)} customers")
    
    max_stops = 0
    total_customers_assigned = 0
    
    for i, route in enumerate(routes):
        stops = len(route.route_points)
        total_customers_assigned += stops
        max_stops = max(max_stops, stops)
        print(f"Simple Route {i + 1}: {stops} stops")
        
        assert stops <= 25, f"Simple Route {i + 1} has {stops} stops, exceeding 25-stop limit"
    
    print(f"Maximum stops per simple route: {max_stops}")
    print(f"Total customers assigned: {total_customers_assigned}/{len(customers)}")
    
    assert max_stops <= 25, f"Maximum stops {max_stops} exceeds 25-stop constraint"
    
    print("✅ All simple routes respect the 25-stop constraint")
    return True

if __name__ == "__main__":
    print("Testing route optimization constraints...")
    test_fallback_route_constraints()
    test_simple_route_constraints()
    print("✅ All constraint tests passed!")
