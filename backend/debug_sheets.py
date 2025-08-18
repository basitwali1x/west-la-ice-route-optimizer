#!/usr/bin/env python3

import gspread
from google.oauth2.service_account import Credentials
import sys

def test_sheets_access():
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_file(
            'credentials.json', scopes=scopes)
        client = gspread.authorize(credentials)
        print("✓ Authentication successful")
        
        sheet_id = "1et9tMDnHlc1nUQymyeyL2w_GLvzvBJL0XHN1NRzADgc"
        
        try:
            sheet = client.open_by_key(sheet_id)
            print(f"✓ Sheet opened by key: {sheet.title}")
        except Exception as e:
            print(f"✗ open_by_key failed: {e}")
            
            try:
                sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
                sheet = client.open_by_url(sheet_url)
                print(f"✓ Sheet opened by URL: {sheet.title}")
            except Exception as e2:
                print(f"✗ open_by_url failed: {e2}")
                
                try:
                    all_sheets = client.openall()
                    print(f"✓ Found {len(all_sheets)} accessible sheets:")
                    for s in all_sheets:
                        print(f"  - {s.title} (id: {s.id})")
                        if sheet_id in s.id:
                            print(f"    ^ This matches our target sheet!")
                            sheet = s
                            break
                    else:
                        print("✗ Target sheet not found in accessible sheets")
                        
                        try:
                            from googleapiclient.discovery import build
                            service = build('sheets', 'v4', credentials=credentials)
                            
                            worksheets_to_try = ['all', 'jasper', 'leesville', 'lufkin']
                            
                            for ws_name in worksheets_to_try:
                                try:
                                    range_name = f'{ws_name}!A1:C10'
                                    result = service.spreadsheets().values().get(
                                        spreadsheetId=sheet_id, range=range_name).execute()
                                    values = result.get('values', [])
                                    print(f"✓ Direct data access successful for '{ws_name}': {len(values)} rows")
                                    if values:
                                        print(f"  Headers: {values[0] if values else 'None'}")
                                        print(f"  Sample data: {values[1] if len(values) > 1 else 'No data rows'}")
                                    return True
                                except Exception as ws_error:
                                    print(f"✗ Failed to access worksheet '{ws_name}': {ws_error}")
                                    continue
                            
                            print("✗ All worksheet access attempts failed")
                            return False
                            
                        except Exception as e4:
                            print(f"✗ Direct Sheets API failed: {e4}")
                            return False
                except Exception as e3:
                    print(f"✗ openall failed: {e3}")
                    return False
        
        worksheets = sheet.worksheets()
        print(f"✓ Found {len(worksheets)} worksheets:")
        for ws in worksheets:
            print(f"  - {ws.title} (id: {ws.id})")
        
        if worksheets:
            first_ws = worksheets[0]
            print(f"\n✓ Accessing worksheet: {first_ws.title}")
            
            try:
                records = first_ws.get_all_records()
                print(f"✓ get_all_records() successful: {len(records)} records")
                if records:
                    print(f"  First record keys: {list(records[0].keys())}")
            except Exception as e:
                print(f"✗ get_all_records() failed: {e}")
                
                try:
                    values = first_ws.get_all_values()
                    print(f"✓ get_all_values() successful: {len(values)} rows")
                    if values:
                        print(f"  Headers: {values[0]}")
                except Exception as e2:
                    print(f"✗ get_all_values() failed: {e2}")
                    
                    try:
                        range_values = first_ws.get('A1:E5')
                        print(f"✓ Range access successful: {len(range_values)} rows")
                        print(f"  Sample data: {range_values}")
                    except Exception as e3:
                        print(f"✗ Range access failed: {e3}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Testing Google Sheets API access...")
    success = test_sheets_access()
    sys.exit(0 if success else 1)
