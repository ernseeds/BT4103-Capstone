import os
import re
from datetime import datetime
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Config
BASE = "https://www.motorist.sg"
LIST_URL = f"{BASE}/used-cars"
DEBUG_DIR = "debug"
NUM_PAGES = 5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-SG,en;q=0.9",
    "Referer": BASE + "/",
    "Connection": "keep-alive",
}

# Flexible patterns for regex
DETAIL_ABS_RE = re.compile(
    r'href\s*=\s*["\']\s*(https?://[^"\']+/used-car/\d+[^"\']*)\s*["\']',
    re.I
)
DETAIL_REL_RE = re.compile(
    r'href\s*=\s*["\']\s*(/used-car/\d+[^"\']*)\s*["\']',
    re.I
)
ROUGH_PATH = re.compile(r"/used-car/\d+/\S+")
PRICE_TEXT_RE = re.compile(r'^\s*\$\s?\d[\d,]*\s*$')
MONEY_RE = re.compile(r'\$\s?\d[\d,]*')
EXCLUDE_NEAR = re.compile(r'(instl|mth|month|depre|/yr|per\s*(month|year))', re.I)
DETAIL_ID_RE = re.compile(r"/used-car/(?P<id>\d+)/")
SOLD_RE = re.compile(r'^\s*Vehicle\s+Sold\s*$', re.I)
POSTED_RE = re.compile(r"\bPosted\s+(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{2,4})\b", re.I)
MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct":10, "nov":11, "dec":12
}

## helper functions
def dbg(msg: str):
    print(f"[DEBUG] {msg}", flush=True)

MISSING_TOKENS = {"", "-", "–", "—", "n/a", "na", "nil"}

def coerce_na(val, label=None):
    s = clean_text(val)
    if (not s) or (s.lower() in MISSING_TOKENS) or (label and s.lower() == label.lower()):
        return "N.A."
    return s

def listing_id_from_url(url: str) -> str:
    m = DETAIL_ID_RE.search(url or "")
    return m.group("id") if m else ""

def get_html(url, params=None, retries=3, timeout=30):
    """GET helper with loud debug."""
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(
                url, params=params, headers=HEADERS, timeout=timeout, allow_redirects=True
            )
            dbg(f"GET {r.request.url} -> {r.status_code}")
            dbg(f"Headers sent: {HEADERS}")
            dbg(f"Response URL: {r.url}")
            if r.ok:
                return r.text
            else:
                dbg(f"Non-OK status. Sleeping and retrying... attempt {attempt}/{retries}")
        except Exception as e:
            dbg(f"Exception on GET: {e} (attempt {attempt}/{retries})")
        time.sleep(1.0 * attempt)
    raise RuntimeError(f"Failed to fetch {url} after {retries} retries")

