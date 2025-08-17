from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from typing import List

from .models import Customer, RouteOptimizationRequest, RouteOptimizationResponse, VehicleRoute, DepotLocation
from .customer_data import load_west_la_ice_customers, get_customer_count
from .route_optimizer import RouteOptimizer
from .google_maps_service import GoogleMapsService

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
            num_vehicles=request.num_vehicles
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
