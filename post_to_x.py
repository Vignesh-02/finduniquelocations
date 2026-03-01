"""
Daily X (Twitter) poster for BuenaVista.
Fetches a random location from OpenTripMap, generates an engaging tweet
using Claude AI, and posts it to X with a link to buenavista.in.
"""

import os
import json
import tempfile
import logging
from datetime import datetime

import requests
import tweepy
import anthropic

# --- PATH SETUP ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(SCRIPT_DIR, "DailyViews")
SAVE_DIR = os.path.join(BASE_DIR, "Locations")
LOG_FILE = os.path.join(BASE_DIR, "daily_locations.log")
POSTS_LOG = os.path.join(BASE_DIR, "posted_tweets.json")

os.makedirs(SAVE_DIR, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# --- CONFIG FROM ENV ---
OTM_API_KEY = os.environ.get("OTM_API_KEY")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
X_API_KEY = os.environ.get("X_API_KEY")
X_API_SECRET = os.environ.get("X_API_SECRET")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET")
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY")


def fetch_location():
    """Fetch a random breathtaking location from OpenTripMap."""
    if not OTM_API_KEY:
        logging.error("OTM_API_KEY missing!")
        return None

    params = {
        "lon_min": -180, "lat_min": -60,
        "lon_max": 180, "lat_max": 70,
        "kinds": "natural",
        "rate": "3",
        "limit": "100",
        "apikey": OTM_API_KEY,
    }

    try:
        resp = requests.get(
            "https://api.opentripmap.com/0.1/en/places/bbox",
            params=params, timeout=20,
        )
        if resp.status_code != 200:
            logging.error(f"OTM API Error {resp.status_code}: {resp.text}")
            return None

        import random
        features = resp.json().get("features", [])
        named = [f for f in features if f["properties"].get("name")]
        if not named:
            logging.warning("No named features found.")
            return None

        target = random.choice(named)
        xid = target["properties"]["xid"]
        details = requests.get(
            f"https://api.opentripmap.com/0.1/en/places/xid/{xid}",
            params={"apikey": OTM_API_KEY}, timeout=20,
        ).json()

        return {
            "name": details.get("name", "Hidden Wonder"),
            "description": details.get("wikipedia_extracts", {}).get(
                "text", "A spectacular natural location."
            ),
            "country": details.get("address", {}).get("country", "Unknown"),
            "otm_url": details.get("otm", "https://opentripmap.com"),
            "image_url": details.get("image"),  # Wikimedia Commons image
        }
    except Exception as e:
        logging.error(f"fetch_location error: {e}")
        return None


def save_location_file(data):
    """Save location as markdown (same format as daily_view.py)."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    clean_name = "".join(
        x for x in data["name"] if x.isalnum() or x in " -_"
    ).strip()
    filename = f"{date_str}_{clean_name.replace(' ', '_')}.md"
    filepath = os.path.join(SAVE_DIR, filename)

    content = (
        f"# 🌍 Daily Discovery: {data['name']}\n"
        f"**Country:** {data['country']}\n\n"
        f"{data['description']}\n\n"
        f"[OpenTripMap]({data['otm_url']})"
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    logging.info(f"Saved location file: {filepath}")
    return filepath


def fetch_image(location_data):
    """Download a photo for the location. Tries OpenTripMap image first, then Unsplash."""
    image_path = os.path.join(tempfile.gettempdir(), "buenavista_daily.jpg")

    # 1. Try the Wikimedia Commons image from OpenTripMap
    wiki_url = location_data.get("image_url")
    if wiki_url:
        try:
            resp = requests.get(wiki_url, timeout=15, headers={"User-Agent": "BuenaVistaBot/1.0"})
            if resp.status_code == 200 and len(resp.content) > 5000:
                with open(image_path, "wb") as f:
                    f.write(resp.content)
                logging.info(f"Image from Wikimedia: {wiki_url}")
                return image_path
        except Exception as e:
            logging.warning(f"Wikimedia image failed: {e}")

    # 2. Fallback to Unsplash
    if UNSPLASH_ACCESS_KEY:
        try:
            search_query = f"{location_data['name']} {location_data['country']} nature landscape"
            resp = requests.get(
                "https://api.unsplash.com/search/photos",
                params={"query": search_query, "per_page": 1, "orientation": "landscape"},
                headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
                timeout=15,
            )
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    img_url = results[0]["urls"]["regular"]  # 1080px wide
                    img_resp = requests.get(img_url, timeout=15)
                    if img_resp.status_code == 200:
                        with open(image_path, "wb") as f:
                            f.write(img_resp.content)
                        logging.info(f"Image from Unsplash: {img_url}")
                        return image_path
        except Exception as e:
            logging.warning(f"Unsplash image failed: {e}")

    logging.warning("No image found for this location.")
    return None


def generate_tweet(location_data):
    """Use Claude to generate an engaging tweet about the location."""
    if not CLAUDE_API_KEY:
        logging.error("CLAUDE_API_KEY missing!")
        return None

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    prompt = f"""Write a single tweet about this place. STRICT LIMIT: 240 characters max.
Do NOT write in first person. Do NOT say "I visited" or "I went" or "Just returned".
Present it as a recommendation — tell people why they should check this place out.
Highlight what makes it unique using the description.
Include 1-2 relevant emojis naturally.
End with: Explore more at buenavista.in
Do NOT use hashtags. Do NOT use quotes. Just the tweet text.

Place: {location_data['name']}
Country: {location_data['country']}
Description: {location_data['description'][:500]}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}],
    )

    tweet_text = message.content[0].text.strip()

    # Ensure it fits in 280 chars while preserving the CTA
    if len(tweet_text) > 280:
        cta = "Explore more at buenavista.in"
        max_body = 280 - len(cta) - 4  # 4 for "... "
        tweet_text = tweet_text[:max_body].rsplit(" ", 1)[0] + "... " + cta

    logging.info(f"Generated tweet ({len(tweet_text)} chars): {tweet_text}")
    return tweet_text


