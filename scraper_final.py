#!/usr/bin/env python3
"""
Final Twitter Scraper - Uses multiple methods to get tweet links
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from typing import List, Dict
import gspread
from google.oauth2.service_account import Credentials
import os
import time


def search_via_nitter(query: str) -> List[Dict]:
    """Search using nitter instances"""
    nitter_instances = [
        'https://nitter.net',
        'https://nitter.it',
        'https://nitter.42l.fr',
    ]
    
    tweets = []
    
    for base_url in nitter_instances:
        try:
            url = f"{base_url}/search?f=tweets&q={query}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            
            print(f"Trying {base_url}...")
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find tweet containers
                tweet_containers = soup.find_all('div', class_='tweet')
                if not tweet_containers:
                    tweet_containers = soup.find_all('div', attrs={'data-tweet-id': True})
                
                for container in tweet_containers[:30]:
                    try:
                        # Get tweet text
                        text_elem = container.find('div', class_='tweet-content')
                        if not text_elem:
                            text_elem = container.find('div', class_='tweet-body')
                        text = text_elem.get_text(strip=True) if text_elem else ""
                        
                        # Get author
                        author_elem = container.find('a', class_='username')
                        if not author_elem:
                            author_elem = container.find('a', href=re.compile(r'/.*'))
                        author = "Unknown"
                        if author_elem:
                            author_text = author_elem.get_text(strip=True)
                            author = author_text.replace('@', '')
                        
                        # Get tweet link
                        tweet_link = None
                        # Try to find status link
                        status_link = container.find('a', href=re.compile(r'/.*/status/\d+'))
                        if status_link:
                            href = status_link.get('href', '')
                            if href.startswith('http'):
                                tweet_link = href
                            else:
                                tweet_link = f"{base_url}{href}"
                        
                        # If no direct link, construct from author and tweet ID
                        if not tweet_link:
                            tweet_id = container.get('data-tweet-id')
                            if tweet_id and author != "Unknown":
                                tweet_link = f"https://twitter.com/{author}/status/{tweet_id}"
                        
                        # Get engagement metrics
                        stats = container.find('span', class_='tweet-stat')
                        likes = 0
                        if stats:
                            like_text = stats.get_text()
                            likes = parse_engagement(like_text)
                        
                        if tweet_link:
                            tweets.append({
                                'text': text[:200],  # Truncate
                                'author': author,
                                'url': tweet_link.replace(base_url, 'https://twitter.com'),
                                'likes': likes,
                                'query': query
                            })
                    except Exception as e:
                        continue
                
                if tweets:
                    print(f"✅ Found {len(tweets)} tweets from {base_url}")
                    break
                else:
                    print(f"   No tweets found on {base_url}")
            
        except Exception as e:
            print(f"   Error with {base_url}: {str(e)[:50]}")
            continue
    
    return tweets


def parse_engagement(text: str) -> int:
    """Parse engagement numbers like '1.2K', '5M'"""
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


def get_top_tweets(queries: List[str], top_n: int = 10) -> List[Dict]:
    """Get top tweets for each query"""
    all_tweets = []
    
    for query in queries:
        print(f"\n🔍 Searching for '{query}'...")
        tweets = search_via_nitter(query)
        
        if tweets:
            # Sort by likes
            tweets.sort(key=lambda x: x.get('likes', 0), reverse=True)
            top_tweets = tweets[:top_n]
            all_tweets.extend(top_tweets)
            print(f"   Got {len(top_tweets)} top tweets")
        else:
            print(f"   ⚠️  No tweets found for '{query}'")
        
        time.sleep(2)  # Be nice to servers
    
    return all_tweets


class GoogleSheetsExporter:
    def __init__(self, credentials_path: str, spreadsheet_name: str = None):
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        try:
            creds = Credentials.from_service_account_file(credentials_path, scopes=scope)
            self.client = gspread.authorize(creds)
            
            if spreadsheet_name:
                try:
                    self.spreadsheet = self.client.open(spreadsheet_name)
                except gspread.exceptions.SpreadsheetNotFound:
                    self.spreadsheet = self.client.create(spreadsheet_name)
                    print(f"Created new spreadsheet: {spreadsheet_name}")
            else:
                self.spreadsheet = None
        except FileNotFoundError:
            print(f"⚠️  Google credentials not found at {credentials_path}")
            self.spreadsheet = None
    
    def export_tweets(self, tweets: List[Dict], sheet_name: str = "Tweets"):
        if not self.spreadsheet:
            raise ValueError("No spreadsheet available")
        
        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            worksheet.clear()
        except gspread.exceptions.WorksheetNotFound:
            worksheet = self.spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=1)
        
        headers = ['Link']
        rows = [headers]
        for tweet in tweets:
            tweet_url = tweet.get('url', '')
            if tweet_url:
                link_formula = f'=HYPERLINK("{tweet_url}", "{tweet_url}")'
                rows.append([link_formula])
        
        worksheet.update('A1', rows, value_input_option='USER_ENTERED')
        worksheet.format('A1', {
            'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9},
            'textFormat': {'bold': True, 'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}}
        })
        worksheet.columns_auto_resize(0, len(headers))
        
        print(f"✅ Exported {len(tweets)} tweet links to sheet '{sheet_name}'")
        print(f"📊 Spreadsheet URL: {self.spreadsheet.url}")


def main():
    print("=" * 60)
    print("Twitter Scraper - Clawbot & Moltbot")
    print("=" * 60)
    
    queries = ['Clawbot', 'moltbot']
    tweets = get_top_tweets(queries, top_n=10)
    
    if not tweets:
        print("\n" + "=" * 60)
        print("⚠️  Could not automatically scrape tweets.")
        print("\nTwitter/X has strong anti-scraping measures.")
        print("\nManual search URLs:")
        for query in queries:
            print(f"\n{query}:")
            print(f"  https://twitter.com/search?q={query}&src=typed_query&f=live")
            print(f"  https://nitter.net/search?f=tweets&q={query}")
        
        # Save to file
        with open('search_urls.txt', 'w') as f:
            for query in queries:
                f.write(f"{query}:\n")
                f.write(f"https://twitter.com/search?q={query}&src=typed_query&f=live\n")
                f.write(f"https://nitter.net/search?f=tweets&q={query}\n\n")
        print("\n✅ Search URLs saved to search_urls.txt")
        return
    
    # Export to Google Sheets or JSON
    GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
    SPREADSHEET_NAME = os.getenv('SPREADSHEET_NAME', 'Twitter Scraper - Clawbot & Moltbot')
    
    try:
        exporter = GoogleSheetsExporter(GOOGLE_CREDENTIALS_PATH, SPREADSHEET_NAME)
        exporter.export_tweets(tweets, sheet_name="Top Tweets")
        print(f"\n🎉 Successfully exported {len(tweets)} tweet links!")
    except Exception as e:
        print(f"\n⚠️  Could not export to Google Sheets: {e}")
        # Save to JSON
        output_file = 'tweets_output.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(tweets, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved {len(tweets)} tweet links to {output_file}")
        
        # Also create a simple text file with just links
        links_file = 'tweet_links.txt'
        with open(links_file, 'w') as f:
            for tweet in tweets:
                f.write(f"{tweet.get('url', '')}\n")
        print(f"✅ Saved links to {links_file}")


if __name__ == "__main__":
    main()


