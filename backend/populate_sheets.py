import gspread
from google.oauth2.service_account import Credentials
import csv
import os

def populate_google_sheets():
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    credentials = Credentials.from_service_account_file('credentials.json', scopes=scopes)
    client = gspread.authorize(credentials)
    
    sheet_id = '1et9tMDnHlc1nUQymyeyL2w_GLvzvBJL0XHN1NRzADgc'
    sheet = client.open_by_key(sheet_id)
    
    try:
        worksheet = sheet.worksheet('all')
    except:
        print("'all' worksheet not found, creating it...")
        worksheet = sheet.add_worksheet(title='all', rows=1000, cols=10)
    
    worksheet.clear()
    
    csv_path = '/home/ubuntu/attachments/eeead544-0cf9-49dd-b31e-e0dfcc258f07/google_sheets_import.csv'
    
    with open(csv_path, 'r', encoding='utf-8') as file:
        csv_reader = csv.reader(file)
        data = list(csv_reader)
    
    print(f"Read {len(data)} rows from CSV file (including header)")
    print(f"Customer records: {len(data) - 1}")
    
    batch_size = 100
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        start_row = i + 1
        end_row = start_row + len(batch) - 1
        
        range_name = f'A{start_row}:E{end_row}'
        
        print(f"Uploading batch {i//batch_size + 1}: rows {start_row}-{end_row}")
        try:
            worksheet.update(range_name, batch)
            print(f"  ✓ Successfully uploaded batch {i//batch_size + 1}")
        except Exception as e:
            print(f"  ✗ Error uploading batch {i//batch_size + 1}: {e}")
            return False
    
    print(f"Successfully populated 'all' tab with {len(data)} rows")
    
    all_values = worksheet.get_all_values()
    print(f"Verification: Sheet now contains {len(all_values)} rows")
    print(f"Customer records in sheet: {len(all_values) - 1}")
    
    if len(all_values) > 1:
        print(f"First data row: {all_values[1]}")
        print(f"Last data row: {all_values[-1]}")
    
    return True

if __name__ == "__main__":
    success = populate_google_sheets()
    if success:
        print("\n✓ Google Sheets population completed successfully!")
    else:
        print("\n✗ Google Sheets population failed!")
