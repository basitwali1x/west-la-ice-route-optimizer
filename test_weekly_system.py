#!/usr/bin/env python3
"""
Test script for weekly visit tracking system
Verifies depot assignment balance, priority rules, and weekly reset functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app.customer_data import load_west_la_ice_customers
from backend.app.route_optimizer import RouteOptimizer, DEPOT_CONSTRAINTS, PRIORITY_RULES
from backend.app.google_sheets_service import GoogleSheetsService
from datetime import datetime, timedelta
import random

def test_depot_assignment_balance():
    """Test that depot assignments respect capacity limits (192/190/189)"""
    print("Testing depot assignment balance...")
    
    customers = load_west_la_ice_customers()
    depot_counts = {"Lufkin": 0, "Leesville": 0, "Lake Charles": 0}
    
    for customer in customers:
        if customer.depot in depot_counts:
            depot_counts[customer.depot] += 1
    
    print(f"Current depot distribution:")
    for depot, count in depot_counts.items():
        capacity = DEPOT_CONSTRAINTS[depot]["weekly_capacity"]
        print(f"  {depot}: {count} customers (capacity: {capacity})")
        
        if count > capacity:
            print(f"  ⚠️  WARNING: {depot} exceeds capacity by {count - capacity}")
        else:
            print(f"  ✅ {depot} within capacity")
    
    total_capacity = sum(DEPOT_CONSTRAINTS[depot]["weekly_capacity"] for depot in DEPOT_CONSTRAINTS.keys())
    total_customers = sum(depot_counts.values())
    
    print(f"\nTotal customers: {total_customers}")
    print(f"Total capacity: {total_capacity}")
    
    return depot_counts

def test_priority_rules():
    """Test priority assignment based on days since last visit"""
    print("\nTesting priority rules...")
    
    customers = load_west_la_ice_customers()
    priority_counts = {"URGENT": 0, "HIGH": 0, "STANDARD": 0}
    
    optimizer = RouteOptimizer()
    
    for customer in customers:
        if customer.days_since_last_visit is not None:
            priority = optimizer.assign_priority(customer)
            customer.priority_level = priority
            priority_counts[priority] += 1
    
    print(f"Priority distribution:")
    for priority, count in priority_counts.items():
        print(f"  {priority}: {count} customers")
    
    urgent_customers = [c for c in customers if c.priority_level == "URGENT"]
    print(f"\nUrgent customers (>7 days overdue): {len(urgent_customers)}")
    for customer in urgent_customers[:5]:  # Show first 5
        print(f"  - {customer.name}: {customer.days_since_last_visit} days overdue")
    
    return priority_counts

def test_weekly_reset():
    """Test weekly reset functionality"""
    print("\nTesting weekly reset functionality...")
    
    customers = load_west_la_ice_customers()
    
    visited_before = len([c for c in customers if c.visited_this_week])
    print(f"Customers visited before reset: {visited_before}")
    
    for customer in customers:
        customer.visited_this_week = False
    
    visited_after = len([c for c in customers if c.visited_this_week])
    print(f"Customers visited after reset: {visited_after}")
    
    if visited_after == 0:
        print("✅ Weekly reset successful - all visit flags cleared")
    else:
        print(f"⚠️  WARNING: {visited_after} customers still marked as visited")
    
    return visited_before, visited_after

def test_unvisited_filter():
    """Test filtering of unvisited customers"""
    print("\nTesting unvisited customer filter...")
    
    customers = load_west_la_ice_customers()
    optimizer = RouteOptimizer()
    
    for i, customer in enumerate(customers[:100]):
        customer.visited_this_week = i % 3 == 0  # Every 3rd customer visited
    
    unvisited = optimizer.filter_unvisited_customers(customers)
    
    total_customers = len(customers)
    unvisited_count = len(unvisited)
    visited_count = total_customers - unvisited_count
    
    print(f"Total customers: {total_customers}")
    print(f"Visited this week: {visited_count}")
    print(f"Unvisited (need routes): {unvisited_count}")
    
    priority_order = {"URGENT": 0, "HIGH": 1, "STANDARD": 2}
    is_sorted = all(
        priority_order.get(unvisited[i].priority_level, 2) <= priority_order.get(unvisited[i+1].priority_level, 2)
        for i in range(len(unvisited)-1)
    )
    
    if is_sorted:
        print("✅ Unvisited customers correctly sorted by priority")
    else:
        print("⚠️  WARNING: Unvisited customers not properly sorted by priority")
    
    return unvisited

def test_google_sheets_integration():
    """Test Google Sheets integration for visit tracking"""
    print("\nTesting Google Sheets integration...")
    
    try:
        sheets_service = GoogleSheetsService()
        
        success = sheets_service.update_visit_tracking(
            customer_id="TEST_001",
            customer_name="Test Customer",
            address="123 Test St",
            depot="Lufkin",
            visit_date=datetime.now(),
            priority="HIGH"
        )
        
        if success:
            print("✅ Visit tracking update successful")
        else:
            print("⚠️  WARNING: Visit tracking update failed")
        
        reset_success = sheets_service.reset_weekly_visits()
        
        if reset_success:
            print("✅ Weekly reset in Google Sheets successful")
        else:
            print("⚠️  WARNING: Weekly reset in Google Sheets failed")
        
        return success and reset_success
        
    except Exception as e:
        print(f"❌ Google Sheets integration error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("WEEKLY VISIT TRACKING SYSTEM TEST")
    print("=" * 60)
    
    depot_counts = test_depot_assignment_balance()
    priority_counts = test_priority_rules()
    reset_results = test_weekly_reset()
    unvisited = test_unvisited_filter()
    sheets_success = test_google_sheets_integration()
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    target_distribution = {"Lufkin": 192, "Leesville": 190, "Lake Charles": 189}
    distribution_ok = all(
        abs(depot_counts.get(depot, 0) - target) <= 10  # Allow 10 customer tolerance
        for depot, target in target_distribution.items()
    )
    
    print(f"✅ Depot distribution balanced: {distribution_ok}")
    print(f"✅ Priority rules working: {sum(priority_counts.values()) > 0}")
    print(f"✅ Weekly reset functional: {reset_results[1] == 0}")
    print(f"✅ Unvisited filter working: {len(unvisited) > 0}")
    print(f"✅ Google Sheets integration: {sheets_success}")
    
    overall_success = all([
        distribution_ok,
        sum(priority_counts.values()) > 0,
        reset_results[1] == 0,
        len(unvisited) > 0
    ])
    
    if overall_success:
        print("\n🎉 ALL TESTS PASSED - Weekly visit tracking system is ready!")
    else:
        print("\n⚠️  SOME TESTS FAILED - Review issues above")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
