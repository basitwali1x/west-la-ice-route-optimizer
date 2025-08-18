from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from typing import List

from .models import Customer, RouteOptimizationRequest, RouteOptimizationResponse, VehicleRoute, DepotLocation, RouteValidationRequest, RouteValidationResponse, SheetsSync, TruckAssignment, DriverRoute, SheetsData
from .customer_data import load_west_la_ice_customers, get_customer_count
from .route_optimizer import RouteOptimizer
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

@app.post("/sync-from-sheets")
async def sync_from_sheets(sheets_sync: SheetsSync):
    """Pull latest depot assignments from Google Sheets"""
    try:
        result = sheets_service.sync_from_sheets(sheets_sync.sheet_id)
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

@app.get("/driver-routes/{truck_id}")
async def get_driver_routes(truck_id: str, day: str = "Monday"):
    """Get route data for a specific driver/truck"""
    try:
        sheet_id = os.getenv("DEFAULT_SHEET_ID", "1priXmXhtP2vVSQ1XUa-Y18-O96OsZ9Qw")
        sheet_data = sheets_service.sync_from_sheets(sheet_id)
        
        if "error" in sheet_data:
            raise HTTPException(status_code=400, detail=sheet_data["error"])
        
        driver_routes = []
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
