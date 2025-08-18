from pydantic import BaseModel
from typing import List, Optional, Dict

class Customer(BaseModel):
    id: int
    name: str
    address: str
    depot: str
    truck: Optional[str] = None
    day: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class RouteOptimizationRequest(BaseModel):
    customers: List[Customer]
    num_vehicles: int = 8
    depot_addresses: List[str]
    vehicle_distribution: Optional[Dict[str, int]] = None

class RoutePoint(BaseModel):
    customer_id: int
    customer_name: str
    address: str
    latitude: float
    longitude: float
    order: int

class VehicleRoute(BaseModel):
    vehicle_id: int
    depot_name: str
    route_points: List[RoutePoint]
    total_distance_miles: float
    total_time_minutes: float

class DepotLocation(BaseModel):
    name: str
    address: str
    latitude: float
    longitude: float

class RouteOptimizationResponse(BaseModel):
    routes: List[VehicleRoute]
    total_distance_miles: float
    total_time_minutes: float
    depot_locations: List[DepotLocation]
    status: str = "complete"
    progress: int = 100

class DepotConstraint(BaseModel):
    depot_name: str
    max_distance_miles: float
    max_stops: Optional[int] = None
    allowed_vehicles: Optional[List[str]] = None
    penalty_multiplier: float = 1.0

class RouteValidationRequest(BaseModel):
    stops: List[Dict]
    depot: str
    day: str = "Monday"

class RouteValidationResponse(BaseModel):
    valid: bool
    errors: List[str]
    warnings: Optional[List[str]] = None
