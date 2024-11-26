from flask import Flask, render_template, request, jsonify
import tweepy
import requests
import re
import difflib
import time

# Flaskアプリケーションの初期化
app = Flask(__name__)

# Twitter APIの認証情報
api_key = "YgR5cbRclIFSI7q6A77RvsjIj"
api_secret = "IJ845WQDbbWKR4Hsis66BvG1W7R6b6X3TBwfGQFiDFv10uzDZJ"
access_token = "72551941-mdtnuHbUQrbrsV3d5jeiHKXRkB8RwKgHGYGTnznl1"
access_token_secret = "c95LRscnVMzmT6lR2iK9RYiciLypwHjl5OYxekg47EG5k"
bearer_token = "AAAAAAAAAAAAAAAAAAAAAPRLNAEAAAAAQbfilja%2FufYbuzYBUkzkgAqlW0g%3DzYezAiDEtdLCvkBucScCDJcc2qtTOmUGk3s69XxlvhhLjAbrQq"

# 認証を設定
auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
api = tweepy.API(auth)

# 絵文字判定用正規表現
EMOJI_PATTERN = re.compile(
    "[\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags (iOS)
    "\U00002702-\U000027B0"  # Dingbats
    "\U000024C2-\U0001F251"  # Enclosed characters
    "]+", flags=re.UNICODE
)

# 絵文字のみのリプライ判定
def is_emoji_only(text):
    return bool(EMOJI_PATTERN.fullmatch(text.strip()))

# リンクのみのリプライ判定
LINK_PATTERN = re.compile(r'http\S+')
def is_link_only(text):
    return bool(LINK_PATTERN.fullmatch(text.strip()))

# コピペ判定用関数
def is_copy_paste(reply_text, previous_replies, threshold=0.8):
    for past_reply in previous_replies:
        similarity = difflib.SequenceMatcher(None, reply_text, past_reply).ratio()
        if similarity >= threshold:
            return True
    return False

# 特定のツイートを取得する関数
def fetch_tweet(tweet_id):
    url = f"https://api.twitter.com/2/tweets/{tweet_id}"
    headers = {"Authorization": f"Bearer {bearer_token}"}
    params = {"tweet.fields": "text,author_id"}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get('data', None)
    else:
        return None

# リプライを収集する関数
def fetch_replies(tweet_id):
    replies = []
    headers = {"Authorization": f"Bearer {bearer_token}"}
    replies_url = f"https://api.twitter.com/2/tweets/search/recent?query=conversation_id:{tweet_id}&tweet.fields=author_id,text&max_results=50"

    while True:
        response = requests.get(replies_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            replies.extend(data.get("data", []))

            if "next_token" in data.get("meta", {}):
                next_token = data["meta"]["next_token"]
                replies_url = f"https://api.twitter.com/2/tweets/search/recent?query=conversation_id:{tweet_id}&tweet.fields=author_id,text&max_results=50&pagination_token={next_token}"
                time.sleep(1)  # 短い待機
            else:
                break
        else:
            break

    return replies

# Flaskルート: ホームページ
@app.route('/')
def index():
    return '''
    <h1>Twitterリプライ解析ツール</h1>
    <form action="/analyze" method="post">
        <label for="tweet_id">ツイートIDを入力してください:</label>
        <input type="text" id="tweet_id" name="tweet_id" required>
        <button type="submit">解析開始</button>
    </form>
    '''

# Flaskルート: リプライ解析
@app.route('/analyze', methods=['POST'])
def analyze():
    tweet_id = request.form['tweet_id']
    tweet_data = fetch_tweet(tweet_id)
    if not tweet_data:
        return "ツイートが見つかりませんでした。IDを確認してください。"

    replies = fetch_replies(tweet_id)

    user_points = {}
    previous_replies = []
    for reply in replies:
        user = reply['author_id']
        text = reply['text']

        def add_points(user, points):
            user_points[user] = user_points.get(user, 0) + points

        if is_emoji_only(text):
            add_points(user, 1)
        elif is_link_only(text):
            add_points(user, 1)
        elif is_copy_paste(text, previous_replies):
            add_points(user, 1)
        previous_replies.append(text)

    return jsonify(user_points=user_points, total_replies=len(replies))

# Flaskアプリケーションを起動
if __name__ == '__main__':
    app.run(debug=True)
