export interface Customer {
  id: number;
  name: string;
  address: string;
  depot: string;
  truck?: string;
  day?: string;
  latitude?: number;
  longitude?: number;
  last_visit_date?: string;
  visited_this_week?: boolean;
  days_since_last_visit?: number;
  priority_level?: string;
  weekly_visit_required?: boolean;
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
  compliance?: { [key: string]: boolean };
  violations?: string[];
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
  status: string;
  progress: number;
  constraint_violations?: string[];
}

export interface RouteOptimizationRequest {
  customers: Customer[];
  num_vehicles: number;
  depot_addresses: string[];
  vehicle_distribution?: { [key: string]: number };
}

export interface WeeklyVisitStatus {
  depot_name: string;
  total_customers: number;
  visited_this_week: number;
  pending_visits: number;
  overdue_customers: number;
  completion_percentage: number;
}

export interface WeeklyResetRequest {
  force_reset?: boolean;
  reset_date?: string;
}

export interface VisitTrackingUpdate {
  customer_id: number;
  visited_date: string;
  depot: string;
  truck_id?: string;
}
