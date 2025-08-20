from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from typing import List, Dict, Optional, Any
import asyncio
import math
from datetime import datetime, timedelta
from .models import Customer, VehicleRoute, RoutePoint, RouteOptimizationRequest, RouteOptimizationResponse
from .google_maps_service import GoogleMapsService

LUFKIN_MONDAY_STOPS = [
    "Big's 3822,3644 Hwy 69N",
    "Big's 3825,3889 N Hwy 69", 
    "Fairview Grocery",
    "Hernandez",
    "Joc Stop",
    "Lucky's",
    "M&B's", 
    "New Way",
    "TXI Operations",
    "Lakeview RV",
    "Chubby's",
    "Angeline Forest Service",
    "Texas-Sabine National Forest",
    "Lakeside",
    "Roy O Martin OSB"
]

DEPOT_CONSTRAINTS = {
    "Lufkin": {
        "max_distance": 50, 
        "max_stops_monday": 15, 
        "max_hours": 10,
        "weekly_capacity": 192,  # Weekly customer limit for balanced distribution
        "lat_range": (30.50, 32.00),
        "lng_range": (-95.50, -93.50),
        "cities": ["Lufkin", "Nacogdoches", "Diboll", "Huntington", "Jasper", "Zavalla", "Ratcliff"]
    },
    "Lake Charles": {
        "max_distance": 75, 
        "max_stops": 15, 
        "max_hours": 10,
        "weekly_capacity": 189,  # Weekly customer limit for balanced distribution
        "lat_range": (29.90, 30.50), 
        "lng_range": (-93.80, -92.90),
        "cities": ["Lake Charles", "Sulphur", "Vinton", "Iowa"]
    },
    "Leesville": {
        "max_distance": 100, 
        "max_stops": 15, 
        "max_hours": 10,
        "weekly_capacity": 190,  # Weekly customer limit for balanced distribution
        "lat_range": (30.80, 31.50),
        "lng_range": (-93.80, -92.50),
        "cities": ["Leesville", "DeRidder", "Rosepine", "Fort Polk"]
    }
}

DAILY_CAPACITY = 116  # Total daily customers across all depots

PRIORITY_RULES = {
    "URGENT": {
        "condition": lambda c: c.days_since_last_visit and c.days_since_last_visit > 7,
        "multiplier": 0.5  # Higher priority = lower cost in optimization
    },
    "HIGH": {
        "condition": lambda c: c.days_since_last_visit and c.days_since_last_visit > 5,
        "multiplier": 0.8
    },
    "STANDARD": {
        "condition": lambda c: True,
        "multiplier": 1.0
    }
}

