from flask import Flask, request, jsonify
import requests
import os
import re
import time

app = Flask(__name__)

APIFY_API_TOKEN = os.getenv('APIFY_API_TOKEN')
ACTOR_ID = "apidojo~tweet-scraper"


def extract_keyword(prompt):
    patterns = [r"keyword\s+['\"]?(\w+)['\"]?", r"about\s+['\"]?(\w+)['\"]?"]
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


def scrape_twitter_direct(keyword, count=50):
    """Use Apify REST API directly instead of library"""
    if not APIFY_API_TOKEN:
        raise ValueError("APIFY_API_TOKEN not configured")

    # Start the actor run
    start_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={APIFY_API_TOKEN}"
    run_input = {
        "searchTerms": [keyword],
        "maxTweets": count,
        "sort": "Top",
    }

    response = requests.post(start_url, json=run_input, timeout=30)
    if response.status_code != 201:
        raise ValueError(f"Failed to start actor: {response.text}")

    run_data = response.json()
    run_id = run_data['data']['id']
    dataset_id = run_data['data']['defaultDatasetId']

    # Wait for the run to finish (poll status)
    status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_API_TOKEN}"
    for _ in range(60):  # Wait up to 5 minutes
        time.sleep(5)
        status_response = requests.get(status_url, timeout=30)
        status_data = status_response.json()
        status = status_data['data']['status']
        if status == 'SUCCEEDED':
            break
        elif status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
            raise ValueError(f"Actor run failed: {status}")

    # Get results from dataset
    items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_API_TOKEN}"
    items_response = requests.get(items_url, timeout=30)
    items = items_response.json()

    results = []
    for item in items:
        # Skip invalid items
        author = item.get('author', {})
        author_name = author.get('userName') or author.get('username') or item.get('username')
        if not author_name:
            continue

        text = item.get('text') or item.get('full_text') or ''
        if not text:
            continue

        analysis = analyze_tweet(text)
        tweet_url = item.get('url') or item.get('tweet_url')
        if not tweet_url:
            tweet_id = item.get('id') or item.get('id_str')
            tweet_url = f"https://x.com/{author_name}/status/{tweet_id}" if tweet_id else ''

        results.append({
            'authorName': f"@{author_name}",
            'authorUrl': f"https://x.com/{author_name}",
            'postUrl': tweet_url,
            'theme': analysis['theme'],
            'summary': analysis['summary'],
            'likes': item.get('likeCount') or item.get('favorite_count') or 0,
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
        count = min(data.get('count', 20), 50)  # Limit to 50

        if not keyword:
            return jsonify({'error': 'No keyword provided'}), 400

        if not APIFY_API_TOKEN:
            return jsonify({'error': 'APIFY_API_TOKEN not configured'}), 500

        results = scrape_twitter_direct(keyword, count)
        response = jsonify({'success': True, 'results': results, 'keyword': keyword})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    except Exception as e:
        response = jsonify({'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 500


@app.route('/api/search', methods=['GET'])
def health():
    response = jsonify({'status': 'ok', 'configured': bool(APIFY_API_TOKEN)})
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response
