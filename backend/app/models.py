from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class Customer(BaseModel):
    id: int
    name: str
    address: str
    depot: str
    truck: Optional[str] = None
    day: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    truck_id: Optional[str] = None
    stop_sequence: Optional[int] = None
    estimated_time: Optional[str] = None
    priority: Optional[bool] = False
    phone: Optional[str] = None
    last_visit_date: Optional[datetime] = None
    visited_this_week: bool = False
    days_since_last_visit: Optional[int] = 0
    priority_level: str = "STANDARD"  # URGENT, HIGH, STANDARD
    weekly_visit_required: bool = True

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
    truck_id: Optional[str] = None
    depot: Optional[str] = None
    day: Optional[str] = "Monday"
    estimated_hours: Optional[float] = None
    total_time_minutes: float
    compliance: Optional[Dict[str, bool]] = None
    violations: Optional[List[str]] = None
    priority_score: Optional[float] = None

class SheetsSync(BaseModel):
    sheet_id: str
    last_sync: Optional[str] = None
    status: str = "pending"

class TruckAssignment(BaseModel):
    truck_id: str
    depot: str
    day: str = "Monday"
    stops: List[str] = []
    estimated_time: Optional[str] = None

class DriverRoute(BaseModel):
    truck_id: str
    depot: str
    day: str
    stops: List[RoutePoint]
    total_distance: float
    estimated_hours: float
    priority_stops: List[str] = []

class SheetsData(BaseModel):
    customers: Dict[str, List[Dict[str, Any]]]
    route_assignments: List[Dict[str, Any]]
    truck_allocations: Dict[str, int]
    last_updated: str

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
    constraint_violations: Optional[List[str]] = None

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

class WeeklyVisitStatus(BaseModel):
    depot_name: str
    total_customers: int
    visited_this_week: int
    pending_visits: int
    overdue_customers: int
    completion_percentage: float

class WeeklyResetRequest(BaseModel):
    force_reset: bool = False
    reset_date: Optional[datetime] = None

class VisitTrackingUpdate(BaseModel):
    customer_id: int
    visited_date: datetime
    depot: str
    truck_id: Optional[str] = None

class CustomerCreateRequest(BaseModel):
    name: str
    address: str
    depot: str
    phone: Optional[str] = None
    priority_level: str = "STANDARD"
    weekly_visit_required: bool = True

class CustomerUpdateRequest(BaseModel):
    id: int
    name: Optional[str] = None
    address: Optional[str] = None
    depot: Optional[str] = None
    phone: Optional[str] = None
    priority_level: Optional[str] = None
    weekly_visit_required: Optional[bool] = None

class FourWeekScheduleResponse(BaseModel):
    weeks: List[Dict[str, Any]]
    total_customers: int
    customers_per_week: int
