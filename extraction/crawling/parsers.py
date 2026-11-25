
import json
import re

from bs4 import BeautifulSoup

def _text(el) -> str:
    return el.get_text(" ", strip=True) if el else ""


def parse_number(s: str):
    if not s:
        return None
    m = re.search(r"\d[\d.,\s]*", s.replace("\xa0", " "))
    if not m:
        return None
    raw = m.group(0).strip().replace(" ", "")
    # separatori de mii: '1,234' / '1.234' ; zecimale: '8.5' / '8,5'
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", raw):
        raw = re.sub(r"[.,]", "", raw)
    else:
        raw = raw.replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def _first_int(pattern: str, text: str):
    m = re.search(pattern, text, flags=re.I)
    return int(m.group(1)) if m else None


def property_id_from_url(url: str) -> str:
    m = re.search(r"/hotel/([a-z]{2})/([^./?]+)", url)
    return f"{m.group(1)}/{m.group(2)}" if m else url


# Pagina de rezultate
def parse_search_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for card in soup.select('[data-testid="property-card"]'):
        link = card.select_one('a[data-testid="title-link"]') or card.select_one("a[href*='/hotel/']")
        if not link or not link.get("href"):
            continue
        url = link["href"].split("?")[0]
        if url.startswith("/"):
            url = "https://www.booking.com" + url

        card_text = _text(card)
        review_text = _text(card.select_one('[data-testid="review-score"]'))
        units_text = _text(card.select_one('[data-testid="recommended-units"]'))

        stars_el = card.select_one('[data-testid="rating-stars"], [data-testid="rating-squares"]')
        stars = len(stars_el.find_all("span", recursive=False)) if stars_el else None

        rows.append({
            "property_id": property_id_from_url(url),
            "url": url,
            "name": _text(card.select_one('[data-testid="title"]')),
            "address": _text(card.select_one('[data-testid="address"]')),
            "distance_from_centre": _text(card.select_one('[data-testid="distance"]')),
            "price": parse_number(_text(card.select_one('[data-testid="price-and-discounted-price"]'))),
            "taxes_text": _text(card.select_one('[data-testid="taxes-and-charges"]')),
            "rating": _parse_rating(review_text),
            "num_reviews": _parse_num_reviews(review_text),
            "stars": stars or None,
            "unit_description": units_text,
            "bedrooms_card": _first_int(r"(\d+)\s+bedrooms?", units_text),
            "bathrooms_card": _first_int(r"(\d+)\s+bathrooms?", units_text),
            "beds_card": _first_int(r"(\d+)\s+(?:[a-z-]+\s+){0,2}beds?\b", units_text),
            "area_m2": _first_int(r"(\d+)\s*m²", units_text),
            "free_cancellation": int("free cancellation" in card_text.lower()),
            "breakfast_included": int("breakfast included" in card_text.lower()),
            "no_prepayment": int("no prepayment" in card_text.lower()),
        })
    return rows


def _parse_rating(review_text: str):
    m = re.search(r"\b(10(?:[.,]0)?|\d[.,]\d)\b", review_text)
    return float(m.group(1).replace(",", ".")) if m else None


def _parse_num_reviews(review_text: str):
    m = re.search(r"([\d.,]+)\s+(?:reviews?|external reviews?)", review_text, flags=re.I)
    return int(re.sub(r"[.,]", "", m.group(1))) if m else None


# Pagina unei proprietati
FACILITY_KEYWORDS = {
    "has_wifi": [r"wi-?fi", r"\binternet\b"],
    "has_parking": [r"parking"],
    "has_air_conditioning": [r"air conditioning", r"air-conditioning"],
    "has_balcony": [r"balcony"],
    "has_breakfast": [r"breakfast"],
    "has_kitchen": [r"kitchen"],
    "has_pool": [r"swimming pool", r"(indoor|outdoor|plunge|infinity) pool"],
    "has_pets_allowed": [r"pets (are )?allowed"],
    "has_ski_storage": [r"ski storage", r"ski equipment"],
    "has_ski_to_door": [r"ski-to-door", r"ski in/ski out", r"ski-in"],
    "has_sauna": [r"sauna"],
    "has_fireplace": [r"fireplace"],
    "has_hot_tub": [r"hot tub", r"jacuzzi"],
}
NEG_BEFORE = r"\b(no|without)\s+(\w+\s+)?$"
NEG_AFTER = r"^(\W{0,3}no\b|[^|·•]{0,12}\b(not available|unavailable|not possible)\b)"


def _facilities_text(soup: BeautifulSoup) -> str:
    blocks = soup.select(
        '[data-testid="property-most-popular-facilities-wrapper"], '
        '[data-testid="facility-group-container"], '
        '[data-testid="property-facilities-block-container"], '
        "#hp_facilities_box, .hp_desc_important_facilities"
    )
    return " | ".join(_text(b) for b in blocks)


def _has_facility(text: str, patterns: list[str]) -> int:
    low = text.lower()
    for p in patterns:
        for m in re.finditer(p, low):
            before = low[max(0, m.start() - 20): m.start()]
            after = low[m.end(): m.end() + 30]
            if not re.search(NEG_BEFORE, before) and not re.search(NEG_AFTER, after):
                return 1
    return 0


def parse_detail_page(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    out: dict = {}

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, dict) and data.get("@type") in {"Hotel", "LodgingBusiness", "Apartment", "Hostel", "BedAndBreakfast"}:
            agg = data.get("aggregateRating") or {}
            out["ld_type"] = data.get("@type")
            out["rating_ld"] = parse_number(str(agg.get("ratingValue", "")))
            out["num_reviews_ld"] = parse_number(str(agg.get("reviewCount", "")))
            addr = data.get("address") or {}
            out["locality"] = addr.get("addressLocality")
            out["postal_code"] = addr.get("postalCode")
            break

    # coordonate
    latlng = soup.select_one("[data-atlas-latlng]")
    if latlng:
        try:
            lat, lng = latlng["data-atlas-latlng"].split(",")[:2]
            out["latitude"], out["longitude"] = float(lat), float(lng)
        except ValueError:
            pass

    # capacitate maxima
    page_text = _text(soup)
    occ = [int(x) for x in re.findall(r"Max(?:imum)?\.?\s*(?:people|persons|guests|occupancy)\s*:?\s*(\d+)", page_text, flags=re.I)]
    for block in soup.select(".hprt-roomtype-occupancy-info, .hprt-occupancy-occupancy-info"):
        nums = [int(n) for n in re.findall(r"(\d+)\s*(?:adults?|child(?:ren)?|guests?|persons?|people)", _text(block), flags=re.I)]
        if nums:
            occ.append(sum(nums))
    out["max_capacity"] = max(occ) if occ else None

    # camere / bai / paturi
    out["bedrooms_detail"] = _first_int(r"(\d+)\s+bedrooms?", page_text)
    out["bathrooms_detail"] = _first_int(r"(\d+)\s+bathrooms?", page_text)
    out["beds_detail"] = _first_int(r"(\d+)\s+(?:[a-z-]+\s+){0,2}beds?\b", page_text)

    # facilitati
    fac_text = _facilities_text(soup) or page_text
    for col, patterns in FACILITY_KEYWORDS.items():
        out[col] = _has_facility(fac_text, patterns)
    out["num_facilities_listed"] = len(soup.select('[data-testid="facility-group-container"] li'))

    return out
