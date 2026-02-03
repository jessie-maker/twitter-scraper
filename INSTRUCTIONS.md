# Twitter Scraper - Instructions

## Quick Start

Since Twitter has strong anti-scraping measures, here's the easiest way to collect the top 10 liked tweets:

### Option 1: Use the HTML Tool (Easiest!)

1. Open `twitter_collector.html` in your web browser
2. Click the search links to open Twitter
3. On Twitter, sort by "Most liked"
4. Copy the top 10 tweet URLs for each topic
5. Paste them in the tool
6. Export to CSV or copy the links

### Option 2: Manual Collection

1. Go to these search URLs:
   - **Clawbot**: https://twitter.com/search?q=Clawbot&src=typed_query&f=live
   - **moltbot**: https://twitter.com/search?q=moltbot&src=typed_query&f=live

2. On Twitter:
   - Click the filter/sort button
   - Select "Most liked"
   - Copy the URLs of the top 10 tweets

3. Paste them into a text file or directly into Google Sheets

### Option 3: Google Sheets Setup

If you want to use Google Sheets:

1. Go to https://console.cloud.google.com/
2. Create a project
3. Enable Google Sheets API and Google Drive API
4. Create a Service Account
5. Download the JSON key file
6. Save it as `credentials.json` in this folder
7. Run: `python3 create_sheet.py`

This will create a Google Sheet with clickable search links and space to paste your collected tweet URLs.

## Files Created

- `twitter_collector.html` - Interactive tool to collect and format links
- `create_sheet.py` - Script to create Google Sheet (requires credentials)
- `scraper.py` - Main scraper (may not work due to Twitter restrictions)
- `scraper_final.py` - Alternative scraper using Nitter
- `search_urls.txt` - Direct search URLs

## Why Automated Scraping Doesn't Work

Twitter/X actively blocks automated scraping through:
- Bot detection
- Rate limiting
- Requiring login for many searches
- Frequently changing HTML structure

The HTML tool provides the easiest way to manually collect and format the links!


