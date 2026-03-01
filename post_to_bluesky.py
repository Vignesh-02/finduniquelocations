"""
Daily Bluesky poster for BuenaVista.
Fetches a random location from OpenTripMap, generates an engaging post
using Claude AI, and posts it to Bluesky with a link to buenavista.in.
"""

import os
import json
import tempfile
import logging
from datetime import datetime, timezone

import requests
import anthropic

# --- PATH SETUP ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(SCRIPT_DIR, "DailyViews")
SAVE_DIR = os.path.join(BASE_DIR, "Locations")
LOG_FILE = os.path.join(BASE_DIR, "daily_locations.log")
POSTS_LOG = os.path.join(BASE_DIR, "posted_bluesky.json")

os.makedirs(SAVE_DIR, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# --- CONFIG FROM ENV ---
OTM_API_KEY = os.environ.get("OTM_API_KEY")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
BLUESKY_HANDLE = os.environ.get("BLUESKY_HANDLE")
BLUESKY_APP_PASSWORD = os.environ.get("BLUESKY_APP_PASSWORD")
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY")

ATP_BASE = "https://bsky.social/xrpc"


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
        "limit": "500",
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

        random.shuffle(named)
        for target in named:
            xid = target["properties"]["xid"]
            details = requests.get(
                f"https://api.opentripmap.com/0.1/en/places/xid/{xid}",
                params={"apikey": OTM_API_KEY}, timeout=20,
            ).json()

            if details.get("image"):
                logging.info(f"Found location with image: {details.get('name')} (tried {named.index(target) + 1} locations)")
                return {
                    "name": details.get("name", "Hidden Wonder"),
                    "description": details.get("wikipedia_extracts", {}).get(
                        "text", "A spectacular natural location."
                    ),
                    "country": details.get("address", {}).get("country", "Unknown"),
                    "otm_url": details.get("otm", "https://opentripmap.com"),
                    "image_url": details.get("image"),
                }

        logging.warning("No locations with images found in 500 results.")
        return None
    except Exception as e:
        logging.error(f"fetch_location error: {e}")
        return None


def save_location_file(data):
    """Save location as markdown."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    clean_name = "".join(
        x for x in data["name"] if x.isalnum() or x in " -_"
    ).strip()
    filename = f"{date_str}_{clean_name.replace(' ', '_')}.md"
    filepath = os.path.join(SAVE_DIR, filename)

    content = (
        f"# Daily Discovery: {data['name']}\n"
        f"**Country:** {data['country']}\n\n"
        f"{data['description']}\n\n"
        f"[OpenTripMap]({data['otm_url']})"
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    logging.info(f"Saved location file: {filepath}")
    return filepath


def fetch_image(location_data):
    """Download a photo for the location."""

    wiki_url = location_data.get("image_url")
    if wiki_url:
        try:
            # Resolve Wikimedia wiki page URLs to actual image URLs
            real_url = wiki_url
            if "commons.wikimedia.org/wiki/File:" in wiki_url:
                filename = wiki_url.split("File:")[-1]
                api_resp = requests.get(
                    "https://commons.wikimedia.org/w/api.php",
                    params={
                        "action": "query", "titles": f"File:{filename}",
                        "prop": "imageinfo", "iiprop": "url",
                        "iiurlwidth": 1080, "format": "json",
                    },
                    headers={"User-Agent": "BuenaVistaBot/1.0 (https://buenavista.in)"},
                    timeout=15,
                )
                if api_resp.status_code == 200:
                    pages = api_resp.json().get("query", {}).get("pages", {})
                    for page in pages.values():
                        info = page.get("imageinfo", [{}])[0]
                        real_url = info.get("thumburl") or info.get("url") or wiki_url

            resp = requests.get(real_url, timeout=15, headers={"User-Agent": "BuenaVistaBot/1.0"})
            content_type = resp.headers.get("content-type", "")
            if resp.status_code == 200 and len(resp.content) > 5000 and "image" in content_type:
                ext = os.path.splitext(real_url.split("?")[0])[-1].lower()
                if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                    ext = ".jpg"
                image_path = os.path.join(tempfile.gettempdir(), f"buenavista_daily{ext}")
                with open(image_path, "wb") as f:
                    f.write(resp.content)
                logging.info(f"Image from Wikimedia: {real_url}")
                return image_path
        except Exception as e:
            logging.warning(f"Wikimedia image failed: {e}")

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
                    img_url = results[0]["urls"]["regular"]
                    img_resp = requests.get(img_url, timeout=15)
                    if img_resp.status_code == 200:
                        image_path = os.path.join(tempfile.gettempdir(), "buenavista_daily.jpg")
                        with open(image_path, "wb") as f:
                            f.write(img_resp.content)
                        logging.info(f"Image from Unsplash: {img_url}")
                        return image_path
        except Exception as e:
            logging.warning(f"Unsplash image failed: {e}")

    logging.warning("No image found for this location.")
    return None


def generate_post(location_data):
    """Use Claude to generate an engaging Bluesky post about the location."""
    if not CLAUDE_API_KEY:
        logging.error("CLAUDE_API_KEY missing!")
        return None

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    prompt = f"""You are a senior social media strategist for BuenaVista, a premium travel discovery brand.

Write ONE social media post about this place. STRICT LIMIT: between 240 and 290 characters. Aim for at least 240 characters. Use vivid details to fill the space.

Rules:
- Be impulsive, short, and attention-catching. Make people STOP scrolling.
- Vary your style every time — sometimes a bold statement, sometimes a question, sometimes a vivid one-liner. Do NOT follow the same formula.
- Do NOT write in first person.
- Highlight the single most fascinating thing about this place.
- Include 1-2 emojis naturally.
- Mention buenavista.in somewhere near the end (vary how — "via buenavista.in", "buenavista.in", "Find it on buenavista.in", etc.)
- End with #travel
- Do NOT use ellipsis (...) anywhere.
- Do NOT use em dashes (—) or double dashes (--) anywhere.
- Do NOT use quotes. Just the post text, nothing else.

Place: {location_data['name']}
Country: {location_data['country']}
Description: {location_data['description'][:500]}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}],
    )

    post_text = message.content[0].text.strip()

    # Bluesky limit is 300 chars (graphemes)
    if len(post_text) > 290:
        post_text = post_text[:290].rsplit(" ", 1)[0]

    logging.info(f"Generated Bluesky post ({len(post_text)} chars): {post_text}")
    return post_text


