from flask import Flask, request, jsonify
import json
import os
import re

app = Flask(__name__)

# Check if apify_client is available
try:
    from apify_client import ApifyClient
    APIFY_AVAILABLE = True
except ImportError:
    APIFY_AVAILABLE = False

APIFY_API_TOKEN = os.getenv('APIFY_API_TOKEN')
ACTOR_ID = "apidojo/tweet-scraper"


def extract_keyword(prompt):
    patterns = [
        r"keyword\s+['\"]?(\w+)['\"]?",
        r"about\s+['\"]?(\w+)['\"]?",
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            return match.group(1)
    words = prompt.split()
    return words[-1].strip("'\".,!?") if words else ""


def analyze_tweet(text):
    text_lower = text.lower()
    use_case_kw = ['use', 'using', 'build', 'create', 'automate', 'help', 'workflow', 'tool', 'app', 'made']
    theme = 'Use Case' if any(kw in text_lower for kw in use_case_kw) else 'Discussion'
    sentences = re.split(r'[.!?]+', text)
    summary = sentences[0].strip()[:200] if sentences else text[:200]
    return {'theme': theme, 'summary': summary}


def scrape_twitter(keyword, count=50):
    if not APIFY_AVAILABLE or not APIFY_API_TOKEN:
        raise ValueError("Apify not configured")

    client = ApifyClient(APIFY_API_TOKEN)
    run = client.actor(ACTOR_ID).call(run_input={
        "searchTerms": [keyword],
        "maxTweets": count,
        "sort": "Top",
    })

    results = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        author = item.get('author', {})
        author_name = author.get('userName', 'Unknown')
        text = item.get('text', '')
        analysis = analyze_tweet(text)

        results.append({
            'authorName': f"@{author_name}",
            'authorUrl': f"https://x.com/{author_name}",
            'postUrl': item.get('url', f"https://x.com/{author_name}/status/{item.get('id', '')}"),
            'theme': analysis['theme'],
            'summary': analysis['summary'],
            'likes': item.get('likeCount', 0),
        })

    results.sort(key=lambda x: x.get('likes', 0), reverse=True)
    return results[:count]


@app.route('/api/search', methods=['POST', 'OPTIONS'])
def search():
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    try:
        data = request.get_json() or {}
        keyword = data.get('keyword') or extract_keyword(data.get('prompt', ''))
        count = data.get('count', 50)

        if not keyword:
            return jsonify({'error': 'No keyword provided'}), 400

        if not APIFY_API_TOKEN:
            return jsonify({'error': 'APIFY_API_TOKEN not configured'}), 500

        results = scrape_twitter(keyword, count)
        response = jsonify({'success': True, 'results': results, 'keyword': keyword})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    except Exception as e:
        response = jsonify({'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 500


# Vercel handler
def handler(environ, start_response):
    return app(environ, start_response)
