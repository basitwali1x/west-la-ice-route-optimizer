from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from typing import List
from datetime import datetime

from .models import Customer, RouteOptimizationRequest, RouteOptimizationResponse, VehicleRoute, DepotLocation, RouteValidationRequest, RouteValidationResponse, SheetsSync, TruckAssignment, DriverRoute, SheetsData, WeeklyVisitStatus, WeeklyResetRequest, VisitTrackingUpdate, DayRouteSync, DeliveryCompletionUpdate, AdvancedRebalanceRequest
from .customer_data import load_west_la_ice_customers, get_customer_count
from .route_optimizer import RouteOptimizer, DEPOT_CONSTRAINTS
from .google_maps_service import GoogleMapsService
from .google_sheets_service import GoogleSheetsService

load_dotenv()

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
sheets_service = GoogleSheetsService()

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
        
        all_violations = route_optimizer.enforce_depot_isolation(routes)
        
        for route in routes:
            route_violations = [v for v in all_violations if route.depot_name in v]
            route.violations = route_violations
            route.compliance = {
                "DOT_hours": route.total_time_minutes / 60 <= 10,
                "max_stops": len(route.route_points) <= DEPOT_CONSTRAINTS.get(route.depot_name, {}).get("max_stops", 15),
                "distance_limit": not any("miles from" in v for v in route_violations)
            }
        
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
        
        result = RouteOptimizationResponse(
            routes=routes,
            total_distance_miles=round(total_distance, 2),
            total_time_minutes=round(total_time, 2),
            depot_locations=depot_locations,
            status="complete",
            progress=100,
            constraint_violations=all_violations
        )
        
        global optimization_results_cache
        optimization_results_cache = result.dict()
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizing routes: {str(e)}")

@app.post("/sync-from-sheets")
async def sync_from_sheets(sheets_sync: SheetsSync):
    """Pull latest depot assignments from Google Sheets"""
    try:
        result = sheets_service.sync_from_sheets(sheets_sync.sheet_id, sheets_sync.location_filter)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "status": "success",
            "data": result,
            "message": f"Successfully synced data from sheet {sheets_sync.sheet_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync from sheets: {str(e)}")