def bluesky_login():
    """Authenticate with Bluesky and return session tokens."""
    resp = requests.post(
        f"{ATP_BASE}/com.atproto.server.createSession",
        json={"identifier": BLUESKY_HANDLE, "password": BLUESKY_APP_PASSWORD},
        timeout=15,
    )
    resp.raise_for_status()
    session = resp.json()
    return session["did"], session["accessJwt"]


def bluesky_upload_image(access_token, image_path):
    """Upload an image to Bluesky and return the blob reference."""
    # Detect MIME type from extension
    ext = os.path.splitext(image_path)[-1].lower()
    mime_types = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif",
        ".webp": "image/webp",
    }
    mime_type = mime_types.get(ext, "image/jpeg")

    with open(image_path, "rb") as f:
        img_data = f.read()

    resp = requests.post(
        f"{ATP_BASE}/com.atproto.repo.uploadBlob",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": mime_type,
        },
        data=img_data,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["blob"]


def detect_facets(text):
    """Detect URLs and hashtags in text and return Bluesky facets."""
    import re
    facets = []
    # Links
    for match in re.finditer(r"https?://[^\s]+|buenavista\.in", text):
        url = match.group()
        if not url.startswith("http"):
            url = "https://" + url
        start = len(text[:match.start()].encode("utf-8"))
        end = len(text[:match.end()].encode("utf-8"))
        facets.append({
            "index": {"byteStart": start, "byteEnd": end},
            "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}],
        })
    # Hashtags
    for match in re.finditer(r"#(\w+)", text):
        start = len(text[:match.start()].encode("utf-8"))
        end = len(text[:match.end()].encode("utf-8"))
        facets.append({
            "index": {"byteStart": start, "byteEnd": end},
            "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": match.group(1)}],
        })
    return facets


def post_to_bluesky(post_text, image_path=None, location_name=""):
    """Post to Bluesky with optional image."""
    if not BLUESKY_HANDLE or not BLUESKY_APP_PASSWORD:
        logging.error("Bluesky credentials missing!")
        return None

    try:
        did, access_token = bluesky_login()

        # Build the post record
        record = {
            "$type": "app.bsky.feed.post",
            "text": post_text,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "facets": detect_facets(post_text),
        }

        # Upload image if available
        if image_path and os.path.exists(image_path):
            try:
                blob = bluesky_upload_image(access_token, image_path)
                record["embed"] = {
                    "$type": "app.bsky.embed.images",
                    "images": [{"alt": location_name or "BuenaVista travel discovery", "image": blob}],
                }
                logging.info("Uploaded image to Bluesky")
            except Exception as img_err:
                logging.warning(f"Bluesky image upload failed, posting without image: {img_err}")

        # Create the post
        resp = requests.post(
            f"{ATP_BASE}/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": record,
            },
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        post_uri = result["uri"]
        logging.info(f"Posted to Bluesky! URI: {post_uri}")
        return post_uri

    except Exception as e:
        logging.error(f"Failed to post to Bluesky: {e}")
        print(f"Bluesky Error: {e}")
        return None


def log_posted(location_data, post_text, post_uri):
    """Keep a log of all posted Bluesky posts."""
    entry = {
        "date": datetime.now().isoformat(),
        "location": location_data["name"],
        "country": location_data["country"],
        "post": post_text,
        "post_uri": post_uri,
    }

    posts = []
    if os.path.exists(POSTS_LOG):
        with open(POSTS_LOG, "r") as f:
            posts = json.load(f)

    posts.append(entry)

    with open(POSTS_LOG, "w") as f:
        json.dump(posts, f, indent=2)


if __name__ == "__main__":
    print("🦋 BuenaVista Bluesky Post")

    # Step 1: Fetch location
    location = fetch_location()
    if not location:
        print("Failed to fetch location. Check daily_locations.log")
        exit(1)

    print(f"📍 Location: {location['name']} ({location['country']})")

    # Step 2: Save markdown file
    filepath = save_location_file(location)
    print(f"📄 Saved: {filepath}")

    # Step 3: Generate post with AI
    post = generate_post(location)
    if not post:
        print("Failed to generate post. Check daily_locations.log")
        exit(1)

    print(f"🦋 Post: {post}")

    # Step 4: Fetch image
    image_path = fetch_image(location)
    if image_path:
        print(f"🖼️  Image: {image_path}")
    else:
        print("⚠️  No image found, posting without image.")

    # Step 5: Post to Bluesky
    post_uri = post_to_bluesky(post, image_path, location["name"])
    if not post_uri:
        print("Failed to post to Bluesky. Check daily_locations.log")
        exit(1)

    # Step 6: Log it
    log_posted(location, post, post_uri)
    print(f"✅ Posted! URI: {post_uri}")
