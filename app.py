#!/usr/bin/env python3
"""
Twitter Scraper Backend API with Apify Integration
Scrapes real tweets using Apify's Tweet Scraper V2
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from apify_client import ApifyClient
import re
import json
import os
from typing import List, Dict

app = Flask(__name__, static_folder='.')
CORS(app)

# Apify configuration
APIFY_API_TOKEN = os.getenv('APIFY_API_TOKEN')
ACTOR_ID = "apidojo/tweet-scraper"


def get_apify_client():
    """Get Apify client, raise error if token not set"""
    if not APIFY_API_TOKEN:
        raise ValueError(
            "APIFY_API_TOKEN not set. Run: export APIFY_API_TOKEN='your_token'"
        )
    return ApifyClient(APIFY_API_TOKEN)


def extract_keyword(prompt: str) -> str:
    """Extract keyword from search prompt"""
    patterns = [
        r"keyword\s+['\"]?(\w+)['\"]?",
        r"about\s+['\"]?(\w+)['\"]?",
        r"with\s+keyword\s+['\"]?(\w+)['\"]?",
        r"posts\s+about\s+['\"]?(\w+)['\"]?",
    ]

    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            return match.group(1)

    words = prompt.split()
    if words:
        return words[-1].strip("'\".,!?")
    return ""


def extract_count(prompt: str) -> int:
    """Extract number of posts requested"""
    match = re.search(r'top\s+(\d+)', prompt, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 50


def analyze_tweet_content(text: str, keyword: str) -> Dict:
    """Analyze tweet to determine theme and generate summary"""
    text_lower = text.lower()

    # Use case indicators
    use_case_keywords = [
        'use', 'using', 'used', 'build', 'built', 'create', 'created',
        'automate', 'automated', 'help', 'helps', 'workflow', 'task',
        'integrate', 'integration', 'deploy', 'app', 'application',
        'tool', 'project', 'demo', 'example', 'tutorial', 'how to',
        'made', 'making', 'working', 'works'
    ]

    # Announcement indicators
    announcement_keywords = [
        'announcing', 'launched', 'introducing', 'new', 'release',
        'update', 'version', 'available', 'coming soon'
    ]

    # Opinion/discussion indicators
    opinion_keywords = [
        'think', 'believe', 'opinion', 'thoughts', 'amazing', 'awesome',
        'love', 'hate', 'best', 'worst', 'better', 'comparison'
    ]

    # Determine theme
    if any(kw in text_lower for kw in use_case_keywords):
        theme = 'Use Case'
    elif any(kw in text_lower for kw in announcement_keywords):
        theme = 'Announcement'
    elif any(kw in text_lower for kw in opinion_keywords):
        theme = 'Opinion'
    else:
        theme = 'Discussion'

    # Generate summary - get the most relevant sentence
    sentences = re.split(r'[.!?]+', text)
    summary = ""

    if theme == 'Use Case':
        # Find sentence mentioning the use case
        for sentence in sentences:
            if any(kw in sentence.lower() for kw in use_case_keywords):
                summary = sentence.strip()
                break
        if not summary and sentences:
            summary = sentences[0].strip()
    else:
        # Use first meaningful sentence
        for sentence in sentences:
            if len(sentence.strip()) > 20:
                summary = sentence.strip()
                break
        if not summary and sentences:
            summary = sentences[0].strip()

    # Truncate if too long
    if len(summary) > 200:
        summary = summary[:197] + '...'

    return {'theme': theme, 'summary': summary}


def scrape_twitter_apify(keyword: str, count: int = 50) -> List[Dict]:
    """
    Scrape Twitter using Apify's Tweet Scraper V2
    Returns real tweets with working links
    """
    try:
        client = get_apify_client()

        # Configure the scraper
        run_input = {
            "searchTerms": [keyword],
            "maxTweets": count,
            "sort": "Top",  # Get most popular tweets
            "tweetLanguage": "en",
        }

        print(f"Scraping Twitter via Apify for: {keyword}")

        # Run the actor
        run = client.actor(ACTOR_ID).call(run_input=run_input)

        # Process results
        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            # Extract author info
            author = item.get('author', {})
            author_name = author.get('userName', 'Unknown')
            author_display = author.get('name', author_name)

            # Get tweet URL
            tweet_url = item.get('url', '')
            if not tweet_url and item.get('id'):
                tweet_url = f"https://x.com/{author_name}/status/{item.get('id')}"

            # Analyze content
            text = item.get('text', '')
            analysis = analyze_tweet_content(text, keyword)

            results.append({
                'authorName': f"@{author_name}",
                'authorDisplayName': author_display,
                'authorUrl': f"https://x.com/{author_name}",
                'postUrl': tweet_url,
                'theme': analysis['theme'],
                'summary': analysis['summary'] if analysis['summary'] else text[:200],
                'likes': item.get('likeCount', 0),
                'retweets': item.get('retweetCount', 0),
                'replies': item.get('replyCount', 0),
                'views': item.get('viewCount', 0),
                'fullText': text
            })

        # Sort by likes (most popular first)
        results.sort(key=lambda x: x.get('likes', 0), reverse=True)

        print(f"Found {len(results)} tweets")
        return results[:count]

    except ValueError as e:
        # API token not set
        raise e
    except Exception as e:
        print(f"Apify scraping error: {e}")
        raise Exception(f"Failed to scrape Twitter: {str(e)}")


@app.route('/')
def index():
    return send_from_directory('.', 'twitter_scraper_app.html')


@app.route('/api/search', methods=['POST'])
def search():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        keyword = data.get('keyword', '') or extract_keyword(prompt)
        count = data.get('count', 50) or extract_count(prompt)

        if not keyword:
            return jsonify({
                'error': 'Could not extract keyword from prompt. Please include a keyword.'
            }), 400

        print(f"Searching for: {keyword}, count: {count}")

        # Check if Apify is configured
        if not APIFY_API_TOKEN:
            return jsonify({
                'error': 'APIFY_API_TOKEN not configured on server',
                'message': 'Set the environment variable: export APIFY_API_TOKEN="your_token"',
                'results': []
            }), 500

        # Scrape with Apify
        results = scrape_twitter_apify(keyword, count)

        if not results:
            return jsonify({
                'success': True,
                'results': [],
                'keyword': keyword,
                'count': 0,
                'message': f'No tweets found for "{keyword}"'
            })

        return jsonify({
            'success': True,
            'results': results,
            'keyword': keyword,
            'count': len(results)
        })

    except ValueError as e:
        return jsonify({
            'error': str(e),
            'results': []
        }), 500
    except Exception as e:
        return jsonify({
            'error': str(e),
            'results': []
        }), 500


@app.route('/api/status', methods=['GET'])
def status():
    """Check if API is configured"""
    return jsonify({
        'apify_configured': bool(APIFY_API_TOKEN),
        'message': 'Ready' if APIFY_API_TOKEN else 'APIFY_API_TOKEN not set'
    })


if __name__ == '__main__':
    if not APIFY_API_TOKEN:
        print("\n" + "="*60)
        print("WARNING: APIFY_API_TOKEN not set!")
        print("Run: export APIFY_API_TOKEN='your_token'")
        print("Get token: https://console.apify.com/account/integrations")
        print("="*60 + "\n")
    else:
        print("Apify API configured and ready!")

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
