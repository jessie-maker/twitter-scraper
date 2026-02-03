#!/usr/bin/env python3
"""
Twitter Scraper using Apify's Tweet Scraper V2
Much more reliable than Selenium-based scraping
"""

import os
import json
import time
from typing import List, Dict, Optional
from apify_client import ApifyClient
import gspread
from google.oauth2.service_account import Credentials


class ApifyTwitterScraper:
    """Twitter scraper using Apify's Tweet Scraper V2 actor"""

    ACTOR_ID = "apidojo/tweet-scraper"

    def __init__(self, api_token: str = None):
        """
        Initialize with Apify API token
        Get your token from: https://console.apify.com/account/integrations
        """
        self.api_token = api_token or os.getenv('APIFY_API_TOKEN')
        if not self.api_token:
            raise ValueError(
                "Apify API token required. Set APIFY_API_TOKEN environment variable "
                "or pass api_token parameter.\n"
                "Get your token from: https://console.apify.com/account/integrations"
            )
        self.client = ApifyClient(self.api_token)

    def search_tweets(
        self,
        search_terms: List[str] = None,
        urls: List[str] = None,
        handles: List[str] = None,
        max_tweets: int = 100,
        sort_by: str = "Top",
        include_replies: bool = False
    ) -> List[Dict]:
        """
        Search for tweets using Apify's Tweet Scraper

        Args:
            search_terms: List of search queries (e.g., ["Clawbot", "moltbot"])
            urls: List of Twitter URLs to scrape
            handles: List of Twitter handles to scrape (without @)
            max_tweets: Maximum number of tweets to retrieve
            sort_by: "Top" or "Latest"
            include_replies: Whether to include replies

        Returns:
            List of tweet data dictionaries
        """
        # Build input configuration
        run_input = {
            "maxTweets": max_tweets,
            "sort": sort_by,
            "tweetLanguage": "en",
        }

        # Add search terms
        if search_terms:
            run_input["searchTerms"] = search_terms

        # Add start URLs
        if urls:
            run_input["startUrls"] = [{"url": url} for url in urls]

        # Add Twitter handles
        if handles:
            run_input["twitterHandles"] = handles

        # Add replies handling
        if include_replies:
            run_input["includeReplies"] = True

        print(f"Starting Apify Tweet Scraper with config:")
        print(f"  Search terms: {search_terms}")
        print(f"  URLs: {urls}")
        print(f"  Handles: {handles}")
        print(f"  Max tweets: {max_tweets}")

        # Run the actor
        run = self.client.actor(self.ACTOR_ID).call(run_input=run_input)

        # Fetch results from the dataset
        tweets = []
        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            tweets.append(self._normalize_tweet(item))

        print(f"Retrieved {len(tweets)} tweets")
        return tweets

    def _normalize_tweet(self, item: Dict) -> Dict:
        """Normalize Apify tweet data to match existing format"""
        return {
            'text': item.get('text', ''),
            'author': item.get('author', {}).get('userName', 'Unknown'),
            'author_name': item.get('author', {}).get('name', ''),
            'author_url': f"https://twitter.com/{item.get('author', {}).get('userName', '')}",
            'likes': item.get('likeCount', 0),
            'retweets': item.get('retweetCount', 0),
            'replies': item.get('replyCount', 0),
            'views': item.get('viewCount', 0),
            'url': item.get('url', ''),
            'created_at': item.get('createdAt', ''),
            'id': item.get('id', ''),
            'is_reply': item.get('isReply', False),
            'is_retweet': item.get('isRetweet', False),
            'media': item.get('media', []),
            'hashtags': item.get('hashtags', []),
        }

    def get_top_tweets_by_likes(self, tweets: List[Dict], top_n: int = 10) -> List[Dict]:
        """Sort tweets by likes and return top N"""
        sorted_tweets = sorted(tweets, key=lambda x: x.get('likes', 0), reverse=True)
        return sorted_tweets[:top_n]


