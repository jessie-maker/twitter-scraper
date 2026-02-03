#!/usr/bin/env python3
"""
Create Google Sheet with search URLs and template for manual entry
"""

import gspread
from google.oauth2.service_account import Credentials
import os

def create_sheet():
    GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
    SPREADSHEET_NAME = os.getenv('SPREADSHEET_NAME', 'Twitter Scraper - Clawbot & Moltbot')
    
    try:
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=scope)
        client = gspread.authorize(creds)
        
        try:
            spreadsheet = client.open(SPREADSHEET_NAME)
            print(f"Using existing spreadsheet: {SPREADSHEET_NAME}")
        except gspread.exceptions.SpreadsheetNotFound:
            spreadsheet = client.create(SPREADSHEET_NAME)
            print(f"Created new spreadsheet: {SPREADSHEET_NAME}")
        
        # Create or clear the sheet
        try:
            worksheet = spreadsheet.worksheet("Top Tweets")
            worksheet.clear()
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title="Top Tweets", rows=100, cols=2)
        
        # Add headers and search URLs
        headers = ['Link', 'Instructions']
        rows = [headers]
        
        # Add search URLs as instructions
        rows.append([
            '=HYPERLINK("https://twitter.com/search?q=Clawbot&src=typed_query&f=live", "Search: Clawbot")',
            'Click link above, sort by "Most liked", copy top 10 tweet URLs below'
        ])
        rows.append(['', ''])  # Empty row
        
        rows.append([
            '=HYPERLINK("https://twitter.com/search?q=moltbot&src=typed_query&f=live", "Search: moltbot")',
            'Click link above, sort by "Most liked", copy top 10 tweet URLs below'
        ])
        rows.append(['', ''])  # Empty row
        
        rows.append(['', 'Paste tweet links below:'])
        rows.append(['Link', ''])
        
        # Add empty rows for manual entry
        for i in range(25):
            rows.append(['', ''])
        
        worksheet.update('A1', rows, value_input_option='USER_ENTERED')
        
        # Format
        worksheet.format('A1:B1', {
            'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9},
            'textFormat': {'bold': True, 'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}}
        })
        
        worksheet.columns_auto_resize(0, 2)
        
        print(f"\n✅ Created Google Sheet with search links!")
        print(f"📊 Spreadsheet URL: {spreadsheet.url}")
        print(f"\nInstructions:")
        print(f"1. Open the sheet and click the search links")
        print(f"2. On Twitter, sort by 'Most liked'")
        print(f"3. Copy the top 10 tweet URLs for each topic")
        print(f"4. Paste them in the 'Link' column starting from row 8")
        
    except FileNotFoundError:
        print(f"❌ Google credentials not found at {GOOGLE_CREDENTIALS_PATH}")
        print("\nTo set up Google Sheets:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a project and enable Google Sheets API")
        print("3. Create a Service Account and download JSON key")
        print("4. Save it as 'credentials.json' in this directory")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_sheet()


