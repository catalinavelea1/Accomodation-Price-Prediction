
from pathlib import Path

# Cai
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
DETAILS_HTML_DIR = RAW_DIR / "details_html"
SEARCH_RESULTS_FILE = RAW_DIR / "search_results.jsonl"
PROCESSED_DIR = ROOT / "data" / "processed"
DATASET_FILE = PROCESSED_DIR / "dataset.csv"

# Regiunea de interes = statiuni de schi din Romania
CITIES = [
    "Azuga",
    "Busteni",
    "Sinaia",
    "Predeal",
    "Poiana Brasov",
    "Rasnov",
    "Moieciu",
    "Bran",
    "Brasov",
]
COUNTRY = "Romania"

# Tipuri de proprietate in functie de id filtru Booking
PROPERTY_TYPES = {
    "Hotel": 204,
    "Apartment": 201,
    "Holiday home": 220,
    "Guest house": 216,
    "Chalet": 228,
    "Bed and breakfast": 208,
    "Villa": 213,
    "Hostel": 203,
}

# Parametrii cautarii: 1 noapte, 2 adulti, 1 camera, data = 13 ian 2027
CHECKIN = "2027-01-13"
CHECKOUT = "2027-01-14"
ADULTS = 2
ROOMS = 1
CURRENCY = "RON"
LANG = "en-gb"

MAX_RESULTS_PER_QUERY = 400

# Pauze intre cereri
DELAY_RANGE = (2.0, 5.0)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def search_url(city: str, ht_id: int) -> str:
    from urllib.parse import urlencode

    params = {
        "ss": f"{city}, {COUNTRY}",
        "checkin": CHECKIN,
        "checkout": CHECKOUT,
        "group_adults": ADULTS,
        "no_rooms": ROOMS,
        "group_children": 0,
        "selected_currency": CURRENCY,
        "lang": LANG,
        "nflt": f"ht_id={ht_id}",
    }
    return f"https://www.booking.com/searchresults.{LANG}.html?{urlencode(params)}"


def detail_url(base_url: str) -> str:
    from urllib.parse import urlencode

    params = {
        "checkin": CHECKIN,
        "checkout": CHECKOUT,
        "group_adults": ADULTS,
        "no_rooms": ROOMS,
        "group_children": 0,
        "selected_currency": CURRENCY,
    }
    return f"{base_url}?{urlencode(params)}"
