import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Any, Optional
import os
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    def __init__(self, credentials_path: str = "credentials.json"):
        self.credentials_path = credentials_path
        self.client = None
        self.cache = {}
        self.cache_expiry = {}
        self.cache_duration = timedelta(hours=6)
        
    def _authenticate(self):
        if self.client is None:
            try:
                scopes = [
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
                
                if os.path.exists(self.credentials_path):
                    credentials = Credentials.from_service_account_file(
                        self.credentials_path, scopes=scopes)
                else:
                    logger.warning(f"Credentials file not found at {self.credentials_path}")
                    return None
                    
                self.client = gspread.authorize(credentials)
                logger.info("Successfully authenticated with Google Sheets API")
            except Exception as e:
                logger.error(f"Failed to authenticate with Google Sheets: {e}")
                return None
        return self.client
    
    def _is_cache_valid(self, key: str) -> bool:
        if key not in self.cache_expiry:
            return False
        return datetime.now() < self.cache_expiry[key]
    
    def _set_cache(self, key: str, data: Any):
        self.cache[key] = data
        self.cache_expiry[key] = datetime.now() + self.cache_duration
    
    def sync_from_sheets(self, sheet_id: str) -> Dict[str, Any]:
        cache_key = f"sync_{sheet_id}"
        
        if self._is_cache_valid(cache_key):
            logger.info(f"Returning cached data for sheet {sheet_id}")
            return self.cache[cache_key]
        
        try:
            import requests
            import csv
            from io import StringIO
            
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
            logger.info(f"Attempting to access public CSV export: {csv_url}")
            
            response = requests.get(csv_url, timeout=10)
            if response.status_code == 200:
                logger.info("Successfully accessed public CSV export")
                csv_content = StringIO(response.text)
                csv_reader = csv.DictReader(csv_content)
                
                customers = []
                for row in csv_reader:
                    customer_name = (row.get('Customer') or row.get('customer') or 
                                   row.get('Customer Name') or row.get('Name') or '').strip()
                    address = (row.get('Address') or row.get('address') or '').strip()
                    
                    if customer_name and address:
                        customer = {
                            "name": customer_name,
                            "address": address,
                            "phone": (row.get('Main Phone') or row.get('Phone') or 
                                    row.get('phone') or '').strip(),
                            "depot": "all",
                            "latitude": row.get('Latitude') or row.get('latitude'),
                            "longitude": row.get('Longitude') or row.get('longitude')
                        }
                        customers.append(customer)
                
                result = {
                    "customers": {"all": customers},
                    "route_assignments": [],
                    "truck_allocations": {},
                    "last_updated": datetime.now().isoformat()
                }
                
                self._set_cache(cache_key, result)
                logger.info(f"Successfully loaded {len(customers)} customers from public CSV export")
                return result
                
        except Exception as e:
            logger.warning(f"Failed to access public CSV export: {e}")
        
        client = self._authenticate()
        if not client:
            return {"error": "Failed to authenticate with Google Sheets"}
        
        try:
            sheet = client.open_by_key(sheet_id)
            result = {
                "customers": {},
                "route_assignments": [],
                "truck_allocations": {},
                "last_updated": datetime.now().isoformat()
            }
            
            try:
                all_worksheet = sheet.worksheet('all')
                customers = self._parse_customer_data(all_worksheet)
                result["customers"]["all"] = customers
                logger.info(f"Loaded {len(customers)} customers from 'all' tab")
            except Exception as e:
                logger.error(f"Error loading 'all' worksheet: {e}")
                
            try:
                route_worksheet = sheet.worksheet('Route Assignment')
                route_assignments = self._parse_route_assignments(route_worksheet)
                result["route_assignments"] = route_assignments
            except Exception as e:
                logger.info(f"No 'Route Assignment' worksheet found: {e}")
            
            self._set_cache(cache_key, result)
            logger.info(f"Successfully synced data from sheet {sheet_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error syncing from Google Sheets: {e}")
            return {"error": str(e)}
    
    def _parse_customer_data(self, worksheet) -> List[Dict[str, Any]]:
        try:
            records = worksheet.get_all_records()
            customers = []
            
            logger.info(f"Processing worksheet '{worksheet.title}' with {len(records)} records")
            
            for record in records:
                customer_name = (record.get('Customer') or record.get('customer') or 
                               record.get('Customer Name') or record.get('Name') or '').strip()
                address = (record.get('Address') or record.get('address') or '').strip()
                
                if customer_name and address:
                    customer = {
                        "name": customer_name,
                        "address": address,
                        "phone": (record.get('Main Phone') or record.get('Phone') or 
                                record.get('phone') or '').strip(),
                        "depot": worksheet.title.lower(),
                        "latitude": record.get('Latitude') or record.get('latitude'),
                        "longitude": record.get('Longitude') or record.get('longitude')
                    }
                    customers.append(customer)
            
            logger.info(f"Parsed {len(customers)} valid customers from '{worksheet.title}'")
            return customers
        except Exception as e:
            logger.error(f"Error parsing customer data from {worksheet.title}: {e}")
            return []
    
    def _parse_route_assignments(self, worksheet) -> List[Dict[str, Any]]:
        try:
            records = worksheet.get_all_records()
            assignments = []
            
            for record in records:
                if record.get('Truck ID') and record.get('Depot'):
                    assignment = {
                        "truck_id": record.get('Truck ID', '').strip(),
                        "depot": record.get('Depot', '').strip(),
                        "day": record.get('Day', 'Monday').strip(),
                        "stop_sequence": json.loads(record.get('Stop Sequence', '[]')),
                        "estimated_time": record.get('Estimated Time', '').strip()
                    }
                    assignments.append(assignment)
            
            return assignments
        except Exception as e:
            logger.error(f"Error parsing route assignments: {e}")
            return []
    
    def _parse_day_routes(self, worksheet) -> List[Dict[str, Any]]:
        try:
            records = worksheet.get_all_records()
            routes = []
            
            for record in records:
                if record.get('Customer') and record.get('Address'):
                    route = {
                        "customer": record.get('Customer', '').strip(),
                        "address": record.get('Address', '').strip(),
                        "truck_id": record.get('Truck ID', '').strip(),
                        "stop_sequence": record.get('Stop Sequence', 0),
                        "estimated_time": record.get('Estimated Time', '').strip(),
                        "priority": record.get('Priority', '').lower() == 'high'
                    }
                    routes.append(route)
            
            return routes
        except Exception as e:
            logger.error(f"Error parsing day routes from {worksheet.title}: {e}")
            return []
    
    def update_route_assignments(self, sheet_id: str, assignments: List[Dict[str, Any]]) -> bool:
        client = self._authenticate()
        if not client:
            return False
        
        try:
            sheet = client.open_by_key(sheet_id)
            
            try:
                worksheet = sheet.worksheet("Route Assignment")
            except:
                worksheet = sheet.add_worksheet(title="Route Assignment", rows="100", cols="10")
                headers = ["Depot", "Truck ID", "Day", "Stop Sequence", "Estimated Time"]
                worksheet.append_row(headers)
            
            worksheet.clear()
            headers = ["Depot", "Truck ID", "Day", "Stop Sequence", "Estimated Time"]
            worksheet.append_row(headers)
            
            for assignment in assignments:
                row = [
                    assignment.get('depot', ''),
                    assignment.get('truck_id', ''),
                    assignment.get('day', 'Monday'),
                    json.dumps(assignment.get('stop_sequence', [])),
                    assignment.get('estimated_time', '')
                ]
                worksheet.append_row(row)
            
            cache_key = f"sync_{sheet_id}"
            if cache_key in self.cache:
                del self.cache[cache_key]
            
            logger.info(f"Successfully updated route assignments in sheet {sheet_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating route assignments: {e}")
            return False
    
    def update_visit_tracking(self, customer_id: str, customer_name: str, address: str, depot: str, visit_date: datetime, priority: str = "STANDARD") -> bool:
        """Update visit tracking in Google Sheets"""
        try:
            sheet_id = os.getenv("DEFAULT_SHEET_ID")
            if not sheet_id:
                return False
                
            sheet = self.client.open_by_key(sheet_id)
            
            try:
                worksheet = sheet.worksheet("Visit_Tracking")
            except:
                worksheet = sheet.add_worksheet(title="Visit_Tracking", rows="1000", cols="8")
                headers = ["Customer_ID", "Name", "Address", "Depot", "Last_Visit", "Days_Overdue", "Priority", "Visited_This_Week"]
                worksheet.append_row(headers)
            
            days_overdue = max(0, (datetime.now() - visit_date).days - 7)
            row = [
                customer_id,
                customer_name,
                address,
                depot,
                visit_date.strftime("%Y-%m-%d"),
                days_overdue,
                priority,
                "TRUE"
            ]
            worksheet.append_row(row)
            
            return True
        except Exception as e:
            logger.error(f"Error updating visit tracking: {e}")
            return False
    
    def reset_weekly_visits(self) -> bool:
        """Reset all visited_this_week flags in Google Sheets"""
        try:
            sheet_id = os.getenv("DEFAULT_SHEET_ID")
            if not sheet_id:
                return False
                
            sheet = self.client.open_by_key(sheet_id)
            
            try:
                worksheet = sheet.worksheet("Visit_Tracking")
                all_records = worksheet.get_all_records()
                
                worksheet.clear()
                headers = ["Customer_ID", "Name", "Address", "Depot", "Last_Visit", "Days_Overdue", "Priority", "Visited_This_Week"]
                worksheet.append_row(headers)
                
                for record in all_records:
                    row = [
                        record.get("Customer_ID", ""),
                        record.get("Name", ""),
                        record.get("Address", ""),
                        record.get("Depot", ""),
                        record.get("Last_Visit", ""),
                        record.get("Days_Overdue", 0),
                        record.get("Priority", "STANDARD"),
                        "FALSE"
                    ]
                    worksheet.append_row(row)
                
                self.log_reset(datetime.now())
                return True
            except:
                return True
                
        except Exception as e:
            logger.error(f"Error resetting weekly visits: {e}")
            return False
    
    def log_reset(self, reset_date: datetime) -> bool:
        """Log weekly reset event"""
        try:
            sheet_id = os.getenv("DEFAULT_SHEET_ID")
            if not sheet_id:
                return False
                
            sheet = self.client.open_by_key(sheet_id)
            
            try:
                worksheet = sheet.worksheet("Reset_Log")
            except:
                worksheet = sheet.add_worksheet(title="Reset_Log", rows="100", cols="3")
                headers = ["Reset_Date", "Status", "Notes"]
                worksheet.append_row(headers)
            
            row = [
                reset_date.strftime("%Y-%m-%d %H:%M:%S"),
                "SUCCESS",
                "Weekly visit flags reset automatically"
            ]
            worksheet.append_row(row)
            
            return True
        except Exception as e:
            logger.error(f"Error logging reset: {e}")
            return False
