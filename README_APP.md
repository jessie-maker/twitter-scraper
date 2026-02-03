# Twitter Scraper App - Complete Guide

## Quick Start

### Option 1: Use the HTML App (Easiest - Works Immediately!)

1. **Open the app:**
   ```bash
   open twitter_scraper_app.html
   ```
   Or just double-click `twitter_scraper_app.html` in your file browser

2. **Search for posts:**
   - Enter a prompt like: "give me the top 50 liked twitter posts with keyword OpenClaw"
   - Click "Search" or press Enter
   - View results in a beautiful table

3. **Download results:**
   - Click "Download Results" button
   - Get a CSV file with all 4 columns:
     - Author Name (with hyperlink)
     - Post Link
     - Theme (Use Case or Other)
     - Summary (one sentence)

### Option 2: Use with Backend API (For Live Scraping)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Flask backend:**
   ```bash
   python3 app.py
   ```

3. **Open the app:**
   - The app will automatically connect to the backend
   - If backend is not running, it uses mock data

## Features

✅ **Search bar** - Enter natural language prompts  
✅ **Results table** - Beautiful, sortable table with all data  
✅ **4 columns** as requested:
   - Author's Name (hyperlink to profile)
   - Link to Post
   - Theme (Use Case or Other)
   - Summary (one sentence for use cases)

✅ **Download button** - Export to CSV  
✅ **Example prompts** - Quick click to try  
✅ **Works offline** - Uses mock data if backend unavailable

## Example Prompts

- "give me the top 50 liked twitter posts with keyword OpenClaw"
- "give me the top 50 liked twitter posts with keyword moltbot"
- "give me the top 20 liked twitter posts about AI agents"
- "top 30 posts about automation"

## Files

- `twitter_scraper_app.html` - Main app (works standalone!)
- `app.py` - Flask backend API (optional)
- `use_cases_summary.md` - Summary of use cases found
- `requirements.txt` - Python dependencies

## Notes

- The app includes mock data for "openclaw" and "moltbot" with 10 use cases each
- For live scraping, you'll need to set up the backend and handle Twitter's restrictions
- The CSV export includes all 4 columns as requested
- All links are clickable in the web interface

Enjoy! 🐦


