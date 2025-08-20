#!/usr/bin/env python3
"""
Validation script to check for cross-depot routing violations
Usage: python validate_routes.py
"""

from app.route_optimizer import RouteOptimizer

def main():
    optimizer = RouteOptimizer()
    results = optimizer.validate_routes()
    
    print(f"Cross-depot violations: {results['violations']}")
    print(f"Daily capacity compliance: {results['daily_capacity_ok']}")
    print(f"Depot zones respected: {results['depot_zones_respected']}")

if __name__ == "__main__":
    main()