def post_to_x(tweet_text, image_path=None):
    """Post the tweet to X with an optional image."""
    if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]):
        logging.error("X API credentials missing!")
        return None

    # v2 client for creating tweets
    client = tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )

    try:
        media_ids = None

        # Upload image using v1.1 API (required for media upload)
        if image_path and os.path.exists(image_path):
            try:
                auth = tweepy.OAuth1UserHandler(
                    X_API_KEY, X_API_SECRET,
                    X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET,
                )
                api_v1 = tweepy.API(auth)
                media = api_v1.media_upload(filename=image_path)
                media_ids = [media.media_id]
                logging.info(f"Uploaded image, media_id: {media.media_id}")
            except Exception as img_err:
                logging.warning(f"Image upload failed, posting without image: {img_err}")

        response = client.create_tweet(text=tweet_text, media_ids=media_ids)
        tweet_id = response.data["id"]
        logging.info(f"Posted to X! Tweet ID: {tweet_id}")
        return tweet_id
    except Exception as e:
        logging.error(f"Failed to post to X: {e}")
        print(f"X API Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"X API response: {e.response.text}")
            print(f"X API Response: {e.response.text[:500]}")
        return None


def log_posted_tweet(location_data, tweet_text, tweet_id):
    """Keep a log of all posted tweets."""
    entry = {
        "date": datetime.now().isoformat(),
        "location": location_data["name"],
        "country": location_data["country"],
        "tweet": tweet_text,
        "tweet_id": tweet_id,
    }

    posts = []
    if os.path.exists(POSTS_LOG):
        with open(POSTS_LOG, "r") as f:
            posts = json.load(f)

    posts.append(entry)

    with open(POSTS_LOG, "w") as f:
        json.dump(posts, f, indent=2)


if __name__ == "__main__":
    print("🌍 BuenaVista Daily Post")

    # Step 1: Fetch location
    location = fetch_location()
    if not location:
        print("Failed to fetch location. Check daily_locations.log")
        exit(1)

    print(f"📍 Location: {location['name']} ({location['country']})")

    # Step 2: Save markdown file
    filepath = save_location_file(location)
    print(f"📄 Saved: {filepath}")

    # Step 3: Generate tweet with AI
    tweet = generate_tweet(location)
    if not tweet:
        print("Failed to generate tweet. Check daily_locations.log")
        exit(1)

    print(f"🐦 Tweet: {tweet}")

    # Step 4: Fetch image
    image_path = fetch_image(location)
    if image_path:
        print(f"🖼️  Image: {image_path}")
    else:
        print("⚠️  No image found, posting without image.")

    # Step 5: Post to X
    tweet_id = post_to_x(tweet, image_path)
    if not tweet_id:
        print("Failed to post to X. Check daily_locations.log")
        exit(1)

    # Step 6: Log it
    log_posted_tweet(location, tweet, tweet_id)
    print(f"✅ Posted! Tweet ID: {tweet_id}")
