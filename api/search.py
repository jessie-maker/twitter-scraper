"""
Vercel Serverless Function for Twitter Search
"""

from http.server import BaseHTTPRequestHandler
from apify_client import ApifyClient
import json
import os
import re

APIFY_API_TOKEN = os.getenv('APIFY_API_TOKEN')
ACTOR_ID = "apidojo/tweet-scraper"


def extract_keyword(prompt: str) -> str:
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
    match = re.search(r'top\s+(\d+)', prompt, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 50


def analyze_tweet_content(text: str, keyword: str) -> dict:
    text_lower = text.lower()
    use_case_keywords = [
        'use', 'using', 'used', 'build', 'built', 'create', 'created',
        'automate', 'automated', 'help', 'helps', 'workflow', 'task',
        'integrate', 'integration', 'deploy', 'app', 'application',
        'tool', 'project', 'demo', 'example', 'tutorial', 'how to',
        'made', 'making', 'working', 'works'
    ]
    announcement_keywords = [
        'announcing', 'launched', 'introducing', 'new', 'release',
        'update', 'version', 'available', 'coming soon'
    ]
    opinion_keywords = [
        'think', 'believe', 'opinion', 'thoughts', 'amazing', 'awesome',
        'love', 'hate', 'best', 'worst', 'better', 'comparison'
    ]

    if any(kw in text_lower for kw in use_case_keywords):
        theme = 'Use Case'
    elif any(kw in text_lower for kw in announcement_keywords):
        theme = 'Announcement'
    elif any(kw in text_lower for kw in opinion_keywords):
        theme = 'Opinion'
    else:
        theme = 'Discussion'

    sentences = re.split(r'[.!?]+', text)
    summary = ""
    if theme == 'Use Case':
        for sentence in sentences:
            if any(kw in sentence.lower() for kw in use_case_keywords):
                summary = sentence.strip()
                break
        if not summary and sentences:
            summary = sentences[0].strip()
    else:
        for sentence in sentences:
            if len(sentence.strip()) > 20:
                summary = sentence.strip()
                break
        if not summary and sentences:
            summary = sentences[0].strip()

    if len(summary) > 200:
        summary = summary[:197] + '...'

    return {'theme': theme, 'summary': summary}


def scrape_twitter_apify(keyword: str, count: int = 50) -> list:
    if not APIFY_API_TOKEN:
        raise ValueError("APIFY_API_TOKEN not configured")

    client = ApifyClient(APIFY_API_TOKEN)
    run_input = {
        "searchTerms": [keyword],
        "maxTweets": count,
        "sort": "Top",
        "tweetLanguage": "en",
    }

    run = client.actor(ACTOR_ID).call(run_input=run_input)

    results = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        author = item.get('author', {})
        author_name = author.get('userName', 'Unknown')
        author_display = author.get('name', author_name)
        tweet_url = item.get('url', '')
        if not tweet_url and item.get('id'):
            tweet_url = f"https://x.com/{author_name}/status/{item.get('id')}"

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

    results.sort(key=lambda x: x.get('likes', 0), reverse=True)
    return results[:count]


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body) if body else {}
            prompt = data.get('prompt', '')
            keyword = data.get('keyword', '') or extract_keyword(prompt)
            count = data.get('count', 50) or extract_count(prompt)

            if not keyword:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'Could not extract keyword from prompt'
                }).encode())
                return

            if not APIFY_API_TOKEN:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'APIFY_API_TOKEN not configured on server'
                }).encode())
                return

            results = scrape_twitter_apify(keyword, count)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'results': results,
                'keyword': keyword,
                'count': len(results)
            }).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': str(e)
            }).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
