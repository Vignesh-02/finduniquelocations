import requests
import random
import os
from datetime import datetime
import logging

# 1. PATH SETUP
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(SCRIPT_DIR, "DailyViews")
SAVE_DIR = os.path.join(BASE_DIR, "Locations")
LOG_FILE = os.path.join(BASE_DIR, "daily_locations.log")

os.makedirs(SAVE_DIR, exist_ok=True)

# 2. LOGGING SETUP
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 3. CONFIGURATION
API_KEY = os.environ.get("OTM_API_KEY")
# Using only ONE broad category to bypass the "Unknown category name" error
OSM_KINDS = "natural"

def get_breathtaking_location():
    if not API_KEY:
        logging.error("API Key missing!")
        return None

    # We are using the most basic parameter set to ensure the 400 error goes away
    params = {
        "lon_min": -180,
        "lat_min": -60,
        "lon_max": 180,
        "lat_max": 70,
        "kinds": OSM_KINDS,
        "rate": "3",
        "limit": "100",
        "apikey": API_KEY
    }

    try:
        logging.info("Requesting data with simplified 'natural' category...")
        # Using the 'params' argument in requests handles URL encoding automatically
        response = requests.get("https://api.opentripmap.com/0.1/en/places/bbox", params=params, timeout=20)
        
        if response.status_code != 200:
            logging.error(f"API Error {response.status_code}: {response.text}")
            return None

        features = response.json().get('features', [])
        named_features = [f for f in features if f['properties'].get('name')]
        
        if not named_features:
            logging.warning("No named features found.")
            return None

        target = random.choice(named_features)
        xid = target['properties']['xid']

        details_url = f"https://api.opentripmap.com/0.1/en/places/xid/{xid}?apikey={API_KEY}"
        details = requests.get(details_url, timeout=20).json()

        return {
            "name": details.get('name', 'Hidden Wonder'),
            "description": details.get('wikipedia_extracts', {}).get('text', 'A spectacular natural location.'),
            "country": details.get('address', {}).get('country', 'Global'),
            "otm_url": details.get('otm', 'https://opentripmap.com')
        }
    except Exception as e:
        logging.error(f"Exception: {e}")
        return None

def save_to_file(data):
    date_str = datetime.now().strftime("%Y-%m-%d")
    clean_name = "".join(x for x in data['name'] if x.isalnum() or x in " -_").strip()
    filename = f"{date_str}_{clean_name.replace(' ', '_')}.md"
    filepath = os.path.join(SAVE_DIR, filename)

    content = f"# 🌍 Daily Discovery: {data['name']}\n**Country:** {data['country']}\n\n{data['description']}\n\n[OpenTripMap]({data['otm_url']})"
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath

if __name__ == "__main__":
    location_data = get_breathtaking_location()
    if location_data:
        path = save_to_file(location_data)
        print(f"Success! File created: {path}")
    else:
        print("Still failing. See daily_locations.log")
