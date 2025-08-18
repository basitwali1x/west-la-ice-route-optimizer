from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from typing import List, Dict, Optional
import asyncio
import math
from .models import Customer, VehicleRoute, RoutePoint
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
    "Lufkin": {"max_distance": 50, "max_stops_monday": 15, "max_hours": 10},
    "Lake Charles": {"max_distance": 75, "max_stops": 15, "max_hours": 10},
    "Leesville": {"max_distance": 100, "max_stops": 15, "max_hours": 10}
}

class RouteOptimizer:
    def __init__(self):
        self.google_maps = GoogleMapsService()
    
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
        
        all_routes = []
        
        for depot_name, depot_customers in customers_by_depot.items():
            if not depot_customers:
                continue
                
            depot_address = depot_mapping[depot_name]
            vehicles_for_depot = self._calculate_vehicles_per_depot(depot_name, num_vehicles, vehicle_distribution)
            
            depot_routes = await self._optimize_single_depot_routes(
                depot_customers, depot_address, depot_name, vehicles_for_depot
            )
            all_routes.extend(depot_routes)
        
        return all_routes
    
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
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.FromSeconds(30)
        
        solution = routing.SolveWithParameters(search_parameters)
        
        if solution:
            return await self._extract_routes(
                manager, routing, solution, customers, geocoded_locations, distance_matrix, depot_name
            )
        else:
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
        """Create fallback routes using simple round-robin assignment"""
        routes = []
        
        customers_per_vehicle = len(customers) // num_vehicles
        remainder = len(customers) % num_vehicles
        
        start_idx = 0
        for vehicle_id in range(num_vehicles):
            vehicle_customers = customers_per_vehicle + (1 if vehicle_id < remainder else 0)
            
            if vehicle_customers == 0:
                continue
                
            end_idx = start_idx + vehicle_customers
            vehicle_customer_list = customers[start_idx:end_idx]
            
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
            
            start_idx = end_idx
        
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