def extract_detail_links_from_html(html, page_num=None):
    """Try multiple strategies to find detail links and print what we see."""
    os.makedirs(DEBUG_DIR, exist_ok=True)

    # Parse anchors
    soup = BeautifulSoup(html, "html.parser")
    anchors = soup.find_all("a", href=True)

    links = set()

    # Strat 1: by parsing with BeautifulSoup, look for '/used-car/' in href
    for a in anchors:
        href = a["href"].strip()
        if "/used-car/" in href:
            links.add(urljoin(BASE, href))

    # Strat 2: regex (absolute and relative; both quote styles)
    for m in DETAIL_ABS_RE.finditer(html):
        links.add(m.group(1).strip())
    for m in DETAIL_REL_RE.finditer(html):
        links.add(urljoin(BASE, m.group(1).strip()))

    # Strat 3: last-ditch search in raw HTML (useful if inside scripts/data-attrs)
    for m in ROUGH_PATH.finditer(html):
        links.add(urljoin(BASE, m.group(0).rstrip('">)\'')))

    links = sorted(links)
    dbg(f"extract_detail_links_from_html: total detail links = {len(links)}")

    # Save listing page for manual inspection
    if page_num is not None:
        out = os.path.join(DEBUG_DIR, f"listing_page_{page_num}.html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)

    return links

def clean_text(x):
    return re.sub(r"\s+", " ", x).strip() if x else ""

def extract_posted_date(soup) -> str:
    """
    Returns the listing's posted date as YYYY-MM-DD if found, else 'N.A.'.
    Handles formats like: 'Posted 06 May 25' or 'Posted 06 May 2025 | Updated …'
    """
    # try to find a node that already matches
    node = soup.find(string=POSTED_RE)
    if node:
        m = POSTED_RE.search(node)
    else:
        # fallback: search the whole text if markup varies
        m = POSTED_RE.search(soup.get_text(" ", strip=True))
    if not m:
        return "N.A."

    d_s, mon_s, y_s = m.groups()
    try:
        d = int(d_s)
        y = int(y_s)
        if y < 100:  # e.g., 25 -> 2025
            y += 2000
        mon = MONTHS.get(mon_s[:3].lower(), 0)
        if not mon:
            return "N.A."
        return f"{y:04d}-{mon:02d}-{d:02d}"
    except Exception:
        return "N.A."

def find_value_by_label(soup, label):
    """Look for a label like 'Registration Date' and return the associated value."""
    # Exact label match first
    label_node = soup.find(string=re.compile(rf"^\s*{re.escape(label)}\s*$", re.I))
    if label_node:
        parent = label_node.find_parent(["dt","th","strong","b","span","div","p"])
        if parent:
            for sib in parent.next_siblings:
                if getattr(sib, "get_text", None):
                    val = clean_text(sib.get_text(" ", strip=True))
                    if val:
                        return val
        # Fallback: next text node
        if label_node.parent:
            nxt = label_node.parent.find_next(string=True)
            if nxt:
                return clean_text(nxt)

    # Secondary: lines like "Label: value"
    for node in soup.find_all(string=True):
        t = clean_text(node)
        if t.lower().startswith(label.lower()) and (":" in t or "\t" in t):
            after = t.split(":",1)[-1]
            return clean_text(after)
    return ""

def _find_price_card(soup):
    # Prefer the sidebar that contains "Seller Information"
    hdr = soup.find(string=re.compile(r'^\s*Seller Information\s*$', re.I))
    if hdr:
        return hdr.find_parent(['aside', 'section', 'div', 'article'])
    # Fallback: climb up from any "Instl." / "depre" hint
    hint = soup.find(string=re.compile(r'\bInstl\.?\b|\bdepre\b', re.I))
    node = hint
    for _ in range(6):
        if not node:
            break
        if getattr(node, 'name', None) in ('aside', 'section', 'div', 'article'):
            return node
        node = getattr(node, 'parent', None)
    return None

def _pick_price_from_container(el):
    """Largest $ amount in the element text, excluding monthly/depre contexts."""
    if not el:
        return ""
    txt = el.get_text(" ", strip=True)
    candidates = []
    for m in MONEY_RE.finditer(txt):
        # discard amounts with 'mth/Instl/depre/yr' in a small context window
        start, end = m.span()
        ctx = txt[max(0, start - 24): min(len(txt), end + 24)]
        if EXCLUDE_NEAR.search(ctx):
            continue
        n = int(re.sub(r'\D', '', m.group()))
        if n >= 1000:
            candidates.append(n)
    return f"${max(candidates):,}" if candidates else ""

def extract_display_price(soup):
    """
    Robust price extractor:
      1) Offer Price (if present & >= 1000)
      2) Exact $xx,xxx text in the price card
      3) Max $ in price card excluding 'mth'/'depre'
    """
    # 1) Loan Calculator → Offer Price
    for label in soup.find_all(string=re.compile(r'^\s*Offer Price\s*$', re.I)):
        box = label.find_parent()
        if box:
            inp = box.find_next('input')
            if inp:
                raw = (inp.get('value') or inp.get('placeholder') or '').strip()
                digits = re.sub(r'\D', '', raw)
                if digits:
                    n = int(digits)
                    if n >= 1000:  # ignore blank/zero/silly values
                        return f"${n:,}"

    # 2) Price card → look for an element whose text is EXACTLY a price
    card = _find_price_card(soup)
    if card:
        for tag in card.find_all(['h1','h2','h3','strong','span','div'], string=True):
            txt = clean_text(tag.get_text(" ", strip=True))
            if PRICE_TEXT_RE.match(txt):
                return txt

        # 3) Fallback in the card: largest $ not labeled monthly/depre
        val = _pick_price_from_container(card)
        if val:
            return val

    # Last-chance fallback: broaden slightly around Seller Information if card detection fails
    seller = soup.find(string=re.compile(r'Seller Information', re.I))
    if seller:
        sidebar = seller.find_parent(['aside','section','div','article']) or soup
        for tag in sidebar.find_all(['h1','h2','h3','strong','span','div'], string=True):
            txt = clean_text(tag.get_text(" ", strip=True))
            if PRICE_TEXT_RE.match(txt):
                return txt
        val = _pick_price_from_container(sidebar)
        if val:
            return val

    return ""  

def extract_sold_flag(soup) -> str:
    """
    Returns 'Yes' if the detail page shows the 'Vehicle Sold' badge, else 'No'.
    """
    # direct text match anywhere in the page
    if soup.find(string=SOLD_RE):
        return "Sold"

    # optional: also check the right-hand sidebar where price lives
    seller_hdr = soup.find(string=re.compile(r'^\s*Seller Information\s*$', re.I))
    if seller_hdr:
        sidebar = seller_hdr.find_parent(['aside','section','div','article'])
        if sidebar and sidebar.find(string=SOLD_RE):
            return "Sold"

    return "Available"

def parse_detail_page(url):
    """Fetch and parse a detail page; dump HTML for inspection (no per-listing prints)."""
    html = get_html(url)

    # Persist detail page for inspection
    os.makedirs(DEBUG_DIR, exist_ok=True)
    m = DETAIL_ID_RE.search(url)
    did = m.group("id") if m else str(int(time.time()))
    path = os.path.join(DEBUG_DIR, f"detail_{did}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    dbg(f"Wrote detail HTML to {path}")

    soup = BeautifulSoup(html, "html.parser")

    # Title and price are parsed but not printed
    h = soup.find(["h1", "h2"])
    title = clean_text(h.get_text(" ", strip=True)) if h else ""
    price = extract_display_price(soup)
    sold_flag = extract_sold_flag(soup)
    posted_date = extract_posted_date(soup)


    labels = [
        "Registration Date","Ownership","Mileage","Veh. Scheme","COE","OMV","ARF",
        "Min. PARF","Paper Value","Road Tax Payable","COE Expiry Date",
        "PARF Expiry Date","Road Tax Expiry Date","Manufacturing Year",
        "Primary Colour","Transmission","Fuel Type","Engine Capacity","Power",
    ]
    fields = {lab: coerce_na(find_value_by_label(soup, lab), lab) for lab in labels}

    return {
        "url": url,
        "title": title.lstrip("# ").strip(),
        "price": price,
        "Status": sold_flag,
        "Posted Date": posted_date,
        **fields,
    }

def crawl(num_pages=3, delay=0.1):
    seen_links = set()
    rows = []

    for page in range(1, num_pages + 1):
        params = {"page": page, "order": "price-asc", "_": int(time.time())}
        dbg(f"--- Page {page} ---")
        list_html = get_html(LIST_URL, params=params)
        links = extract_detail_links_from_html(list_html, page_num=page)

        if not links:
            dbg(f"No links found on page {page}. Stopping.")
            break

        new_links = [u for u in links if u not in seen_links]
        dbg(f"New links on page {page}: {len(new_links)} (of {len(links)} total)")
        if not new_links:
            dbg(f"No new links on page {page}. Stopping.")
            break

        for url in new_links:
            seen_links.add(url)
            try:
                dbg(f"Fetching detail: {url}")
                row = parse_detail_page(url)
                rows.append(row)
                dbg(f"Added row #{len(rows)}")
            except Exception as e:
                dbg(f"[WARN] detail fetch failed: {url} -> {e}")
            # time.sleep(delay + random.random() * 0.5)  # jitter

        # time.sleep(delay + random.random() * 0.5)

    return rows

def crawl_all(delay=0.1, max_consecutive_no_new=2, max_repeated_pages=2):
    """
    Crawl ALL listing pages with guardrails:
      - Stop if a page has no links
      - Stop after 'max_consecutive_no_new' pages in a row with no new links
      - Stop if the same page (same link set) repeats 'max_repeated_pages' times
    """
    seen_links = set()
    rows = []
    page = 1

    consecutive_no_new = 0
    last_fingerprint = None
    repeated_pages = 0

    while True:
        params = {"page": page, "_": int(time.time())}  
        dbg(f"--- Page {page} ---")
        
        # Break cleanly when the site returns 404 (no pages left)
        try:
            list_html = get_html(LIST_URL, params=params, retries=3)
        except RuntimeError as e:
            dbg(f"Non-OK on page {page} (likely 404). Assuming no more pages. Stopping.")
            break

        links = extract_detail_links_from_html(list_html, page_num=page)

        if not links:
            dbg(f"No links found on page {page}. Assuming end of listings.")
            break

        # Fingerprint the page's links to detect repeated last-page responses
        fingerprint = tuple(links)
        if last_fingerprint is not None and fingerprint == last_fingerprint:
            repeated_pages += 1
            dbg(f"Page {page} has identical link set as previous (repeat #{repeated_pages}).")
        else:
            repeated_pages = 0
        last_fingerprint = fingerprint

        new_links = [u for u in links if u not in seen_links]
        dbg(f"New links on page {page}: {len(new_links)} (of {len(links)} total)")

        if not new_links:
            consecutive_no_new += 1
            dbg(f"No NEW links on page {page}. Consecutive no-new pages: {consecutive_no_new}")
        else:
            consecutive_no_new = 0

        # Stop conditions to avoid infinite loops
        if consecutive_no_new >= max_consecutive_no_new:
            dbg("Stopping: hit consecutive pages with no new links.")
            break
        if repeated_pages >= max_repeated_pages:
            dbg("Stopping: page content repeated too many times (likely last page).")
            break

        # Fetch details for any new links
        for url in new_links:
            seen_links.add(url)
            try:
                dbg(f"Fetching detail: {url}")
                row = parse_detail_page(url)
                rows.append(row)
                dbg(f"Added row #{len(rows)}")
            except Exception as e:
                dbg(f"[WARN] detail fetch failed: {url} -> {e}")
            # time.sleep(delay + random.random() * 0.5)  # jitter

        page += 1
        # time.sleep(delay + random.random() * 0.5)

    dbg(f"[crawl_all] Finished. Total rows: {len(rows)} across {page-1} pages.")
    return rows

def crawl_available_only(max_pages=500, delay=0.1):
    """
    Crawl listing pages and stop as soon as we encounter a SOLD listing.
    Only returns available listings collected up to that point.
    """
    seen_links = set()
    rows = []

    for page in range(1, max_pages + 1):
        params = {"page": page, "_": int(time.time())}  # default ordering
        dbg(f"--- Page {page} ---")
        try:
            list_html = get_html(LIST_URL, params=params)
        except RuntimeError as e:
            dbg(f"[available_only] listing page fetch failed: {e}")
            break

        links = extract_detail_links_from_html(list_html, page_num=page)
        if not links:
            dbg(f"[available_only] No links on page {page}. Stopping.")
            break

        new_links = [u for u in links if u not in seen_links]
        dbg(f"[available_only] New links on page {page}: {len(new_links)} (of {len(links)} total)")
        if not new_links:
            dbg(f"[available_only] No new links on page {page}. Stopping.")
            break

        for url in new_links:
            seen_links.add(url)
            try:
                dbg(f"[available_only] Fetching detail: {url}")
                row = parse_detail_page(url)
                # IMPORTANT: stop immediately if this listing is sold
                if row.get("Status", "") == "Sold":
                    dbg(f"[available_only] Encountered SOLD listing. Halting crawl at {url}")
                    return rows  # do not include the sold row
                rows.append(row)
                dbg(f"[available_only] Added row #{len(rows)}")
            except Exception as e:
                dbg(f"[available_only][WARN] detail fetch failed: {url} -> {e}")
            # time.sleep(delay + random.random() * 0.5)

        # time.sleep(delay + random.random() * 0.5)

    return rows

DEFAULT_COLUMNS = [
    "url","title","price","Status","Posted Date",
    "Registration Date","Ownership","Mileage",
    "Veh. Scheme","COE","OMV","ARF","Min. PARF","Paper Value","Road Tax Payable",
    "COE Expiry Date","PARF Expiry Date","Road Tax Expiry Date","Manufacturing Year",
    "Primary Colour","Transmission","Fuel Type","Engine Capacity","Power"
]

def save_to_csv(df, filename=None):
    os.makedirs("./data", exist_ok=True)
    if filename is None:
        filename = f"motorist_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join("data", filename)
    df.to_csv(filepath, index=False)
    print(f"Saved file: {filename}")

def get_motorist_data(mode: str = "available_only", **kwargs) -> pd.DataFrame:
    """
    Returns a DataFrame of Motorist listings.
    mode:
      - "available_only": stops when first SOLD is seen (your current default)
      - "all": crawl all pages with guardrails (crawl_all)
      - "pages": crawl a fixed number of pages (crawl), pass NUM_PAGES via kwargs
    Extra kwargs are passed to the selected crawl function.
    """
    if mode == "available_only":
        rows = crawl_available_only(**kwargs)
    elif mode == "all":
        rows = crawl_all(**kwargs)
    elif mode == "pages":
        num_pages = kwargs.pop("num_pages", 5)
        rows = crawl(num_pages=num_pages, **kwargs)
    else:
        raise ValueError(f"Unknown mode: {mode}")
    if not rows:
        # return empty df with stable schema so downstream never breaks
        df = pd.DataFrame(columns=DEFAULT_COLUMNS + ['scrape_date'])
        return df
    df = pd.DataFrame(rows)
    # ensure required columns exist
    for col in DEFAULT_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    # add scrape date and listing_id
    df['scrape_date'] = pd.Timestamp.now().strftime('%Y-%m-%d')
    if "listing_id" not in df.columns:
        df["listing_id"] = df["url"].apply(listing_id_from_url)
    
    save_to_csv(df, filename=None)
    return df


# # Main
# if __name__ == "__main__":
#     os.makedirs(DEBUG_DIR, exist_ok=True)
#     # data = crawl(NUM_PAGES)
#     # data = crawl_all()
#     data = crawl_available_only()
#     dbg(f"Total rows collected: {len(data)}")

#     fieldnames = list(data[0].keys()) if data else [
#         "url","title","price","Status","Posted Date",
#         "Registration Date","Ownership","Mileage",
#         "Veh. Scheme","COE","OMV","ARF","Min. PARF","Paper Value","Road Tax Payable",
#         "COE Expiry Date","PARF Expiry Date","Road Tax Expiry Date","Manufacturing Year",
#         "Primary Colour","Transmission","Fuel Type","Engine Capacity","Power"
#     ]
#     with open("motorist_used_cars.csv", "w", newline="", encoding="utf-8") as f:
#         w = csv.DictWriter(f, fieldnames=fieldnames)
#         w.writeheader()
#         w.writerows(data)

#     print(f"Saved {len(data)} rows to motorist_used_cars.csv")