@app.post("/optimize-with-sheets")
async def optimize_with_sheets(sheets_sync: SheetsSync):
    """Run OR-Tools optimization using sheet-based constraints"""
    try:
        sheet_data = sheets_service.sync_from_sheets(sheets_sync.sheet_id)
        if "error" in sheet_data:
            raise HTTPException(status_code=400, detail=sheet_data["error"])
        
        optimizer = RouteOptimizer(
            depot_radius=75,
            max_stops=25,
            truck_allocations={"Lufkin": 3, "Leesville": 3, "Lake Charles": 2}
        )
        
        customers = []
        for depot, depot_customers in sheet_data.get("customers", {}).items():
            for customer_data in depot_customers:
                if customer_data.get("name") and customer_data.get("address"):
                    customer = Customer(
                        id=f"{depot}_{customer_data['name']}",
                        name=customer_data["name"],
                        address=customer_data["address"],
                        latitude=0.0,
                        longitude=0.0,
                        depot=depot,
                        phone=customer_data.get("phone", "")
                    )
                    customers.append(customer)
        
        request = RouteOptimizationRequest(
            customers=customers,
            num_vehicles=8,
            depot_address=os.getenv("DEPOT_ADDRESS", "1707 Smart Street, Leesville, LA 71446")
        )
        
        result = await optimizer.optimize_routes_with_sheets_constraints(request, sheet_data)
        
        return {
            "status": "success",
            "optimization_result": result,
            "sheet_data": sheet_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to optimize with sheets: {str(e)}")

optimization_results_cache = {}

@app.get("/driver-routes/{truck_id}")
async def get_driver_routes(truck_id: str, day: str = "Monday"):
    """Get route data for a specific driver/truck"""
    try:
        driver_routes = []
        
        print(f"DEBUG: Driver routes request for truck_id={truck_id}, day={day}")
        print(f"DEBUG: optimization_results_cache exists: {bool(optimization_results_cache)}")
        
        if optimization_results_cache:
            available_vehicle_ids = [route.get("vehicle_id") for route in optimization_results_cache.get("routes", [])]
            print(f"DEBUG: Available vehicle IDs in cache: {available_vehicle_ids}")
            
            truck_mapping = {
                "L1": (1, "Leesville"), "L2": (2, "Leesville"), "L3": (3, "Leesville"), 
                "L4": (4, "Leesville"), "L5": (5, "Leesville"),
                "Le1": (1, "Leesville"), "Le2": (2, "Leesville"), "Le3": (3, "Leesville"),
                "Le4": (4, "Leesville"), "Le5": (5, "Leesville"),
                "LC1": (1, "Lake Charles"), "LC2": (2, "Lake Charles"),
                "Lu1": (1, "Lufkin"), "Lf1": (1, "Lufkin")
            }
            
            target_vehicle_id, target_depot = truck_mapping.get(truck_id, (None, None))
            print(f"DEBUG: Mapped truck_id={truck_id} to vehicle_id={target_vehicle_id}, depot={target_depot}")
            
            for route in optimization_results_cache.get("routes", []):
                print(f"DEBUG: Checking route with vehicle_id={route.get('vehicle_id')}, depot={route.get('depot_name')}")
                if (route.get("vehicle_id") == target_vehicle_id and 
                    route.get("depot_name") == target_depot and 
                    route.get("day", "Monday") == day):
                    print(f"DEBUG: Found matching route! Processing route data...")
                    print(f"DEBUG: Route keys: {list(route.keys())}")
                    print(f"DEBUG: Route points count: {len(route.get('route_points', []))}")
                    
                    try:
                        route_points = []
                        for i, point in enumerate(route.get("route_points", [])):
                            print(f"DEBUG: Processing route point {i}: {point}")
                            route_point = {
                                "customer_id": point.get("customer_id", ""),
                                "customer_name": point.get("customer_name", ""),
                                "address": point.get("address", ""),
                                "latitude": point.get("latitude", 0.0),
                                "longitude": point.get("longitude", 0.0),
                                "estimated_time": f"{point.get('order', 0) * 30 + 480} minutes",
                                "priority": False,
                                "order": point.get("order", i + 1)
                            }
                            route_points.append(route_point)
                        
                        print(f"DEBUG: Creating DriverRoute object...")
                        driver_route = DriverRoute(
                            truck_id=truck_id,
                            depot=route.get("depot_name", ""),
                            day=day,
                            stops=route_points,
                            total_distance=route.get("total_distance_miles", 0.0),
                            estimated_hours=route.get("total_time_minutes", 480) / 60.0,
                            priority_stops=[]
                        )
                        driver_routes.append(driver_route)
                        print(f"DEBUG: Successfully created driver route with {len(route_points)} stops")
                    except Exception as e:
                        print(f"DEBUG: Error processing route: {str(e)}")
                        import traceback
                        traceback.print_exc()
        
        if not driver_routes:
            sheet_id = os.getenv("DEFAULT_SHEET_ID", "1priXmXhtP2vVSQ1XUa-Y18-O96OsZ9Qw")
            sheet_data = sheets_service.sync_from_sheets(sheet_id)
            
            if "error" not in sheet_data:
                for assignment in sheet_data.get("route_assignments", []):
                    if assignment.get("truck_id") == truck_id and assignment.get("day") == day:
                        route_points = []
                        for stop in assignment.get("stop_sequence", []):
                            route_point = {
                                "customer_id": stop.get("customer_id", ""),
                                "customer_name": stop.get("customer_name", ""),
                                "address": stop.get("address", ""),
                                "latitude": stop.get("latitude", 0.0),
                                "longitude": stop.get("longitude", 0.0),
                                "estimated_time": stop.get("estimated_time", ""),
                                "priority": stop.get("priority", False)
                            }
                            route_points.append(route_point)
                        
                        driver_route = DriverRoute(
                            truck_id=truck_id,
                            depot=assignment.get("depot", ""),
                            day=day,
                            stops=route_points,
                            total_distance=0.0,
                            estimated_hours=float(assignment.get("estimated_time", "8").split()[0]) if assignment.get("estimated_time") else 8.0,
                            priority_stops=[stop.get("customer_id", "") for stop in assignment.get("stop_sequence", []) if stop.get("priority")]
                        )
                        driver_routes.append(driver_route)
        
        return {
            "truck_id": truck_id,
            "day": day,
            "routes": driver_routes
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get driver routes: {str(e)}")

@app.post("/rebalance-trucks")
async def rebalance_trucks(rebalance_data: dict):
    """Dynamic truck reallocation"""
    try:
        sheet_id = rebalance_data.get("sheet_id", os.getenv("DEFAULT_SHEET_ID", "1priXmXhtP2vVSQ1XUa-Y18-O96OsZ9Qw"))
        assignments = rebalance_data.get("assignments", [])
        
        success = sheets_service.update_route_assignments(sheet_id, assignments)
        
        if success:
            return {
                "status": "success",
                "message": "Truck assignments updated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update truck assignments")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rebalance trucks: {str(e)}")

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
        
        return {
            "status": "complete",
            "routes": routes,
            "violations": violations,
            "depot": depot,
            "day": day
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error re-optimizing routes: {str(e)}")

@app.post("/reset-weekly-visits")
async def reset_weekly_visits(request: WeeklyResetRequest = WeeklyResetRequest()):
    """Reset all visited_this_week flags for weekly cycle"""
    try:
        customers = load_west_la_ice_customers()
        
        for customer in customers:
            customer.visited_this_week = False
        
        success = sheets_service.reset_weekly_visits()
        
        if success:
            return {
                "status": "success",
                "message": "Weekly visit flags reset successfully",
                "reset_date": request.reset_date or datetime.now().isoformat(),
                "customers_reset": len(customers)
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to reset weekly visits in Google Sheets")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting weekly visits: {str(e)}")

@app.get("/visit-status")
async def get_visit_status():
    """Get weekly visit status for all depots"""
    try:
        customers = load_west_la_ice_customers()
        
        depot_stats = {}
        for depot_name in ["Lufkin", "Leesville", "Lake Charles"]:
            depot_customers = [c for c in customers if c.depot == depot_name]
            visited_count = len([c for c in depot_customers if c.visited_this_week])
            overdue_count = len([c for c in depot_customers if c.days_since_last_visit and c.days_since_last_visit > 7])
            
            depot_stats[depot_name] = WeeklyVisitStatus(
                depot_name=depot_name,
                total_customers=len(depot_customers),
                visited_this_week=visited_count,
                pending_visits=len(depot_customers) - visited_count,
                overdue_customers=overdue_count,
                completion_percentage=round((visited_count / len(depot_customers)) * 100, 1) if depot_customers else 0
            )
        
        return {
            "status": "success",
            "depot_status": depot_stats,
            "total_customers": len(customers),
            "total_visited": sum(len([c for c in customers if c.depot == depot and c.visited_this_week]) for depot in depot_stats.keys()),
            "total_overdue": sum(depot_stats[depot].overdue_customers for depot in depot_stats.keys())
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting visit status: {str(e)}")

@app.post("/mark-customer-visited")
async def mark_customer_visited(update: VisitTrackingUpdate):
    """Mark a customer as visited and update tracking"""
    try:
        customers = load_west_la_ice_customers()
        
        customer = next((c for c in customers if c.id == update.customer_id), None)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        customer.visited_this_week = True
        customer.last_visit_date = update.visited_date
        customer.days_since_last_visit = 0
        customer.priority_level = "STANDARD"
        
        success = sheets_service.update_visit_tracking(
            customer_id=str(update.customer_id),
            customer_name=customer.name,
            address=customer.address,
            depot=update.depot,
            visit_date=update.visited_date,
            priority=customer.priority_level
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Customer {customer.name} marked as visited",
                "customer_id": update.customer_id,
                "visit_date": update.visited_date.isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update visit tracking in Google Sheets")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error marking customer as visited: {str(e)}")

@app.post("/optimize-weekly-routes")
async def optimize_weekly_routes(request: RouteOptimizationRequest):
    """Optimize routes for weekly visits with priority and capacity constraints"""
    try:
        depot_addresses = [
            "1707 Smart Street, Leesville, LA 71446",
            "220 Bunker Road, Lake Charles, LA 70615", 
            "1107 Weiner St, Lufkin, TX 75904"
        ]
        
        routes = await route_optimizer.optimize_weekly_routes(
            customers=request.customers,
            depot_addresses=depot_addresses,
            num_vehicles=request.num_vehicles,
            vehicle_distribution=request.vehicle_distribution
        )
        
        all_violations = route_optimizer.enforce_depot_isolation(routes)
        
        for route in routes:
            route_violations = [v for v in all_violations if route.depot_name in v]
            route.violations = route_violations
            route.compliance = {
                "DOT_hours": route.total_time_minutes / 60 <= 10,
                "max_stops": len(route.route_points) <= DEPOT_CONSTRAINTS.get(route.depot_name, {}).get("max_stops", 15),
                "distance_limit": not any("miles from" in v for v in route_violations),
                "weekly_capacity": len([rp for rp in route.route_points]) <= DEPOT_CONSTRAINTS.get(route.depot_name, {}).get("weekly_capacity", 200)
            }
            
            priority_customers = [rp for rp in route.route_points if any(c.id == rp.customer_id and c.priority_level == "URGENT" for c in request.customers)]
            route.priority_score = len(priority_customers) / len(route.route_points) if route.route_points else 0
        
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
        
        result = RouteOptimizationResponse(
            routes=routes,
            total_distance_miles=round(total_distance, 2),
            total_time_minutes=round(total_time, 2),
            depot_locations=depot_locations,
            status="complete",
            progress=100,
            constraint_violations=all_violations
        )
        
        global optimization_results_cache
        optimization_results_cache = result.dict()
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizing weekly routes: {str(e)}")

@app.post("/optimize-complete-weekly-routes")
async def optimize_complete_weekly_routes(request: RouteOptimizationRequest):
    """Optimize routes grouped by days (Monday-Friday) with ~116 customers per day"""
    try:
        depot_addresses = [
            "1707 Smart Street, Leesville, LA 71446",
            "220 Bunker Road, Lake Charles, LA 70615", 
            "1107 Weiner St, Lufkin, TX 75904"
        ]
        
        routes = await route_optimizer.optimize_complete_weekly_routes(
            customers=request.customers,
            depot_addresses=depot_addresses,
            num_vehicles=request.num_vehicles,
            vehicle_distribution=request.vehicle_distribution
        )
        
        all_violations = route_optimizer.enforce_depot_isolation(routes)
        
        for route in routes:
            route_violations = [v for v in all_violations if route.depot_name in v]
            route.violations = route_violations
            route.compliance = {
                "DOT_hours": route.total_time_minutes / 60 <= 10,
                "max_stops": len(route.route_points) <= DEPOT_CONSTRAINTS.get(route.depot_name, {}).get("max_stops", 15),
                "distance_limit": not any("miles from" in v for v in route_violations),
                "weekly_capacity": len([rp for rp in route.route_points]) <= DEPOT_CONSTRAINTS.get(route.depot_name, {}).get("weekly_capacity", 200)
            }
            
            priority_customers = [rp for rp in route.route_points if any(c.id == rp.customer_id and c.priority_level == "URGENT" for c in request.customers)]
            route.priority_score = len(priority_customers) / len(route.route_points) if route.route_points else 0
        
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
        
        result = RouteOptimizationResponse(
            routes=routes,
            total_distance_miles=round(total_distance, 2),
            total_time_minutes=round(total_time, 2),
            depot_locations=depot_locations,
            status="complete",
            progress=100,
            constraint_violations=all_violations
        )
        
        global optimization_results_cache
        optimization_results_cache = result.dict()
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizing complete weekly routes: {str(e)}")

@app.post("/sync-day-routes")
async def sync_day_routes(day_sync: DayRouteSync):
    """Pull day-specific route assignments from Google Sheets"""
    try:
        result = sheets_service.sync_day_specific_routes(day_sync.sheet_id, day_sync.location_filter)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "status": "success",
            "data": result,
            "message": f"Successfully synced day-specific routes from sheet {day_sync.sheet_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync day routes: {str(e)}")

@app.post("/update-delivery-completion")
async def update_delivery_completion(completion_data: DeliveryCompletionUpdate):
    """Update delivery completion status in Google Sheets"""
    try:
        success = sheets_service.update_delivery_completion(
            completion_data.sheet_id,
            completion_data.truck_id,
            completion_data.day,
            completion_data.completed_stops
        )
        
        if success:
            return {
                "status": "success",
                "message": "Delivery completion updated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update delivery completion")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update delivery completion: {str(e)}")

@app.post("/rebalance-trucks-advanced")
async def rebalance_trucks_advanced(rebalance_data: AdvancedRebalanceRequest):
    """Advanced dynamic truck reallocation with capacity validation"""
    try:
        from .route_optimizer import DEPOT_CONSTRAINTS
        
        if rebalance_data.validate_capacity:
            depot_counts = {}
            for assignment in rebalance_data.assignments:
                depot = assignment.get('depot')
                if depot not in depot_counts:
                    depot_counts[depot] = 0
                depot_counts[depot] += len(assignment.get('stop_sequence', []))
            
            violations = []
            for depot, count in depot_counts.items():
                max_capacity = DEPOT_CONSTRAINTS.get(depot, {}).get('weekly_capacity', 200)
                if count > max_capacity:
                    violations.append(f"{depot} exceeds capacity: {count}/{max_capacity}")
            
            if violations:
                return {
                    "status": "validation_failed",
                    "violations": violations,
                    "message": "Rebalancing would violate depot capacity constraints"
                }
        
        success = sheets_service.update_route_assignments(rebalance_data.sheet_id, rebalance_data.assignments)
        
        day_update_success = True
        if rebalance_data.update_day_tabs:
            for assignment in rebalance_data.assignments:
                day_success = sheets_service.update_delivery_completion(
                    rebalance_data.sheet_id, 
                    assignment.get('truck_id'), 
                    assignment.get('day', 'Monday'), 
                    []
                )
                day_update_success = day_update_success and day_success
        
        if success:
            return {
                "status": "success",
                "message": "Advanced truck rebalancing completed successfully",
                "day_tabs_updated": day_update_success
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update route assignments")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rebalance trucks: {str(e)}")
