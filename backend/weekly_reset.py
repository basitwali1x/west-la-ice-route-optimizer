#!/usr/bin/env python3
"""
Weekly reset script for West LA Ice Route Optimization
Resets all visited_this_week flags every Monday at 12:05 AM
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from backend.app.google_sheets_service import GoogleSheetsService
from backend.app.customer_data import load_west_la_ice_customers
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reset_weekly_visits():
    """Reset all visited_this_week flags and depot counters"""
    try:
        today = datetime.now()
        if today.weekday() == 0:  # Monday
            logger.info("Starting weekly reset process...")
            
            customers = load_west_la_ice_customers()
            for customer in customers:
                customer.visited_this_week = False
            
            sheets_service = GoogleSheetsService()
            success = sheets_service.reset_weekly_visits()
            
            if success:
                logger.info(f"Weekly reset completed successfully at {datetime.now()}")
                logger.info(f"Reset {len(customers)} customer visit flags")
            else:
                logger.error("Failed to reset weekly visits in Google Sheets")
                
        else:
            logger.info(f"Not Monday (weekday: {today.weekday()}), skipping reset")
            
    except Exception as e:
        logger.error(f"Error during weekly reset: {e}")
        sys.exit(1)

if __name__ == "__main__":
    reset_weekly_visits()