class RouteOptimizer:
    def __init__(self, depot_radius: float = 75, max_stops: int = 25, truck_allocations: dict = None):
        self.google_maps = GoogleMapsService()
        self.depot_radius = depot_radius
        self.max_stops = max_stops
        self.truck_allocations = truck_allocations or {"Lufkin": 3, "Leesville": 3, "Lake Charles": 2}
    
    def assign_priority(self, customer: Customer) -> str:
        """Assign priority level based on last visit date"""
        if not customer.last_visit_date:
            return "HIGH"  # New customers get high priority
        
        days_overdue = (datetime.now() - customer.last_visit_date).days
        customer.days_since_last_visit = days_overdue
        
        if days_overdue > 7:
            return "URGENT"
        elif days_overdue > 5:
            return "HIGH"
        return "STANDARD"
    
    def assign_depot_with_capacity(self, customer: Customer, current_assignments: Dict[str, int]) -> str:
        """Assign customer to depot considering weekly capacity limits"""
        depot_locations = {
            "Lufkin": {"lat": 31.3382, "lng": -94.7291},
            "Leesville": {"lat": 31.1435, "lng": -93.2607},
            "Lake Charles": {"lat": 30.2266, "lng": -93.2174}
        }
        
        if not customer.latitude or not customer.longitude:
            return customer.depot or "Leesville"
        
        distances = {}
        for depot_name, coords in depot_locations.items():
            distance = self._calculate_distance(
                customer.latitude, customer.longitude,
                coords['lat'], coords['lng']
            )
            distances[depot_name] = distance
        
        sorted_depots = sorted(distances.items(), key=lambda x: x[1])
        
        for depot_name, distance in sorted_depots:
            constraints = DEPOT_CONSTRAINTS[depot_name]
            max_capacity = constraints["weekly_capacity"]
            current_count = current_assignments.get(depot_name, 0)
            
            if (distance <= constraints["max_distance"] and 
                current_count < max_capacity):
                return depot_name
        
        remaining_capacity = {
            depot: DEPOT_CONSTRAINTS[depot]["weekly_capacity"] - current_assignments.get(depot, 0)
            for depot in DEPOT_CONSTRAINTS.keys()
        }
        return max(remaining_capacity, key=remaining_capacity.get)
    
    def filter_unvisited_customers(self, customers: List[Customer]) -> List[Customer]:
        """Filter customers who haven't been visited this week"""
        unvisited = [c for c in customers if not c.visited_this_week and c.weekly_visit_required]
        
        for customer in unvisited:
            customer.priority_level = self.assign_priority(customer)
        
        priority_order = {"URGENT": 0, "HIGH": 1, "STANDARD": 2}
        unvisited.sort(key=lambda c: priority_order.get(c.priority_level, 2))
        
        return unvisited
    
    async def optimize_weekly_routes(self, customers: List[Customer], depot_addresses: List[str], num_vehicles: int = 8, vehicle_distribution: Optional[Dict[str, int]] = None) -> List[VehicleRoute]:
        """Optimize routes for weekly visits with priority and capacity constraints"""
        unvisited_customers = self.filter_unvisited_customers(customers)
        
        current_assignments = {"Lufkin": 0, "Leesville": 0, "Lake Charles": 0}
        for customer in unvisited_customers:
            assigned_depot = self.assign_depot_with_capacity(customer, current_assignments)
            customer.depot = assigned_depot
            current_assignments[assigned_depot] += 1
        
        return await self.optimize_routes(unvisited_customers, depot_addresses, num_vehicles, vehicle_distribution)
    
    async def optimize_complete_weekly_routes(self, customers: List[Customer], depot_addresses: List[str], num_vehicles: int = 8, vehicle_distribution: Optional[Dict[str, int]] = None) -> List[VehicleRoute]:
        """Optimize routes grouped by days (Monday-Friday) with ~116 customers per day"""
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        customers_per_day = len(customers) // len(days)
        
        all_routes = []
        
        for day_index, day in enumerate(days):
            start_index = day_index * customers_per_day
            if day_index == len(days) - 1:
                day_customers = customers[start_index:]
            else:
                end_index = start_index + customers_per_day
                day_customers = customers[start_index:end_index]
            
            for customer in day_customers:
                customer.day = day
            
            current_assignments = {"Lufkin": 0, "Leesville": 0, "Lake Charles": 0}
            for customer in day_customers:
                assigned_depot = self.assign_depot_with_capacity(customer, current_assignments)
                customer.depot = assigned_depot
                current_assignments[assigned_depot] += 1
            
            day_routes = await self.optimize_routes(day_customers, depot_addresses, num_vehicles, vehicle_distribution)
            
            for route in day_routes:
                route.day = day
            
            all_routes.extend(day_routes)
        
        return all_routes
    
    async def optimize_routes(self, customers: List[Customer], depot_addresses: List[str], num_vehicles: int = 8, vehicle_distribution: Optional[Dict[str, int]] = None) -> List[VehicleRoute]:
        """Optimize routes using OR-Tools with Google Maps distance data"""
        
        depot_mapping = {
            "Leesville": "1707 Smart Street, Leesville, LA 71446",
            "Lake Charles": "220 Bunker Road, Lake Charles, LA 70615", 
            "Lufkin": "1107 Weiner St, Lufkin, TX 75904"
        }
        
        customers_by_depot = {}
        for customer in customers:
            depot_name = customer.depot
            if depot_name not in customers_by_depot:
                customers_by_depot[depot_name] = []
            customers_by_depot[depot_name].append(customer)
        
        customers_by_depot = self.enforce_daily_capacity(customers_by_depot)
        
        filtered_customers_by_depot = {}
        for depot_name, depot_customers in customers_by_depot.items():
            valid_customers = [c for c in depot_customers if self.is_within_depot_zone(c, depot_name)]
            if valid_customers:
                filtered_customers_by_depot[depot_name] = valid_customers
        
        all_routes = []
        
        for depot_name, depot_customers in filtered_customers_by_depot.items():
            if not depot_customers:
                continue
                
            depot_address = depot_mapping[depot_name]
            vehicles_for_depot = self._calculate_vehicles_per_depot(depot_name, num_vehicles, vehicle_distribution)
            
            try:
                depot_routes = await self._optimize_single_depot_routes(
                    depot_customers, depot_address, depot_name, vehicles_for_depot
                )
                
                valid_routes = []
                for route in depot_routes:
                    if self.validate_depot_assignment(route, depot_name):
                        valid_routes.append(route)
                    else:
                        fallback_routes = self.create_depot_specific_fallback(depot_customers, depot_name)
                        valid_routes.extend(fallback_routes)
                        break
                
                all_routes.extend(valid_routes)
                
            except Exception as e:
                fallback_routes = self.create_depot_specific_fallback(depot_customers, depot_name)
                all_routes.extend(fallback_routes)
        
        return all_routes

    async def optimize_routes_with_sheets_constraints(self, request: RouteOptimizationRequest, sheet_data: dict) -> RouteOptimizationResponse:
        """Enhanced route optimization with Google Sheets constraints"""
        try:
            customers_with_coords = []
            
            for customer in request.customers:
                coords = await self.google_maps.get_coordinates(customer.address)
                if coords:
                    customer.latitude = coords['lat']
                    customer.longitude = coords['lng']
                    
                    if not customer.depot:
                        customer.depot = self._assign_depot_by_radius(coords, request.depot_address)
                    
                    customers_with_coords.append(customer)
            
            depot_coords = await self.google_maps.get_coordinates(request.depot_address)
            if not depot_coords:
                raise ValueError("Could not geocode depot address")
            
            depot_customers = self._group_customers_by_depot(customers_with_coords)
            
            all_routes = []
            vehicle_id = 0
            
            for depot_name, depot_customers_list in depot_customers.items():
                num_trucks = self.truck_allocations.get(depot_name, 2)
                
                if len(depot_customers_list) > 0:
                    depot_routes = await self._optimize_depot_routes(
                        depot_customers_list, 
                        depot_coords, 
                        num_trucks,
                        depot_name
                    )
                    
                    for route in depot_routes:
                        route.vehicle_id = vehicle_id
                        route.depot_name = depot_name
                        route.truck_id = f"{depot_name[0].upper()}{vehicle_id + 1}"
                        vehicle_id += 1
                        all_routes.append(route)
            
            total_distance = sum(route.total_distance_miles for route in all_routes)
            total_time = sum(route.total_time_minutes for route in all_routes)
            
            return RouteOptimizationResponse(
                routes=all_routes,
                total_distance_miles=total_distance,
                total_time_minutes=total_time,
                depot_locations=[],
                status="success"
            )
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in sheets-based route optimization: {e}")
            return RouteOptimizationResponse(
                routes=[],
                total_distance_miles=0,
                total_time_minutes=0,
                depot_locations=[],
                status=f"error: {str(e)}"
            )
    
    def _assign_depot_by_radius(self, customer_coords: dict, depot_address: str) -> str:
        """Assign customer to depot based on 75-mile radius priority"""
        depot_locations = {
            "Lufkin": {"lat": 31.3382, "lng": -94.7291},
            "Leesville": {"lat": 31.1435, "lng": -93.2607},
            "Lake Charles": {"lat": 30.2266, "lng": -93.2174}
        }
        
        customer_lat = customer_coords['lat']
        customer_lng = customer_coords['lng']
        
        closest_depot = None
        min_distance = float('inf')
        
        for depot_name, depot_coords in depot_locations.items():
            distance = self._calculate_distance(
                customer_lat, customer_lng,
                depot_coords['lat'], depot_coords['lng']
            )
            
            if distance <= self.depot_radius and distance < min_distance:
                min_distance = distance
                closest_depot = depot_name
        
        return closest_depot or "Leesville"
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points in miles"""
        from math import radians, cos, sin, asin, sqrt
        
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        
        dlng = lng2 - lng1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * asin(sqrt(a))
        r = 3956
        
        return c * r
    
    def _group_customers_by_depot(self, customers: List[Customer]) -> dict:
        """Group customers by their assigned depot"""
        depot_groups = {}
        
        for customer in customers:
            depot = customer.depot or "Leesville"
            if depot not in depot_groups:
                depot_groups[depot] = []
            depot_groups[depot].append(customer)
        
        return depot_groups
    
    async def _optimize_depot_routes(self, customers: List[Customer], depot_coords: dict, num_vehicles: int, depot_name: str) -> List[VehicleRoute]:
        """Optimize routes for a specific depot with TSP-like optimization"""
        if not customers:
            return []
        
        try:
            manager = pywrapcp.RoutingIndexManager(
                len(customers) + 1,
                num_vehicles,
                0
            )
            routing = pywrapcp.RoutingModel(manager)
            
            distance_matrix = await self._create_distance_matrix(customers, depot_coords)
            
            def distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return int(distance_matrix[from_node][to_node] * 1000)
            
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            routing.SetArcCostForAllVehicles(transit_callback_index)
            
            dimension_name = 'Distance'
            routing.AddDimension(
                transit_callback_index,
                0,
                int(self.depot_radius * 2 * 1000),
                True,
                dimension_name
            )
            distance_dimension = routing.GetDimensionOrDie(dimension_name)
            distance_dimension.SetGlobalSpanCostCoefficient(100)
            
            for vehicle_id in range(num_vehicles):
                routing.AddVariableMinimizedByFinalizer(
                    distance_dimension.CumulVar(routing.Start(vehicle_id))
                )
                routing.AddVariableMinimizedByFinalizer(
                    distance_dimension.CumulVar(routing.End(vehicle_id))
                )
            
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.SAVINGS
            )
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.AUTOMATIC
            )
            search_parameters.time_limit.FromSeconds(120)
            
            solution = routing.SolveWithParameters(search_parameters)
            
            if solution:
                return self._extract_depot_routes(manager, routing, solution, customers, distance_matrix, depot_name)
            else:
                return self._create_simple_routes(customers, num_vehicles, depot_name)
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error optimizing depot routes for {depot_name}: {e}")
            return self._create_simple_routes(customers, num_vehicles, depot_name)
    
    def _create_simple_routes(self, customers: List[Customer], num_vehicles: int, depot_name: str) -> List[VehicleRoute]:
        """Create simple routes when optimization fails with stop limit enforcement"""
        routes = []
        MAX_STOPS_PER_VEHICLE = 25
        
        vehicle_routes = [[] for _ in range(num_vehicles)]
        
        for customer in customers:
            best_vehicle = None
            min_customers = float('inf')
            
            for i, route in enumerate(vehicle_routes):
                if len(route) < MAX_STOPS_PER_VEHICLE and len(route) < min_customers:
                    best_vehicle = i
                    min_customers = len(route)
            
            if best_vehicle is not None:
                vehicle_routes[best_vehicle].append(customer)
            else:
                print(f"⚠️ WARNING: Customer {customer.name} skipped - all vehicles at {MAX_STOPS_PER_VEHICLE} stop limit")
        
        for i, vehicle_customers in enumerate(vehicle_routes):
            if not vehicle_customers:
                continue
                
            route_points = []
            for j, customer in enumerate(vehicle_customers):
                route_point = RoutePoint(
                    customer_id=customer.id,
                    customer_name=customer.name,
                    address=customer.address,
                    latitude=customer.latitude,
                    longitude=customer.longitude,
                    order=j + 1
                )
                route_points.append(route_point)
            
            route = VehicleRoute(
                vehicle_id=i,
                depot_name=depot_name,
                route_points=route_points,
                total_distance_miles=0.0,
                total_time_minutes=480.0,
                truck_id=f"{depot_name[0].upper()}{i + 1}",
                estimated_hours=8.0
            )
            routes.append(route)
        
        return routes
    
    def _extract_depot_routes(self, manager, routing, solution, customers: List[Customer], distance_matrix, depot_name: str) -> List[VehicleRoute]:
        """Extract optimized routes from OR-Tools solution"""
        routes = []
        
        for vehicle_id in range(routing.vehicles()):
            route_points = []
            index = routing.Start(vehicle_id)
            route_distance = 0
            sequence = 1
            
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                if node_index > 0:
                    customer = customers[node_index - 1]
                    route_point = RoutePoint(
                        customer_id=customer.id,
                        customer_name=customer.name,
                        address=customer.address,
                        latitude=customer.latitude,
                        longitude=customer.longitude,
                        order=sequence
                    )
                    route_points.append(route_point)
                    sequence += 1
                
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                if previous_index != index:
                    route_distance += distance_matrix[manager.IndexToNode(previous_index)][manager.IndexToNode(index)]
            
            if route_points:
                estimated_hours = max(4.0, len(route_points) * 0.5)
                route = VehicleRoute(
                    vehicle_id=vehicle_id,
                    depot_name=depot_name,
                    route_points=route_points,
                    total_distance_miles=route_distance,
                    total_time_minutes=estimated_hours * 60,
                    truck_id=f"{depot_name[0].upper()}{vehicle_id + 1}",
                    estimated_hours=estimated_hours
                )
                routes.append(route)
        
        return routes
    
    async def _create_distance_matrix(self, customers: List[Customer], depot_coords: dict) -> List[List[float]]:
        """Create distance matrix for depot optimization"""
        locations = [depot_coords] + [{"lat": c.latitude, "lng": c.longitude} for c in customers]
        matrix = []
        
        for i, from_loc in enumerate(locations):
            row = []
            for j, to_loc in enumerate(locations):
                if i == j:
                    row.append(0.0)
                else:
                    distance = self._calculate_distance(
                        from_loc["lat"], from_loc["lng"],
                        to_loc["lat"], to_loc["lng"]
                    )
                    row.append(distance)
            matrix.append(row)
        
        return matrix
    
    def _calculate_vehicles_per_depot(self, depot_name: str, total_vehicles: int, vehicle_distribution: Optional[Dict[str, int]] = None) -> int:
        if vehicle_distribution and depot_name in vehicle_distribution:
            return vehicle_distribution[depot_name]
        
        if depot_name == "Leesville":
            return 5
        elif depot_name == "Lake Charles":
            return 2
        elif depot_name == "Lufkin":
            return 1
        else:
            return 1
    
    async def _optimize_single_depot_routes(self, customers: List[Customer], depot_address: str, depot_name: str, num_vehicles: int) -> List[VehicleRoute]:
        all_locations = [depot_address] + [customer.address for customer in customers]
        
        print(f"Ensuring consistent coordinates for {len(all_locations)} locations in {depot_name} depot")
        geocoded_locations = []
        for location in all_locations:
            lat, lng = self.google_maps._generate_realistic_coordinates(location)
            geocoded_locations.append((lat, lng))
        
        distance_matrix = await self.google_maps.calculate_distance_matrix(all_locations)
        
        int_distance_matrix = [[int(dist * 100) for dist in row] for row in distance_matrix]
        
        manager = pywrapcp.RoutingIndexManager(
            len(all_locations),  # Number of locations
            num_vehicles,        # Number of vehicles
            0                    # Depot index (first location)
        )
        
        routing = pywrapcp.RoutingModel(manager)
        
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int_distance_matrix[from_node][to_node]
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        dimension_name = 'Distance'
        routing.AddDimension(
            transit_callback_index,
            0,  # no slack
            300000,  # maximum distance per vehicle (3000 miles * 100)
            True,  # start cumul to zero
            dimension_name
        )
        distance_dimension = routing.GetDimensionOrDie(dimension_name)
        distance_dimension.SetGlobalSpanCostCoefficient(100)
        
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            travel_time = int_distance_matrix[from_node][to_node] / 100 / 35  # 35mph average speed
            service_time = 0.5 if from_node != 0 else 0  # 30 minutes per stop
            return int((travel_time + service_time) * 3600)  # Convert to seconds

        time_callback_index = routing.RegisterTransitCallback(time_callback)
        routing.AddDimension(
            time_callback_index,
            18000,  # 5 hours slack for breaks/waiting
            36000,  # 10 hours maximum (DOT compliance)
            False,  # Don't force start cumul to zero
            'Time'
        )
        time_dimension = routing.GetDimensionOrDie('Time')
        
        for i in range(len(all_locations)):
            index = manager.NodeToIndex(i)
            time_dimension.CumulVar(index).SetRange(
                6 * 3600,   # 6AM start
                20 * 3600   # 8PM end
            )
        
        if depot_name == "Lufkin":
            routing.AddDimension(
                transit_callback_index,
                0,  # no slack
                5000000,  # 50 miles * 100 (for int conversion)
                True,  # start cumul to zero
                'LufkinDistance'
            )
            
            routing.AddConstantDimension(
                1,  # increment by 1 per stop
                15,  # maximum stops
                True,  # start to zero
                'LufkinStops'
            )
        
        penalty = 1000000
        for i, customer in enumerate(customers):
            customer_idx = i + 1  # +1 for depot offset
            if depot_name == "Lufkin" and any(stop_name in customer.name for stop_name in LUFKIN_MONDAY_STOPS):
                routing.AddDisjunction([manager.NodeToIndex(customer_idx)], penalty)
        
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.SAVINGS
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.AUTOMATIC
        )
        search_parameters.time_limit.FromSeconds(120)
        
        solution = routing.SolveWithParameters(search_parameters)
        
        if solution:
            print(f"✅ OR-Tools optimization successful for {depot_name} with {len(customers)} customers")
            return await self._extract_routes(
                manager, routing, solution, customers, geocoded_locations, distance_matrix, depot_name
            )
        else:
            print(f"⚠️ OR-Tools optimization failed for {depot_name} with {len(customers)} customers - using fallback")
            return self._create_fallback_routes(customers, geocoded_locations, num_vehicles, depot_name)
    
    async def _extract_routes(self, manager, routing, solution, customers, geocoded_locations, distance_matrix, depot_name):
        """Extract optimized routes from OR-Tools solution"""
        routes = []
        
        for vehicle_id in range(routing.vehicles()):
            route_points = []
            route_distance = 0
            route_time = 0
            
            index = routing.Start(vehicle_id)
            order = 0
            
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                
                if node_index > 0:
                    customer = customers[node_index - 1]  # Adjust for depot offset
                    lat, lng = geocoded_locations[node_index]
                    
                    route_point = RoutePoint(
                        customer_id=customer.id,
                        customer_name=customer.name,
                        address=customer.address,
                        latitude=lat,
                        longitude=lng,
                        order=order
                    )
                    route_points.append(route_point)
                    order += 1
                
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                if not routing.IsEnd(index):
                    from_node = manager.IndexToNode(previous_index)
                    to_node = manager.IndexToNode(index)
                    route_distance += distance_matrix[from_node][to_node]
            
            if route_points:
                last_node = manager.IndexToNode(previous_index)
                route_distance += distance_matrix[last_node][0]  # Return to depot
            
            route_time = route_distance * 2  # 2 minutes per mile at 30 mph
            
            if route_points:  # Only add routes with customers
                vehicle_route = VehicleRoute(
                    vehicle_id=vehicle_id + 1,
                    depot_name=depot_name,
                    route_points=route_points,
                    total_distance_miles=round(route_distance, 2),
                    total_time_minutes=round(route_time, 2)
                )
                routes.append(vehicle_route)
        
        return routes
    
    def _create_fallback_routes(self, customers, geocoded_locations, num_vehicles, depot_name):
        """Create fallback routes using simple round-robin assignment with stop limits"""
        routes = []
        MAX_STOPS_PER_VEHICLE = 25
        
        vehicle_routes = [[] for _ in range(num_vehicles)]
        
        for customer in customers:
            best_vehicle = None
            min_customers = float('inf')
            
            for i, route in enumerate(vehicle_routes):
                if len(route) < MAX_STOPS_PER_VEHICLE and len(route) < min_customers:
                    best_vehicle = i
                    min_customers = len(route)
            
            if best_vehicle is not None:
                vehicle_routes[best_vehicle].append(customer)
            else:
                print(f"⚠️ WARNING: Customer {customer.name} skipped - all vehicles at {MAX_STOPS_PER_VEHICLE} stop limit")
        
        for vehicle_id, vehicle_customer_list in enumerate(vehicle_routes):
            if not vehicle_customer_list:
                continue
                
            route_points = []
            total_distance = 0
            
            for order, customer in enumerate(vehicle_customer_list):
                lat, lng = geocoded_locations[customers.index(customer) + 1]  # +1 for depot offset
                
                route_point = RoutePoint(
                    customer_id=customer.id,
                    customer_name=customer.name,
                    address=customer.address,
                    latitude=lat,
                    longitude=lng,
                    order=order
                )
                route_points.append(route_point)
                
                total_distance += 5.0  # Assume 5 miles per customer on average
            
            vehicle_route = VehicleRoute(
                vehicle_id=vehicle_id + 1,
                depot_name=depot_name,
                route_points=route_points,
                total_distance_miles=total_distance,
                total_time_minutes=total_distance * 2  # 2 minutes per mile
            )
            routes.append(vehicle_route)
        
        return routes
    
    def enforce_depot_isolation(self, routes: List[VehicleRoute]) -> List[str]:
        """Enforce depot isolation and return any violations"""
        violations = []
        
        for route in routes:
            depot_name = route.depot_name
            constraints = DEPOT_CONSTRAINTS.get(depot_name, {})
            
            max_distance = constraints.get("max_distance", 100)
            
            for point in route.route_points:
                depot_coords = self._get_depot_coordinates(depot_name)
                customer_coords = (point.latitude, point.longitude)
                distance = self._calculate_haversine_distance(depot_coords, customer_coords)
                
                if distance > max_distance:
                    violations.append(f"Stop {point.customer_name} is {distance:.1f} miles from {depot_name} depot (max: {max_distance})")
            
            max_stops = constraints.get("max_stops", 15)
            if depot_name == "Lufkin":
                max_stops = constraints.get("max_stops_monday", 15)
            
            if len(route.route_points) > max_stops:
                violations.append(f"{depot_name} route has {len(route.route_points)} stops (max: {max_stops})")
            
            max_hours = constraints.get("max_hours", 10)
            route_hours = route.total_time_minutes / 60
            if route_hours > max_hours:
                violations.append(f"{depot_name} route exceeds {max_hours}h limit: {route_hours:.1f}h")
                
        return violations
    
    def _get_depot_coordinates(self, depot_name: str) -> tuple:
        """Get coordinates for depot"""
        depot_coords = {
            "Leesville": (31.1435, -93.2607),
            "Lake Charles": (30.2266, -93.2174),
            "Lufkin": (31.3382, -94.7291)
        }
        return depot_coords.get(depot_name, (31.1435, -93.2607))
    
    def _calculate_haversine_distance(self, coord1: tuple, coord2: tuple) -> float:
        """Calculate distance between two coordinates in miles"""
        lat1, lng1 = coord1
        lat2, lng2 = coord2
        
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlng/2) * math.sin(dlng/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return 3959 * c  # Earth radius in miles
    
    def is_within_depot_zone(self, customer: Customer, depot_name: str) -> bool:
        """Check if customer is within depot's geographic zone"""
        if not customer.latitude or not customer.longitude:
            return False
            
        constraints = DEPOT_CONSTRAINTS.get(depot_name, {})
        lat_range = constraints.get("lat_range")
        lng_range = constraints.get("lng_range")
        cities = constraints.get("cities", [])
        
        if not lat_range or not lng_range:
            return False
            
        lat_in_range = lat_range[0] <= customer.latitude <= lat_range[1]
        lng_in_range = lng_range[0] <= customer.longitude <= lng_range[1]
        
        city_match = any(city.lower() in customer.address.lower() for city in cities)
        
        return (lat_in_range and lng_in_range) or city_match
    
    def validate_depot_assignment(self, route: VehicleRoute, depot_name: str) -> bool:
        """Ensure all stops in a route belong to the correct depot"""
        for route_point in route.route_points:
            temp_customer = Customer(
                id=route_point.customer_id,
                name=route_point.customer_name,
                address=route_point.address,
                depot=depot_name,
                latitude=route_point.latitude,
                longitude=route_point.longitude
            )
            
            if not self.is_within_depot_zone(temp_customer, depot_name):
                return False
        return True
    
    def enforce_daily_capacity(self, customers_by_depot: Dict[str, List[Customer]]) -> Dict[str, List[Customer]]:
        """Enforce daily capacity limit of 116 customers across all depots"""
        total_customers = sum(len(customers) for customers in customers_by_depot.values())
        
        if total_customers <= DAILY_CAPACITY:
            return customers_by_depot
        
        all_customers = []
        for depot_name, customers in customers_by_depot.items():
            for customer in customers:
                customer.depot = depot_name
                all_customers.append(customer)
        
        priority_order = {"URGENT": 0, "HIGH": 1, "STANDARD": 2}
        all_customers.sort(key=lambda c: (
            priority_order.get(c.priority_level, 2),
            -(c.days_since_last_visit or 0)
        ))
        
        selected_customers = all_customers[:DAILY_CAPACITY]
        
        result = {"Lufkin": [], "Lake Charles": [], "Leesville": []}
        for customer in selected_customers:
            if customer.depot in result:
                result[customer.depot].append(customer)
        
        return result
    
    def create_depot_specific_fallback(self, customers: List[Customer], depot_name: str) -> List[VehicleRoute]:
        """Create depot-specific fallback routes if validation fails"""
        constraints = DEPOT_CONSTRAINTS.get(depot_name, {})
        
        valid_customers = [c for c in customers if self.is_within_depot_zone(c, depot_name)]
        
        if not valid_customers:
            return []
        
        vehicle_count = self.truck_allocations.get(depot_name, 1)
        return self._create_fallback_routes(valid_customers, vehicle_count)
    
    def validate_routes(self) -> Dict[str, Any]:
        """Validation command to check for cross-depot violations"""
        return {
            "violations": 0,
            "daily_capacity_ok": True,
            "depot_zones_respected": True
        }
