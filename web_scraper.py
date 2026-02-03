#!/usr/bin/env python3
"""
Web-based Twitter Scraper - Accessible via browser
Run this and share the URL with others
"""

from flask import Flask, render_template_string, request, jsonify, send_from_directory
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import re
import threading
import os
from typing import List, Dict

app = Flask(__name__)
CORS(app)

# Store active browser sessions
active_sessions = {}

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Twitter Scraper - Web Version</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #1da1f2 0%, #0d8bd9 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 32px; margin-bottom: 10px; }
        .content { padding: 30px; }
        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .search-input {
            flex: 1;
            padding: 15px 20px;
            border: 2px solid #e1e8ed;
            border-radius: 8px;
            font-size: 16px;
        }
        .search-input:focus {
            outline: none;
            border-color: #1da1f2;
        }
        .btn {
            background: #1da1f2;
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn:hover { background: #1a91da; transform: translateY(-2px); }
        .btn:disabled { background: #ccc; cursor: not-allowed; }
        .info-box {
            background: #e8f5fe;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #1da1f2;
        }
        .results-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        .results-table th {
            background: #f8f9fa;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #e1e8ed;
        }
        .results-table td {
            padding: 15px;
            border-bottom: 1px solid #e1e8ed;
        }
        .results-table tr:hover { background: #f8f9fa; }
        .link { color: #1da1f2; text-decoration: none; }
        .link:hover { text-decoration: underline; }
        .loading {
            text-align: center;
            padding: 40px;
            color: #657786;
        }
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #1da1f2;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .download-btn {
            background: #28a745;
            margin-top: 20px;
        }
        .download-btn:hover { background: #218838; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐦 Twitter Scraper</h1>
            <p>Search and extract real Twitter/X post links</p>
        </div>
        <div class="content">
            <div class="info-box">
                <strong>How it works:</strong> This tool opens a browser window where you can log in to Twitter.
                Then it searches for tweets and extracts real links. The browser window will open automatically.
            </div>
            
            <div class="search-box">
                <input type="text" id="searchInput" class="search-input" 
                       placeholder="Enter search term (e.g., 'clawbot', 'openclaw', 'moltbot')" 
                       value="clawbot">
                <input type="number" id="countInput" class="search-input" 
                       placeholder="Number of tweets" value="10" style="width: 150px;">
                <button class="btn" onclick="startScrape()">Start Scraping</button>
            </div>
            
            <div id="status"></div>
            <div id="results"></div>
        </div>
    </div>

    <script>
        let sessionId = null;
        
        async function startScrape() {
            const query = document.getElementById('searchInput').value.trim();
            const count = parseInt(document.getElementById('countInput').value) || 10;
            
            if (!query) {
                alert('Please enter a search term');
                return;
            }
            
            document.getElementById('status').innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Starting scraper... A browser window will open. Please log in to Twitter if needed.</p>
                </div>
            `;
            document.getElementById('results').innerHTML = '';
            
            try {
                const response = await fetch('/api/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query, count })
                });
                
                const data = await response.json();
                sessionId = data.sessionId;
                
                // Poll for results
                pollResults();
            } catch (error) {
                document.getElementById('status').innerHTML = `
                    <div style="background: #fee; color: #c33; padding: 15px; border-radius: 8px;">
                        Error: ${error.message}
                    </div>
                `;
            }
        }
        
        async function pollResults() {
            if (!sessionId) return;
            
            try {
                const response = await fetch(`/api/status/${sessionId}`);
                const data = await response.json();
                
                if (data.status === 'completed') {
                    displayResults(data.results);
                    document.getElementById('status').innerHTML = `
                        <div style="background: #d4edda; color: #155724; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                            ✅ Found ${data.results.length} tweets!
                        </div>
                    `;
                } else if (data.status === 'error') {
                    document.getElementById('status').innerHTML = `
                        <div style="background: #fee; color: #c33; padding: 15px; border-radius: 8px;">
                            ❌ Error: ${data.error}
                        </div>
                    `;
                } else {
                    document.getElementById('status').innerHTML = `
                        <div class="loading">
                            <div class="spinner"></div>
                            <p>${data.message || 'Scraping in progress...'}</p>
                            <p style="font-size: 12px; color: #999;">Check the browser window that opened</p>
                        </div>
                    `;
                    setTimeout(pollResults, 2000);
                }
            } catch (error) {
                setTimeout(pollResults, 2000);
            }
        }
        
        function displayResults(results) {
            if (!results || results.length === 0) {
                document.getElementById('results').innerHTML = '<p>No results found.</p>';
                return;
            }
            
            let html = `
                <button class="btn download-btn" onclick="downloadCSV()">📥 Download CSV</button>
                <table class="results-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Author</th>
                            <th>Post Link</th>
                            <th>Likes</th>
                            <th>Preview</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            results.forEach((tweet, i) => {
                html += `
                    <tr>
                        <td>${i + 1}</td>
                        <td><a href="${tweet.author_url}" target="_blank" class="link">@${tweet.author}</a></td>
                        <td><a href="${tweet.url}" target="_blank" class="link">${tweet.url}</a></td>
                        <td>${tweet.likes || 0}</td>
                        <td>${(tweet.text || '').substring(0, 100)}...</td>
                    </tr>
                `;
            });
            
            html += '</tbody></table>';
            document.getElementById('results').innerHTML = html;
            
            // Store results globally for download
            window.currentResults = results;
        }
        
        function downloadCSV() {
            if (!window.currentResults) return;
            
            let csv = 'Author,Author URL,Post Link,Likes,Text\\n';
            window.currentResults.forEach(tweet => {
                const author = tweet.author || '';
                const authorUrl = tweet.author_url || '';
                const postUrl = tweet.url || '';
                const likes = tweet.likes || 0;
                const text = (tweet.text || '').replace(/"/g, '""');
                csv += `"${author}","${authorUrl}","${postUrl}",${likes},"${text}"\\n`;
            });
            
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `twitter_results_${Date.now()}.csv`;
            a.click();
        }
    </script>
</body>
</html>
'''

def create_driver():
    """Create a Chrome driver instance"""
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_tweets(driver, query: str, top_n: int = 10) -> List[Dict]:
    """Scrape tweets using the driver"""
    tweets = []
    
    try:
        search_url = f"https://x.com/search?q={query}&src=typed_query&f=live"
        driver.get(search_url)
        time.sleep(5)
        
        # Check if login needed
        if "login" in driver.current_url.lower() or "i/flow" in driver.current_url:
            return None  # Signal that login is needed
        
        # Scroll to load tweets
        for scroll in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        
        # Find tweets
        tweet_selectors = [
            'article[data-testid="tweet"]',
            'div[data-testid="tweet"]',
            'article[role="article"]'
        ]
        
        tweet_elements = []
        for selector in tweet_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    tweet_elements = elements
                    break
            except:
                continue
        
        # Extract data
        for element in tweet_elements[:100]:
            try:
                tweet_data = extract_tweet_data(element, query)
                if tweet_data:
                    tweets.append(tweet_data)
            except:
                continue
        
        tweets.sort(key=lambda x: x.get('likes', 0), reverse=True)
        return tweets[:top_n]
        
    except Exception as e:
        print(f"Error: {e}")
        return []

def extract_tweet_data(element, query: str) -> Dict:
    """Extract data from tweet element"""
    try:
        # Get text
        text_elements = element.find_elements(By.CSS_SELECTOR, 'div[data-testid="tweetText"]')
        text = text_elements[0].text if text_elements else ""
        
        # Get author
        author = "Unknown"
        author_url = ""
        author_elements = element.find_elements(By.CSS_SELECTOR, 'div[data-testid="User-Name"] a, a[role="link"]')
        if author_elements:
            try:
                href = author_elements[0].get_attribute('href')
                if href:
                    author_url = href
                    match = re.search(r'x\.com/([^/]+)', href)
                    if match:
                        author = match.group(1)
            except:
                pass
        
        # Get likes
        likes = 0
        like_selectors = ['button[data-testid="like"] span', 'div[data-testid="like"] span']
        for selector in like_selectors:
            try:
                like_elements = element.find_elements(By.CSS_SELECTOR, selector)
                if like_elements:
                    like_text = like_elements[-1].text
                    likes = parse_count(like_text)
                    break
            except:
                continue
        
        # Get URL
        tweet_url = ""
        status_links = element.find_elements(By.CSS_SELECTOR, 'a[href*="/status/"]')
        if status_links:
            try:
                href = status_links[0].get_attribute('href')
                if href and '/status/' in href:
                    tweet_url = href if href.startswith('http') else f"https://x.com{href}"
            except:
                pass
        
        if not tweet_url:
            return None
        
        tweet_url = tweet_url.replace('twitter.com', 'x.com')
        if '?s=' not in tweet_url:
            tweet_url += '?s=20'
        
        return {
            'text': text[:500],
            'author': author,
            'author_url': author_url if author_url else f"https://x.com/{author}",
            'likes': likes,
            'url': tweet_url,
            'query': query
        }
    except:
        return None

def parse_count(text: str) -> int:
    """Parse count like '1.2K' to integer"""
    if not text:
        return 0
    text = text.strip().upper().replace(',', '')
    multipliers = {'K': 1000, 'M': 1000000, 'B': 1000000000}
    for suffix, mult in multipliers.items():
        if suffix in text:
            try:
                num = float(re.sub(r'[^\d.]', '', text))
                return int(num * mult)
            except:
                return 0
    try:
        return int(re.sub(r'[^\d]', '', text))
    except:
        return 0

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/start', methods=['POST'])
def start_scrape():
    """Start a scraping session"""
    data = request.json
    query = data.get('query', 'clawbot')
    count = data.get('count', 10)
    
    session_id = f"session_{int(time.time())}"
    
    # Start scraping in background thread
    def scrape_thread():
        driver = create_driver()
        active_sessions[session_id] = {
            'status': 'running',
            'message': 'Browser window opened. Please log in if needed...',
            'driver': driver,
            'results': None
        }
        
        try:
            time.sleep(3)  # Give time for browser to open
            results = scrape_tweets(driver, query, count)
            
            if results is None:
                active_sessions[session_id] = {
                    'status': 'login_required',
                    'message': 'Please log in to Twitter in the browser window, then click "Retry"',
                    'driver': driver,
                    'results': None
                }
            else:
                active_sessions[session_id] = {
                    'status': 'completed',
                    'message': f'Found {len(results)} tweets',
                    'driver': driver,
                    'results': results
                }
        except Exception as e:
            active_sessions[session_id] = {
                'status': 'error',
                'error': str(e),
                'driver': driver,
                'results': None
            }
    
    threading.Thread(target=scrape_thread, daemon=True).start()
    
    return jsonify({'sessionId': session_id})

@app.route('/api/status/<session_id>')
def get_status(session_id):
    """Get scraping status"""
    if session_id not in active_sessions:
        return jsonify({'status': 'not_found'}), 404
    
    session = active_sessions[session_id]
    response = {
        'status': session['status'],
        'message': session.get('message', ''),
        'results': session.get('results')
    }
    
    if session['status'] == 'error':
        response['error'] = session.get('error', 'Unknown error')
    
    return jsonify(response)

@app.route('/api/close/<session_id>', methods=['POST'])
def close_session(session_id):
    """Close a browser session"""
    if session_id in active_sessions:
        try:
            active_sessions[session_id]['driver'].quit()
        except:
            pass
        del active_sessions[session_id]
    return jsonify({'success': True})

if __name__ == '__main__':
    import socket
    
    # Get local IP address
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    port = int(os.environ.get('PORT', 5000))
    
    print("\n" + "="*60)
    print("🌐 Twitter Scraper Web Server")
    print("="*60)
    print(f"\n✅ Server starting...")
    print(f"\n📱 Access from this computer:")
    print(f"   http://localhost:{port}")
    print(f"\n🌍 Access from other devices on your network:")
    print(f"   http://{local_ip}:{port}")
    print(f"\n💡 Share this link with others!")
    print(f"\n⚠️  Make sure your firewall allows connections on port {port}")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)


