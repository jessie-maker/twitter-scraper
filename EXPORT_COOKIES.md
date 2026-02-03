# How to Export Twitter Cookies for Scraping

Since you're already logged in to Twitter, we can use your session to scrape! Here's how:

## Quick Method: Browser Extension (Recommended)

### Step 1: Install Cookie-Editor Extension
- **Chrome**: https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm
- **Edge**: https://microsoftedge.microsoft.com/addons/detail/cookie-editor/ajfboaconbpkglpfanefocmgjjdhpamj
- **Firefox**: https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/

### Step 2: Export Cookies
1. Go to **x.com** (make sure you're logged in)
2. Click the **Cookie-Editor** extension icon
3. Click **"Export"** button
4. Select **"JSON"** format
5. Copy the JSON content

### Step 3: Save Cookies File
1. Create a file named `twitter_cookies.json` in this folder
2. Paste the JSON content
3. Save the file

## Alternative: Manual Method (Chrome)

1. Open Chrome DevTools (F12 or Cmd+Option+I)
2. Go to **Application** tab
3. In left sidebar: **Storage** → **Cookies** → **https://x.com**
4. You'll see all cookies - but this is tedious to copy manually

## Using the Scraper

Once you have `twitter_cookies.json`:

```bash
python3 scraper_with_cookies.py
```

The scraper will:
- Load your cookies (so you're logged in)
- Search for tweets
- Extract real URLs like: `https://x.com/qrimeCapital/status/2017352450034880665?s=20`
- Sort by likes
- Save results to JSON and CSV

## No Cookies? No Problem!

If you don't export cookies, the scraper will:
- Open a browser window
- Wait for you to log in manually
- Then proceed with scraping

## Why This Works

When you're logged in to Twitter, your browser stores authentication cookies. By using those same cookies in the scraper, Twitter thinks it's you browsing, not a bot. This bypasses most blocking!


