from flask import Flask, request, jsonify
import requests
import os
import re
import time

app = Flask(__name__)

APIFY_API_TOKEN = os.getenv('APIFY_API_TOKEN')
ACTOR_ID = "apidojo~tweet-scraper"


def parse_natural_language(user_input):
    """
    Convert natural language search to Twitter search syntax.

    Examples:
    - "give me top 50 posts about OpenClaw" -> "OpenClaw"
    - "search for OpenClaw with at least 100 likes" -> "OpenClaw min_faves:100"
    - "find tweets from elonmusk about AI" -> "AI from:elonmusk"
    - "OpenClaw excluding spam" -> "OpenClaw -spam"
    """
    query_parts = []
    original = user_input.strip()

    # If it already looks like Twitter search syntax, use as-is
    if re.search(r'(min_faves:|from:|since:|until:|-\w)', original):
        return original, extract_count(original)

    # Extract keyword/topic
    keyword_patterns = [
        r'(?:keyword|topic|about|for|find|search|get)\s*[:\s]+["\']?([^"\',.]+)["\']?',
        r'(?:posts?|tweets?)\s+(?:about|on|for)\s+["\']?([^"\',.]+)["\']?',
        r'["\']([^"\']+)["\']',  # Quoted phrases
    ]

    keyword = None
    for pattern in keyword_patterns:
        match = re.search(pattern, original, re.IGNORECASE)
        if match:
            keyword = match.group(1).strip()
            break

    # If no keyword found via patterns, try to extract the main topic
    if not keyword:
        # Remove common filler words and extract what's left
        cleaned = re.sub(r'\b(give|me|the|top|get|find|search|show|liked|popular|twitter|posts?|tweets?|with|from|about|please|can|you|i|want)\b', '', original, flags=re.IGNORECASE)
        cleaned = re.sub(r'\d+', '', cleaned)  # Remove numbers
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        if cleaned:
            # Take the most significant remaining word(s)
            words = cleaned.split()
            keyword = ' '.join(w for w in words if len(w) > 2)[:50]

    if keyword:
        query_parts.append(keyword)

    # Extract minimum likes/faves
    likes_patterns = [
        r'(?:at\s+least|minimum|min|more\s+than|over|>\s*)\s*(\d+)\s*(?:likes?|faves?|favorites?)',
        r'(\d+)\+?\s*(?:likes?|faves?)',
        r'min_faves:\s*(\d+)',
    ]
    for pattern in likes_patterns:
        match = re.search(pattern, original, re.IGNORECASE)
        if match:
            query_parts.append(f"min_faves:{match.group(1)}")
            break

    # Extract "from" user
    from_patterns = [
        r'from\s*[:\s]+@?(\w+)',
        r'by\s+@?(\w+)',
        r'from:@?(\w+)',
    ]
    for pattern in from_patterns:
        match = re.search(pattern, original, re.IGNORECASE)
        if match:
            query_parts.append(f"from:{match.group(1)}")
            break

    # Extract exclusions
    exclude_patterns = [
        r'(?:excluding?|without|no|remove|-)\s*[:\s]*["\']?(\w+)["\']?',
        r'-(\w+)',
    ]
    for pattern in exclude_patterns:
        matches = re.findall(pattern, original, re.IGNORECASE)
        for match in matches:
            if match.lower() not in ['spam', 'bot', 'bots']:
                continue  # Only exclude common spam words
            query_parts.append(f"-{match}")

    # Extract date filters
    date_patterns = [
        r'since\s*[:\s]+(\d{4}-\d{2}-\d{2})',
        r'after\s+(\d{4}-\d{2}-\d{2})',
        r'since:(\d{4}-\d{2}-\d{2})',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, original, re.IGNORECASE)
        if match:
            query_parts.append(f"since:{match.group(1)}")
            break

    # Build final query
    final_query = ' '.join(query_parts) if query_parts else original
    count = extract_count(original)

    return final_query, count


def extract_count(text):
    """Extract desired number of results from text"""
    patterns = [
        r'top\s+(\d+)',
        r'(\d+)\s+(?:posts?|tweets?|results?)',
        r'(?:get|show|find)\s+(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return min(int(match.group(1)), 50)
    return 20  # Default


def analyze_tweet(text):
    text_lower = text.lower()
    use_case_kw = ['use', 'using', 'build', 'create', 'automate', 'help', 'workflow', 'tool', 'app', 'made', 'built', 'demo', 'example', 'tutorial']
    theme = 'Use Case' if any(kw in text_lower for kw in use_case_kw) else 'Discussion'
    sentences = re.split(r'[.!?]+', text)
    summary = sentences[0].strip()[:200] if sentences else text[:200]
    return {'theme': theme, 'summary': summary}


def scrape_twitter_direct(search_query, count=50):
    """Use Apify REST API directly"""
    if not APIFY_API_TOKEN:
        raise ValueError("APIFY_API_TOKEN not configured")

    start_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={APIFY_API_TOKEN}"
    run_input = {
        "searchTerms": [search_query],
        "maxTweets": count,
        "sort": "Top",
    }

    response = requests.post(start_url, json=run_input, timeout=30)
    if response.status_code != 201:
        raise ValueError(f"Failed to start actor: {response.text}")

    run_data = response.json()
    run_id = run_data['data']['id']
    dataset_id = run_data['data']['defaultDatasetId']

    # Wait for completion
    status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_API_TOKEN}"
    for _ in range(60):
        time.sleep(5)
        status_response = requests.get(status_url, timeout=30)
        status_data = status_response.json()
        status = status_data['data']['status']
        if status == 'SUCCEEDED':
            break
        elif status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
            raise ValueError(f"Actor run failed: {status}")

    # Get results
    items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_API_TOKEN}"
    items_response = requests.get(items_url, timeout=30)
    items = items_response.json()

    results = []
    for item in items:
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
        user_input = data.get('query') or data.get('keyword') or data.get('prompt', '')
        user_input = user_input.strip()

        if not user_input:
            return jsonify({'error': 'No search query provided'}), 400

        if not APIFY_API_TOKEN:
            return jsonify({'error': 'APIFY_API_TOKEN not configured'}), 500

        # Parse natural language to Twitter search syntax
        twitter_query, count = parse_natural_language(user_input)

        # Override count if provided in request
        if data.get('count'):
            count = min(data.get('count'), 50)

        results = scrape_twitter_direct(twitter_query, count)

        response = jsonify({
            'success': True,
            'results': results,
            'query': twitter_query,
            'originalInput': user_input,
            'count': len(results)
        })
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
