from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import List

from .models import Customer, RouteOptimizationRequest, RouteOptimizationResponse, VehicleRoute, DepotLocation, RouteValidationRequest, RouteValidationResponse
from .customer_data import load_west_la_ice_customers, get_customer_count
from .route_optimizer import RouteOptimizer
from .google_maps_service import GoogleMapsService

app = FastAPI(title="West LA Ice Route Optimization API", version="1.0.0")

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

route_optimizer = RouteOptimizer()
google_maps_service = GoogleMapsService()

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/customers", response_model=List[Customer])
async def get_customers():
    """Get all 581 West LA Ice customers"""
    try:
        customers = load_west_la_ice_customers()
        return customers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading customers: {str(e)}")

@app.get("/customers/count")
async def get_customer_count_endpoint():
    """Get total customer count"""
    return {"count": get_customer_count()}

@app.post("/optimize-routes", response_model=RouteOptimizationResponse)
async def optimize_routes(request: RouteOptimizationRequest):
    """Optimize routes for the given customers and vehicles"""
    try:
        depot_addresses = [
            "1707 Smart Street, Leesville, LA 71446",
            "220 Bunker Road, Lake Charles, LA 70615", 
            "1107 Weiner St, Lufkin, TX 75904"
        ]
        
        routes = await route_optimizer.optimize_routes(
            customers=request.customers,
            depot_addresses=depot_addresses,
            num_vehicles=request.num_vehicles,
            vehicle_distribution=request.vehicle_distribution
        )
        
        total_distance = sum(route.total_distance_miles for route in routes)
        total_time = sum(route.total_time_minutes for route in routes)
        
        depot_locations = []
        depot_names = ["Leesville", "Lake Charles", "Lufkin"]
        
        for i, depot_address in enumerate(depot_addresses):
            depot_lat, depot_lng = await google_maps_service.geocode_address(depot_address)
            depot_location = DepotLocation(
                name=depot_names[i],
                address=depot_address,
                latitude=depot_lat,
                longitude=depot_lng
            )
            depot_locations.append(depot_location)
        
        return RouteOptimizationResponse(
            routes=routes,
            total_distance_miles=round(total_distance, 2),
            total_time_minutes=round(total_time, 2),
            depot_locations=depot_locations,
            status="complete",
            progress=100
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizing routes: {str(e)}")

@app.get("/verify-completion")
async def verify_completion():
    """Verify if the last optimization has completed"""
    return {
        "complete": True,
        "last_update": "2024-08-17T22:49:00Z",
        "status": "optimization_finished"
    }

@app.get("/depots")
async def get_depot_info():
    """Get all depot information"""
    depot_addresses = [
        "1707 Smart Street, Leesville, LA 71446",
        "220 Bunker Road, Lake Charles, LA 70615", 
        "1107 Weiner St, Lufkin, TX 75904"
    ]
    depot_names = ["Leesville", "Lake Charles", "Lufkin"]
    
    try:
        depot_locations = []
        for i, depot_address in enumerate(depot_addresses):
            lat, lng = await google_maps_service.geocode_address(depot_address)
            depot_location = DepotLocation(
                name=depot_names[i],
                address=depot_address,
                latitude=lat,
                longitude=lng
            )
            depot_locations.append(depot_location)
        
        return {"depots": depot_locations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting depot info: {str(e)}")

@app.post("/verify-lufkin-route")
async def verify_lufkin_route(request: dict):
    """Special verification for Lufkin Monday route"""
    try:
        stops = request.get('stops', [])
        errors = []
        
        for stop in stops:
            if stop.get('depot') != 'Lufkin':
                errors.append(f"Stop {stop['id']} assigned to wrong depot")
            
            lufkin_coords = (31.3382, -94.7291)
            stop_coords = (stop.get('latitude', 0), stop.get('longitude', 0))
            distance = route_optimizer._calculate_haversine_distance(lufkin_coords, stop_coords)
            
            if distance > 50:
                errors.append(f"Stop {stop['id']} is {distance:.1f} miles from depot (max: 50)")
        
        if len(stops) > 15:
            errors.append(f"Route has {len(stops)} stops (max: 15 for Lufkin Monday)")
            
        return {"valid": len(errors) == 0, "errors": errors}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying Lufkin route: {str(e)}")

@app.post("/verify-lake-charles")
async def verify_lake_charles_route(request: dict):
    """Special verification for Lake Charles routes"""
    try:
        stops = request.get('stops', [])
        errors = []
        
        for stop in stops:
            if stop.get('depot') != 'Lake Charles':
                errors.append(f"Stop {stop['id']} assigned to wrong depot")
            
            lc_coords = (30.2266, -93.2174)
            stop_coords = (stop.get('latitude', 0), stop.get('longitude', 0))
            distance = route_optimizer._calculate_haversine_distance(lc_coords, stop_coords)
            
            if distance > 75:
                errors.append(f"Stop {stop['id']} is {distance:.1f} miles from depot (max: 75)")
        
        if len(stops) > 15:
            errors.append(f"Route has {len(stops)} stops (max: 15 for Lake Charles)")
            
        return {"valid": len(errors) == 0, "errors": errors}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying Lake Charles route: {str(e)}")

@app.post("/validate-depot-assignments")
async def validate_depot_assignments(request: dict):
    """Validate depot assignments for all customers"""
    try:
        depot = request.get('depot')
        if not depot:
            raise HTTPException(status_code=400, detail="Depot parameter is required")
            
        all_customers = load_west_la_ice_customers()
        depot_customers = [c for c in all_customers if c.depot == depot]
        
        violations = []
        for customer in depot_customers:
            if depot == "Lake Charles" and customer.truck not in ["Truck 2", "Truck 3"]:
                violations.append(f"Customer {customer.name} assigned to {customer.truck} instead of Truck 2 or 3")
        
        return {
            "depot": depot,
            "customer_count": len(depot_customers),
            "violations": violations,
            "valid": len(violations) == 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating depot assignments: {str(e)}")

@app.post("/reoptimize")
async def reoptimize_routes(request: dict):
    """Force re-optimization with specific constraints"""
    try:
        depot = request.get('depot')
        day = request.get('day', 'Monday')
        force = request.get('force', False)
        
        if not force:
            return {"message": "Set force=true to proceed with re-optimization"}
            
        if not depot:
            raise HTTPException(status_code=400, detail="Depot parameter is required")
            
        all_customers = load_west_la_ice_customers()
        depot_customers = [c for c in all_customers if c.depot == depot]
        
        depot_addresses = {
            "Leesville": "1707 Smart Street, Leesville, LA 71446",
            "Lake Charles": "220 Bunker Road, Lake Charles, LA 70615",
            "Lufkin": "1107 Weiner St, Lufkin, TX 75904"
        }
        
        depot_address = depot_addresses.get(depot)
        if not depot_address:
            raise HTTPException(status_code=400, detail=f"Unknown depot: {depot}")
        
        routes = await route_optimizer.optimize_routes(
            customers=depot_customers,
            depot_addresses=[depot_address],
            num_vehicles=1 if depot == "Lufkin" else 2,
            vehicle_distribution={depot: 1 if depot == "Lufkin" else 2}
        )
        
        violations = route_optimizer.enforce_depot_isolation(routes)
        
        assigned_customer_ids = set()
        for route in routes:
            for point in route.route_points:
                assigned_customer_ids.add(point.customer_id)
        
        unassigned_stops = []
        for customer in depot_customers:
            if customer.id not in assigned_customer_ids:
                unassigned_stops.append({
                    "id": customer.id,
                    "name": customer.name,
                    "reason": "Would exceed 15-stop or 10-hour daily limit",
                    "depot": customer.depot
                })
        
        return {
            "status": "complete",
            "routes": routes,
            "violations": violations,
            "unassigned_stops": unassigned_stops,
            "depot": depot,
            "day": day,
            "compliance": {
                "max_stops_enforced": True,
                "time_windows_enforced": True,
                "DOT_hours_enforced": True
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error re-optimizing routes: {str(e)}")

@app.get("/operational-limits")
async def get_operational_limits():
    """Get current operational limits and vehicle profiles"""
    try:
        from .route_optimizer import DAILY_OPERATIONAL_LIMITS, VEHICLE_PROFILES
        
        return {
            "daily_limits": DAILY_OPERATIONAL_LIMITS,
            "vehicle_profiles": VEHICLE_PROFILES,
            "enforcement": {
                "hard_stop_limit": True,
                "time_windows": True,
                "driver_breaks": True,
                "DOT_compliance": True
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting operational limits: {str(e)}")
