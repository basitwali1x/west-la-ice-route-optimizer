# Google Sheets Integration Setup Guide

## Overview
This guide explains how to set up Google Sheets API integration for the West LA ICE Route Optimizer.

## Prerequisites
- Google Cloud Console account
- Access to the target Google Sheet (ID: `1priXmXhtP2vVSQ1XUa-Y18-O96OsZ9Qw`)

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"

## Step 2: Create Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in the service account details:
   - Name: `west-la-ice-optimizer`
   - Description: `Service account for route optimization app`
4. Click "Create and Continue"
5. Skip role assignment (click "Continue")
6. Click "Done"

## Step 3: Generate Service Account Key

1. Click on the created service account
2. Go to the "Keys" tab
3. Click "Add Key" > "Create New Key"
4. Select "JSON" format
5. Click "Create" - this downloads the credentials file

## Step 4: Install Credentials

1. Rename the downloaded file to `credentials.json`
2. Place it in the `backend/` directory of this project
3. **IMPORTANT**: Never commit this file to git (it's already in .gitignore)

## Step 5: Share Google Sheet

1. Open your Google Sheet
2. Click "Share" button
3. Add the service account email as an Editor:
   - Email format: `your-service-account@your-project-id.iam.gserviceaccount.com`
   - Find this email in the `client_email` field of your credentials.json

## Step 6: Test Integration

1. Start the backend server:
   ```bash
   cd backend
   poetry run fastapi dev app/main.py
   ```

2. Test the sync endpoint:
   ```bash
   curl -X POST http://localhost:8000/sync-from-sheets \
     -H "Content-Type: application/json" \
     -d '{"sheet_id": "1priXmXhtP2vVSQ1XUa-Y18-O96OsZ9Qw", "status": "pending"}'
   ```

3. Start the frontend:
   ```bash
   cd frontend
   npm run dev
   ```

4. Open http://localhost:5173 and test the Google Sheets tab

## API Endpoints

### Sync Data from Sheets
```
POST /sync-from-sheets
Body: {"sheet_id": "1priXmXhtP2vVSQ1XUa-Y18-O96OsZ9Qw", "status": "pending"}
```

### Optimize Routes with Sheets Data
```
POST /optimize-with-sheets
Body: {"sheet_id": "1priXmXhtP2vVSQ1XUa-Y18-O96OsZ9Qw", "status": "pending"}
```

### Get Driver Routes
```
GET /driver-routes/{truck_id}?day=Monday
```

### Rebalance Trucks
```
POST /rebalance-trucks
Body: {"sheet_id": "...", "assignments": [...]}
```

## Sheet Structure Expected

The integration expects these tabs in your Google Sheet:

### Route Assignment Tab
- Columns: Depot, Truck ID, Day, Stop Sequence, Estimated Time
- Contains optimized route assignments

### Customer Data Tabs (Lufkin, Leesville, Lake Charles, etc.)
- Columns: Customer Name, Address, Phone, etc.
- Contains customer information by depot

## Troubleshooting

### Authentication Errors
- Verify credentials.json is in the correct location
- Check that the service account email has access to the sheet
- Ensure Google Sheets API is enabled in your project

### Data Sync Issues
- Verify sheet ID is correct
- Check that required tabs exist in the sheet
- Ensure sheet has proper column headers

### Permission Errors
- Service account needs Editor access to the sheet
- Check that the sheet is not restricted by organization policies

## Security Notes

- Never commit credentials.json to version control
- Rotate service account keys periodically
- Use least-privilege access (Editor access only to specific sheets)
- Monitor API usage in Google Cloud Console
