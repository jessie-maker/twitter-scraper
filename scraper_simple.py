#!/usr/bin/env python3
"""
Simple Twitter Scraper using requests and alternative methods
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from typing import List, Dict
import gspread
from google.oauth2.service_account import Credentials
import os


def search_twitter_alternative(query: str, max_results: int = 50) -> List[Dict]:
    """
    Try alternative methods to get Twitter data
    """
    tweets = []
    
    # Method 1: Try using nitter.net (Twitter frontend)
    try:
        print(f"Trying nitter.net for '{query}'...")
        nitter_url = f"https://nitter.net/search?f=tweets&q={query}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(nitter_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            tweet_divs = soup.find_all('div', class_='tweet-content')
            for idx, div in enumerate(tweet_divs[:max_results]):
                try:
                    text = div.get_text(strip=True)
                    # Try to find author and link
                    tweet_elem = div.find_parent('div', class_='tweet')
                    if tweet_elem:
                        author_link = tweet_elem.find('a', class_='username')
                        if author_link:
                            author = author_link.get_text(strip=True).replace('@', '')
                            tweet_link = author_link.get('href', '')
                            if tweet_link and not tweet_link.startswith('http'):
                                tweet_link = f"https://nitter.net{tweet_link}"
                            
                            tweets.append({
                                'text': text,
                                'author': author,
                                'url': tweet_link,
                                'query': query,
                                'likes': 0  # Nitter doesn't always show likes
                            })
                except:
                    continue
            
            if tweets:
                print(f"Found {len(tweets)} tweets via nitter.net")
                return tweets
    except Exception as e:
        print(f"Nitter method failed: {e}")
    
    # Method 2: Try Twitter's public search (may require login)
    # This is a fallback - Twitter often blocks this
    return tweets


def get_top_tweets_by_manual_search():
    """
    Since automated scraping is difficult, provide manual search URLs
    and instructions
    """
    queries = ['Clawbot', 'moltbot']
    results = []
    
    for query in queries:
        print(f"\nSearching for '{query}'...")
        tweets = search_twitter_alternative(query, max_results=20)
        
        if not tweets:
            print(f"⚠️  Could not automatically scrape '{query}'")
            print(f"   Manual search URL: https://twitter.com/search?q={query}&src=typed_query&f=live")
            print(f"   Alternative: https://nitter.net/search?f=tweets&q={query}")
        else:
            results.extend(tweets)
    
    return results


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
            print(f"Google credentials not found at {credentials_path}")
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
        
        print(f"Exported {len(tweets)} tweet links to sheet '{sheet_name}'")
        print(f"Spreadsheet URL: {self.spreadsheet.url}")


def main():
    print("Twitter Scraper - Alternative Method")
    print("=" * 50)
    
    # Try to get tweets
    tweets = get_top_tweets_by_manual_search()
    
    if not tweets:
        print("\n" + "=" * 50)
        print("⚠️  Automated scraping failed due to Twitter's restrictions.")
        print("\nHere are manual search URLs you can use:")
        print("\nClawbot:")
        print("  https://twitter.com/search?q=Clawbot&src=typed_query&f=live")
        print("  https://nitter.net/search?f=tweets&q=Clawbot")
        print("\nmoltbot:")
        print("  https://twitter.com/search?q=moltbot&src=typed_query&f=live")
        print("  https://nitter.net/search?f=tweets&q=moltbot")
        print("\nYou can manually copy the top 10 liked tweet links from these pages.")
        
        # Save instructions to file
        with open('manual_instructions.txt', 'w') as f:
            f.write("Manual Twitter Search Instructions\n")
            f.write("=" * 50 + "\n\n")
            f.write("Clawbot search:\n")
            f.write("https://twitter.com/search?q=Clawbot&src=typed_query&f=live\n\n")
            f.write("moltbot search:\n")
            f.write("https://twitter.com/search?q=moltbot&src=typed_query&f=live\n\n")
            f.write("Alternative (nitter.net):\n")
            f.write("https://nitter.net/search?f=tweets&q=Clawbot\n")
            f.write("https://nitter.net/search?f=tweets&q=moltbot\n")
        
        print("\n✅ Instructions saved to manual_instructions.txt")
        return
    
    # Try to export to Google Sheets
    GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
    SPREADSHEET_NAME = os.getenv('SPREADSHEET_NAME', 'Twitter Scraper - Clawbot & Moltbot')
    
    try:
        exporter = GoogleSheetsExporter(GOOGLE_CREDENTIALS_PATH, SPREADSHEET_NAME)
        exporter.export_tweets(tweets, sheet_name="Top Tweets")
        print(f"\n✅ Successfully exported {len(tweets)} tweet links to Google Sheets!")
    except Exception as e:
        print(f"\n⚠️  Could not export to Google Sheets: {e}")
        # Save to JSON
        output_file = 'tweets_output.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(tweets, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved {len(tweets)} tweet links to {output_file}")


if __name__ == "__main__":
    main()


