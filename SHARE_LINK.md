# 🌐 Share Your Twitter Scraper

## Quick Start

The web server is now running! Here's how to access it:

### On This Computer:
```
http://localhost:5000
```

### From Other Devices (Same Network):
```
http://[YOUR_IP]:5000
```

To find your IP address, run:
```bash
# Mac/Linux:
ifconfig | grep "inet " | grep -v 127.0.0.1

# Or:
hostname -I
```

## How to Share

1. **Find your local IP address** (see above)
2. **Share this link**: `http://[YOUR_IP]:5000`
3. **Make sure**:
   - Other devices are on the same WiFi/network
   - Your firewall allows connections on port 5000

## For Internet Access (Optional)

To make it accessible from anywhere:

### Option 1: ngrok (Easiest)
```bash
# Install ngrok: https://ngrok.com/
ngrok http 5000
# Share the ngrok URL (e.g., https://abc123.ngrok.io)
```

### Option 2: Deploy to Cloud
- Heroku
- Railway
- Render
- DigitalOcean

## How It Works

1. User opens the link in their browser
2. Enters search term (e.g., "clawbot")
3. Clicks "Start Scraping"
4. A browser window opens automatically
5. User logs in to Twitter (if needed)
6. Scraper collects tweets and shows real links
7. User can download results as CSV

## Stop the Server

Press `Ctrl+C` in the terminal where it's running.

## Restart

```bash
python3 web_scraper.py
```


