from app.google_sheets_service import GoogleSheetsService

service = GoogleSheetsService()
service.cache.clear()
service.cache_expiry.clear()
print('Cache cleared successfully')
