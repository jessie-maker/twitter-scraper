# Twitter Scraper for Clawbot & Moltbot

Scrapes the top 10 most liked Twitter posts about "Clawbot" and "moltbot" using web scraping (no Twitter API needed!) and exports them to a Google Sheet with:
- **Link**: Clickable link to the tweet

## How It Works

This scraper works like other online Twitter scrapers - it uses **browser automation** (Selenium) to access Twitter's web interface directly. No Twitter API credentials needed!

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will automatically install ChromeDriver for browser automation.

### 2. Google Sheets Setup (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API and Google Drive API
4. Create a Service Account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Give it a name and create
   - Click on the service account > "Keys" > "Add Key" > "Create new key"
   - Choose JSON format and download
5. Save the JSON file as `credentials.json` in this directory
6. Share your Google Sheet with the service account email (found in the JSON file)

### 3. Run the Scraper

```bash
python scraper.py
```

The script will:
- Open a browser (headless by default) and navigate to Twitter
- Search for top 10 liked tweets about "Clawbot"
- Search for top 10 liked tweets about "moltbot"
- Sort by likes and get the top results
- Export all links to a Google Sheet (or JSON file if Google Sheets not configured)

**Note**: If Google Sheets isn't set up, the script will save results to `tweets_output.json` instead.

## Output Format

The Google Sheet will have 1 column:
- **Link**: Clickable hyperlink to the tweet

## Customization

You can customize the spreadsheet name by setting:
```bash
export SPREADSHEET_NAME="Your Custom Name"
```

You can change the Google credentials path by setting:
```bash
export GOOGLE_CREDENTIALS_PATH="path/to/your/credentials.json"
```

To see the browser in action (not headless):
```bash
export HEADLESS=false
python scraper.py
```

## Troubleshooting

- **No tweets found**: Twitter's HTML structure may have changed. The scraper tries multiple methods to find tweets.
- **Rate limiting**: Twitter may detect automated access. Try running with `HEADLESS=false` or add delays.
- **ChromeDriver issues**: The script automatically downloads ChromeDriver, but you may need Chrome browser installed.

