export interface Customer {
  id: number;
  name: string;
  address: string;
  depot: string;
  truck?: string;
  day?: string;
  latitude?: number;
  longitude?: number;
}

export interface RoutePoint {
  customer_id: number;
  customer_name: string;
  address: string;
  latitude: number;
  longitude: number;
  order: number;
}

export interface VehicleRoute {
  vehicle_id: number;
  depot_name: string;
  route_points: RoutePoint[];
  total_distance_miles: number;
  total_time_minutes: number;
}

export interface DepotLocation {
  name: string;
  address: string;
  latitude: number;
  longitude: number;
}

export interface RouteOptimizationResponse {
  routes: VehicleRoute[];
  total_distance_miles: number;
  total_time_minutes: number;
  depot_locations: DepotLocation[];
}

export interface RouteOptimizationRequest {
  customers: Customer[];
  num_vehicles: number;
  depot_addresses: string[];
}
