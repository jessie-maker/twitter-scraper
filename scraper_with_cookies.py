#!/usr/bin/env python3
"""
Twitter Scraper using your browser cookies
This works because you're already logged in to Twitter
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import re
from typing import List, Dict
import os


class TwitterScraperWithCookies:
    def __init__(self, cookies_file: str = None, headless: bool = False):
        """
        Initialize scraper with your browser cookies
        cookies_file: Path to JSON file with cookies (exported from browser)
        """
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Load cookies if provided
        if cookies_file and os.path.exists(cookies_file):
            self.load_cookies(cookies_file)
    
    def load_cookies(self, cookies_file: str):
        """Load cookies from JSON file"""
        try:
            self.driver.get("https://x.com")
            time.sleep(2)
            
            with open(cookies_file, 'r') as f:
                cookies = json.load(f)
            
            for cookie in cookies:
                try:
                    # Remove 'sameSite' if present (Selenium doesn't support it)
                    if 'sameSite' in cookie:
                        del cookie['sameSite']
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    print(f"Warning: Could not add cookie: {e}")
            
            # Refresh to apply cookies
            self.driver.refresh()
            time.sleep(3)
            print("✅ Cookies loaded successfully")
        except Exception as e:
            print(f"⚠️  Could not load cookies: {e}")
            print("Continuing without cookies - you may need to log in manually")
    
    def search_tweets(self, query: str, top_n: int = 10, sort_by_likes: bool = True) -> List[Dict]:
        """
        Search for tweets and return top N by likes
        """
        tweets = []
        
        try:
            # Navigate to Twitter search
            if sort_by_likes:
                search_url = f"https://x.com/search?q={query}&src=typed_query&f=live"
            else:
                search_url = f"https://x.com/search?q={query}&src=typed_query"
            
            print(f"Navigating to: {search_url}")
            self.driver.get(search_url)
            time.sleep(5)
            
            # Check if we need to log in
            if "login" in self.driver.current_url.lower() or "i/flow" in self.driver.current_url:
                print("⚠️  Not logged in. Please log in manually in the browser window, then press Enter...")
                input("Press Enter after you've logged in...")
                self.driver.get(search_url)
                time.sleep(5)
            
            # Scroll to load more tweets
            print("Loading tweets...")
            for scroll in range(5):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            # Try multiple selectors for tweets
            tweet_selectors = [
                'article[data-testid="tweet"]',
                'div[data-testid="tweet"]',
                'article[role="article"]',
                'div[data-testid="cellInnerDiv"] article'
            ]
            
            tweet_elements = []
            for selector in tweet_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"Found {len(elements)} tweets using selector: {selector}")
                        tweet_elements = elements
                        break
                except:
                    continue
            
            if not tweet_elements:
                print("⚠️  No tweets found. Twitter's HTML structure may have changed.")
                return []
            
            # Extract tweet data
            print(f"Extracting data from {len(tweet_elements)} tweets...")
            for element in tweet_elements[:100]:  # Check first 100 tweets
                try:
                    tweet_data = self._extract_tweet_data(element, query)
                    if tweet_data:
                        tweets.append(tweet_data)
                except Exception as e:
                    continue
            
            # Sort by likes and return top N
            tweets.sort(key=lambda x: x.get('likes', 0), reverse=True)
            print(f"✅ Found {len(tweets)} tweets, returning top {top_n}")
            return tweets[:top_n]
            
        except Exception as e:
            print(f"❌ Error searching tweets: {str(e)}")
            return []
    
    def _extract_tweet_data(self, element, query: str) -> Dict:
        """Extract data from a tweet element"""
        try:
            # Get tweet text
            text_elements = element.find_elements(By.CSS_SELECTOR, 'div[data-testid="tweetText"]')
            text = text_elements[0].text if text_elements else ""
            
            # Get author info
            author_elements = element.find_elements(By.CSS_SELECTOR, 'div[data-testid="User-Name"] a, a[role="link"]')
            author = "Unknown"
            author_url = ""
            
            if author_elements:
                try:
                    author_link = author_elements[0].get_attribute('href')
                    if author_link:
                        author_url = author_link
                        # Extract username from URL
                        match = re.search(r'x\.com/([^/]+)', author_link)
                        if match:
                            author = match.group(1)
                except:
                    pass
            
            # Get engagement metrics
            likes = 0
            retweets = 0
            replies = 0
            
            # Try to find like count
            like_selectors = [
                'button[data-testid="like"] span',
                'div[data-testid="like"] span',
                'button[aria-label*="Like"] span'
            ]
            for selector in like_selectors:
                try:
                    like_elements = element.find_elements(By.CSS_SELECTOR, selector)
                    if like_elements:
                        like_text = like_elements[-1].text
                        likes = self._parse_count(like_text)
                        break
                except:
                    continue
            
            # Get tweet URL - this is the key part
            tweet_url = ""
            
            # Method 1: Find status link directly
            status_links = element.find_elements(By.CSS_SELECTOR, 'a[href*="/status/"]')
            if status_links:
                try:
                    href = status_links[0].get_attribute('href')
                    if href and '/status/' in href:
                        tweet_url = href if href.startswith('http') else f"https://x.com{href}"
                except:
                    pass
            
            # Method 2: Construct from author and time element
            if not tweet_url:
                try:
                    time_elements = element.find_elements(By.CSS_SELECTOR, 'a[href*="/status/"] time')
                    if time_elements:
                        parent_link = time_elements[0].find_element(By.XPATH, './..')
                        href = parent_link.get_attribute('href')
                        if href:
                            tweet_url = href if href.startswith('http') else f"https://x.com{href}"
                except:
                    pass
            
            # Method 3: Extract from data attributes
            if not tweet_url:
                try:
                    # Try to get status ID from the article element
                    article = element.find_element(By.XPATH, './ancestor::article')
                    status_id = article.get_attribute('data-tweet-id')
                    if status_id and author != "Unknown":
                        tweet_url = f"https://x.com/{author}/status/{status_id}"
                except:
                    pass
            
            if not tweet_url:
                return None
            
            # Ensure x.com format
            tweet_url = tweet_url.replace('twitter.com', 'x.com')
            if '?s=' not in tweet_url:
                tweet_url += '?s=20'
            
            return {
                'text': text[:500],  # Truncate long tweets
                'author': author,
                'author_url': author_url if author_url else f"https://x.com/{author}",
                'likes': likes,
                'retweets': retweets,
                'replies': replies,
                'url': tweet_url,
                'query': query
            }
        except Exception as e:
            return None
    
    def _parse_count(self, text: str) -> int:
        """Parse count text like '1.2K', '5M' into integer"""
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
    
    def close(self):
        """Close the browser"""
        self.driver.quit()


def export_cookies_instructions():
    """Print instructions for exporting cookies"""
    print("\n" + "="*60)
    print("HOW TO EXPORT YOUR TWITTER COOKIES")
    print("="*60)
    print("\nOption 1: Using Browser Extension (Easiest)")
    print("1. Install 'Cookie-Editor' extension for Chrome/Edge")
    print("2. Go to x.com and make sure you're logged in")
    print("3. Click the extension icon")
    print("4. Click 'Export' → 'JSON'")
    print("5. Save as 'twitter_cookies.json' in this folder")
    print("\nOption 2: Manual Export (Chrome)")
    print("1. Open Chrome DevTools (F12)")
    print("2. Go to Application tab → Cookies → https://x.com")
    print("3. Copy all cookies manually (tedious)")
    print("\nOption 3: Use the scraper without cookies")
    print("The scraper will open a browser window where you can log in manually")
    print("="*60 + "\n")


def main():
    """Main function"""
    import sys
    
    print("Twitter Scraper with Your Login Session")
    print("="*60)
    
    # Check for command line arguments
    query = 'clawbot'
    top_n = 10
    
    if len(sys.argv) > 1:
        query = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            top_n = int(sys.argv[2])
        except:
            top_n = 10
    
    # Check for cookies file
    cookies_file = 'twitter_cookies.json'
    if not os.path.exists(cookies_file):
        export_cookies_instructions()
        print("⚠️  No cookies file found - will open browser for manual login")
        print("   (A browser window will open - please log in to Twitter when prompted)")
        cookies_file = None
        time.sleep(3)  # Give user time to read
    else:
        print(f"✅ Found cookies file: {cookies_file}")
    
    print(f"\n🔍 Searching for: '{query}'")
    print(f"📊 Getting top {top_n} tweets")
    
    # Initialize scraper
    print(f"\n🚀 Starting scraper...")
    scraper = TwitterScraperWithCookies(cookies_file=cookies_file, headless=False)
    
    try:
        # Search for tweets
        tweets = scraper.search_tweets(query, top_n=top_n, sort_by_likes=True)
        
        if not tweets:
            print("\n❌ No tweets found. This could be due to:")
            print("   - Twitter's HTML structure changed")
            print("   - Not logged in properly")
            print("   - Rate limiting")
            return
        
        # Display results
        print(f"\n✅ Found {len(tweets)} tweets about '{query}':\n")
        for i, tweet in enumerate(tweets, 1):
            print(f"{i}. {tweet['url']}")
            print(f"   Author: @{tweet['author']}")
            print(f"   Likes: {tweet['likes']}")
            print(f"   Text: {tweet['text'][:100]}...")
            print()
        
        # Save to file
        output_file = f'tweets_{query}_{int(time.time())}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(tweets, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved to {output_file}")
        
        # Also create CSV
        csv_file = f'tweets_{query}_{int(time.time())}.csv'
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.write('Author Name,Author URL,Post Link,Likes,Text\n')
            for tweet in tweets:
                author_name = tweet['author']
                author_url = tweet['author_url']
                post_url = tweet['url']
                likes = tweet['likes']
                text = tweet['text'].replace('"', '""')
                f.write(f'"{author_name}","{author_url}","{post_url}",{likes},"{text}"\n')
        print(f"💾 Saved to {csv_file}")
        
    finally:
        print("\n⏳ Browser will close in 10 seconds...")
        print("   (You can close it manually if you want to keep it open)")
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            print("\nClosing browser...")
        scraper.close()


if __name__ == "__main__":
    main()

