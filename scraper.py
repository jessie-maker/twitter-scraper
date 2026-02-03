#!/usr/bin/env python3
"""
Twitter Scraper for Clawbot and Moltbot
Scrapes top 10 liked tweets for each topic using web scraping (no API needed)
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import gspread
from google.oauth2.service_account import Credentials
import os
import time
import json
from typing import List, Dict
import re


class TwitterWebScraper:
    def __init__(self, headless: bool = True):
        """
        Initialize Selenium WebDriver for Twitter scraping
        No API credentials needed - uses browser automation
        """
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)
    
    def search_tweets(self, query: str, top_n: int = 10) -> List[Dict]:
        """
        Search for tweets on Twitter and extract top N by engagement
        Uses Twitter's search URL
        """
        tweets = []
        
        try:
            # Navigate to Twitter search
            search_url = f"https://twitter.com/search?q={query}&src=typed_query&f=live"
            print(f"Navigating to: {search_url}")
            self.driver.get(search_url)
            
            # Wait for tweets to load
            time.sleep(5)
            
            # Scroll to load more tweets
            for scroll in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            # Try to find tweet elements
            # Twitter's HTML structure changes frequently, so we'll try multiple selectors
            tweet_selectors = [
                'article[data-testid="tweet"]',
                'div[data-testid="tweet"]',
                'article[role="article"]',
                'div[data-testid="cellInnerDiv"] article'
            ]
            
            tweet_elements = []
            for selector in tweet_selectors:
                try:
                    tweet_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if tweet_elements:
                        print(f"Found {len(tweet_elements)} tweets using selector: {selector}")
                        break
                except:
                    continue
            
            if not tweet_elements:
                print("No tweets found. Twitter may have changed their HTML structure.")
                print("Trying alternative method...")
                return self._search_alternative_method(query, top_n)
            
            # Extract tweet data
            for element in tweet_elements[:50]:  # Check first 50 tweets
                try:
                    tweet_data = self._extract_tweet_data(element, query)
                    if tweet_data:
                        tweets.append(tweet_data)
                except Exception as e:
                    continue
            
            # Sort by likes and return top N
            tweets.sort(key=lambda x: x.get('likes', 0), reverse=True)
            return tweets[:top_n]
            
        except Exception as e:
            print(f"Error searching tweets: {str(e)}")
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
                        author = author_link.split('/')[-1] if '/' in author_link else "Unknown"
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
            
            # Get tweet URL
            tweet_link_elements = element.find_elements(By.CSS_SELECTOR, 'a[href*="/status/"]')
            tweet_url = ""
            if tweet_link_elements:
                try:
                    href = tweet_link_elements[0].get_attribute('href')
                    if href:
                        tweet_url = href if href.startswith('http') else f"https://twitter.com{href}"
                except:
                    pass
            
            # If we don't have a URL, construct it from author and status ID
            if not tweet_url and author != "Unknown":
                # Try to extract status ID from the element
                status_id = self._extract_status_id(element)
                if status_id:
                    tweet_url = f"https://twitter.com/{author}/status/{status_id}"
            
            if not tweet_url:
                return None
            
            return {
                'text': text,
                'author': author,
                'author_url': author_url if author_url else f"https://twitter.com/{author}",
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
        text = text.strip().upper()
        multipliers = {'K': 1000, 'M': 1000000, 'B': 1000000000}
        for suffix, mult in multipliers.items():
            if suffix in text:
                try:
                    num = float(text.replace(suffix, ''))
                    return int(num * mult)
                except:
                    return 0
        try:
            return int(text.replace(',', ''))
        except:
            return 0
    
    def _extract_status_id(self, element) -> str:
        """Try to extract status ID from tweet element"""
        try:
            # Look for status ID in href attributes
            links = element.find_elements(By.CSS_SELECTOR, 'a[href*="/status/"]')
            for link in links:
                href = link.get_attribute('href')
                if '/status/' in href:
                    status_id = href.split('/status/')[-1].split('?')[0]
                    if status_id.isdigit():
                        return status_id
        except:
            pass
        return None
    
    def _search_alternative_method(self, query: str, top_n: int) -> List[Dict]:
        """
        Alternative method: Use Twitter's nitter instance or different approach
        """
        print("Trying alternative scraping method...")
        # This is a fallback - you could use nitter.net or other alternatives
        return []
    
    def close(self):
        """Close the browser"""
        self.driver.quit()


class GoogleSheetsExporter:
    def __init__(self, credentials_path: str, spreadsheet_name: str = None):
        """
        Initialize Google Sheets client
        credentials_path: Path to service account JSON file
        spreadsheet_name: Name of the spreadsheet (will create if doesn't exist)
        """
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_file(credentials_path, scopes=scope)
        self.client = gspread.authorize(creds)
        
        if spreadsheet_name:
            try:
                self.spreadsheet = self.client.open(spreadsheet_name)
            except gspread.exceptions.SpreadsheetNotFound:
                # Create new spreadsheet
                self.spreadsheet = self.client.create(spreadsheet_name)
                print(f"Created new spreadsheet: {spreadsheet_name}")
        else:
            self.spreadsheet = None
    
    def export_tweets(self, tweets: List[Dict], sheet_name: str = "Tweets"):
        """
        Export tweets to Google Sheets with just the links
        """
        if not self.spreadsheet:
            raise ValueError("No spreadsheet specified")
        
        # Try to get existing worksheet or create new one
        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            worksheet.clear()
        except gspread.exceptions.WorksheetNotFound:
            worksheet = self.spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=1)
        
        # Prepare headers
        headers = ['Link']
        
        # Prepare data rows with hyperlinks using HYPERLINK formula
        rows = [headers]
        for tweet in tweets:
            tweet_url = tweet.get('url', '')
            if tweet_url:
                # Use HYPERLINK formula for clickable links
                link_formula = f'=HYPERLINK("{tweet_url}", "{tweet_url}")'
                rows.append([link_formula])
        
        # Write to sheet
        worksheet.update('A1', rows, value_input_option='USER_ENTERED')
        
        # Format header row
        worksheet.format('A1', {
            'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9},
            'textFormat': {'bold': True, 'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}}
        })
        
        # Auto-resize columns
        worksheet.columns_auto_resize(0, len(headers))
        
        print(f"Exported {len(tweets)} tweet links to sheet '{sheet_name}'")
        print(f"Spreadsheet URL: {self.spreadsheet.url}")


def main():
    """
    Main function to scrape tweets and export to Google Sheets
    """
    GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
    SPREADSHEET_NAME = os.getenv('SPREADSHEET_NAME', 'Twitter Scraper - Clawbot & Moltbot')
    HEADLESS = os.getenv('HEADLESS', 'true').lower() == 'true'
    
    # Search queries
    queries = ['Clawbot', 'moltbot']
    all_top_tweets = []
    
    # Initialize scraper (no API needed!)
    print("Starting Twitter web scraper (no API required)...")
    scraper = TwitterWebScraper(headless=HEADLESS)
    
    try:
        for query in queries:
            print(f"\nSearching for tweets about '{query}'...")
            top_tweets = scraper.search_tweets(query, top_n=10)
            print(f"Found {len(top_tweets)} top tweets for '{query}'")
            
            if top_tweets:
                print(f"Top tweet has {top_tweets[0].get('likes', 0)} likes")
                all_top_tweets.extend(top_tweets)
            
            # Small delay between searches
            time.sleep(3)
        
        if not all_top_tweets:
            print("\n⚠️  No tweets found. This could be due to:")
            print("   - Twitter's HTML structure changed")
            print("   - Rate limiting or bot detection")
            print("   - Network issues")
            print("\nSaving what we found to JSON file...")
            output_file = 'tweets_output.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_top_tweets, f, indent=2, ensure_ascii=False)
            print(f"Saved to {output_file}")
            return
        
        # Export to Google Sheets
        try:
            exporter = GoogleSheetsExporter(GOOGLE_CREDENTIALS_PATH, SPREADSHEET_NAME)
            exporter.export_tweets(all_top_tweets, sheet_name="Top Tweets")
            print(f"\n✅ Successfully exported {len(all_top_tweets)} tweet links to Google Sheets!")
        except FileNotFoundError:
            print(f"\n⚠️  Google credentials file not found at '{GOOGLE_CREDENTIALS_PATH}'")
            print("Saving to JSON file instead...")
            output_file = 'tweets_output.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_top_tweets, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved {len(all_top_tweets)} tweet links to {output_file}")
        except Exception as e:
            print(f"\n⚠️  Error exporting to Google Sheets: {str(e)}")
            print("Saving to JSON file instead...")
            output_file = 'tweets_output.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_top_tweets, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved {len(all_top_tweets)} tweet links to {output_file}")
    
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