class GoogleSheetsExporter:
    """Export tweets to Google Sheets"""

    def __init__(self, credentials_path: str, spreadsheet_name: str = None):
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
                self.spreadsheet = self.client.create(spreadsheet_name)
                print(f"Created new spreadsheet: {spreadsheet_name}")
        else:
            self.spreadsheet = None

    def export_tweets(self, tweets: List[Dict], sheet_name: str = "Tweets"):
        """Export tweets to Google Sheets with clickable links"""
        if not self.spreadsheet:
            raise ValueError("No spreadsheet specified")

        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            worksheet.clear()
        except gspread.exceptions.WorksheetNotFound:
            worksheet = self.spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=5)

        # Headers
        headers = ['Link', 'Author', 'Likes', 'Retweets', 'Text Preview']

        rows = [headers]
        for tweet in tweets:
            tweet_url = tweet.get('url', '')
            if tweet_url:
                link_formula = f'=HYPERLINK("{tweet_url}", "View Tweet")'
                author = f"@{tweet.get('author', 'Unknown')}"
                likes = tweet.get('likes', 0)
                retweets = tweet.get('retweets', 0)
                text_preview = tweet.get('text', '')[:100] + '...' if len(tweet.get('text', '')) > 100 else tweet.get('text', '')
                rows.append([link_formula, author, likes, retweets, text_preview])

        worksheet.update('A1', rows, value_input_option='USER_ENTERED')

        # Format header row
        worksheet.format('A1:E1', {
            'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9},
            'textFormat': {'bold': True, 'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}}
        })

        print(f"Exported {len(tweets)} tweets to sheet '{sheet_name}'")
        print(f"Spreadsheet URL: {self.spreadsheet.url}")


def main():
    """Main function to scrape tweets and export"""

    # Configuration
    APIFY_API_TOKEN = os.getenv('APIFY_API_TOKEN')
    GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
    SPREADSHEET_NAME = os.getenv('SPREADSHEET_NAME', 'Twitter Scraper - Clawbot & Moltbot')

    if not APIFY_API_TOKEN:
        print("ERROR: APIFY_API_TOKEN environment variable not set")
        print("\nTo set it, run:")
        print("  export APIFY_API_TOKEN='your_token_here'")
        print("\nGet your token from: https://console.apify.com/account/integrations")
        return

    # Search configuration
    search_terms = ['Clawbot', 'moltbot']

    print("Starting Twitter scraper with Apify API...")

    try:
        scraper = ApifyTwitterScraper(api_token=APIFY_API_TOKEN)

        # Search for tweets
        all_tweets = scraper.search_tweets(
            search_terms=search_terms,
            max_tweets=50,  # Get more than needed, then filter top ones
            sort_by="Top"
        )

        if not all_tweets:
            print("No tweets found.")
            return

        # Get top tweets by likes
        top_tweets = scraper.get_top_tweets_by_likes(all_tweets, top_n=20)

        print(f"\nFound {len(top_tweets)} top tweets")
        if top_tweets:
            print(f"Top tweet has {top_tweets[0].get('likes', 0)} likes")

        # Export to Google Sheets or JSON
        try:
            exporter = GoogleSheetsExporter(GOOGLE_CREDENTIALS_PATH, SPREADSHEET_NAME)
            exporter.export_tweets(top_tweets, sheet_name="Top Tweets")
            print(f"\nSuccessfully exported to Google Sheets!")
        except FileNotFoundError:
            print(f"\nGoogle credentials not found. Saving to JSON...")
            save_to_json(top_tweets)
        except Exception as e:
            print(f"\nError with Google Sheets: {str(e)}")
            save_to_json(top_tweets)

    except Exception as e:
        print(f"Error: {str(e)}")
        raise


def save_to_json(tweets: List[Dict], filename: str = 'tweets_output.json'):
    """Save tweets to JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(tweets, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(tweets)} tweets to {filename}")

    # Also print the URLs for easy access
    print("\nTweet URLs:")
    for i, tweet in enumerate(tweets, 1):
        url = tweet.get('url', 'No URL')
        likes = tweet.get('likes', 0)
        print(f"  {i}. {url} ({likes} likes)")


if __name__ == "__main__":
    main()
