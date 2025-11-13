# motorist_new_listings.py
import csv
import os
import re
import time
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Reuse old scraper's pieces
from apis.motorist_webscraping import (
    LIST_URL,
    DEBUG_DIR,
    dbg,
    get_html,
    parse_detail_page,
)

# IDs & columns 
ID_RE = re.compile(r"/used-car/(?P<id>\d+)/")
POSTED_COL = "Posted Date"

DEFAULT_COLUMNS = [
    "url","title","price","Status","Posted Date",
    "Registration Date","Ownership","Mileage","Veh. Scheme","COE","OMV","ARF",
    "Min. PARF","Paper Value","Road Tax Payable","COE Expiry Date","PARF Expiry Date",
    "Road Tax Expiry Date","Manufacturing Year","Primary Colour","Transmission",
    "Fuel Type","Engine Capacity","Power"
]

def listing_id_from_url(url: str) -> str:
    m = ID_RE.search(url or "")
    return m.group("id") if m else ""

# CSV helpers 
def parse_iso_date(s: str) -> Optional[date]:
    if not s or s.strip().upper() in {"N.A.", "NA", "N/A", "-"}:
        return None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except Exception:
        return None

def load_existing(prev_df: pd.DataFrame) -> Tuple[Dict[str, dict], Optional[date], List[str]]:
    rows_by_id: Dict[str, dict] = {}
    header: List[str] = []
    latest: Optional[date] = None

    if prev_df is None or prev_df.empty:
        return rows_by_id, latest, header

    # Normalize URL and listing_id
    if "url" in prev_df.columns:
        prev_df["url"] = prev_df["url"].astype(str).str.strip()
    if "listing_id" not in prev_df.columns:
        prev_df["listing_id"] = prev_df["url"].apply(listing_id_from_url)

    header = list(prev_df.columns)

    # Convert each row to dict
    for _, row in prev_df.iterrows():
        lid = row.get("listing_id", "")
        if not lid:
            continue
        row_dict = row.to_dict()
        rows_by_id[lid] = row_dict

        # Parse Posted Date to track latest
        d = parse_iso_date(row_dict.get(POSTED_COL, ""))
        if d and (latest is None or d > latest):
            latest = d

    return rows_by_id, latest, header

def _date_for_sort(s: str) -> date:
    d = parse_iso_date(s)
    return d or date.min  # N.A. sinks to bottom

# def _id_for_sort(r: dict) -> int:
#     lid = r.get("listing_id") or listing_id_from_url(r.get("url", ""))
#     try:
#         return int(lid)
#     except Exception:
#         return -1

    # with open(csv_path, "w", encoding="utf-8", newline="") as f:
    #     w = csv.DictWriter(f, fieldnames=fieldnames)
    #     w.writeheader()
    #     for r in rows:
    #         w.writerow({k: r.get(k, "") for k in fieldnames})

def save_to_csv(df, filename=None):
    os.makedirs("./data", exist_ok=True)
    if filename is None:
        filename = f"motorist_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join("data", filename)
    df.to_csv(filepath, index=False)
    print(f"Saved file: {filename}")

# # spotlight detection on INDEX 
# SPOTLIGHT_CLASS_RE = re.compile(r"(spotlight|featured|sponsored|promo)", re.I)
# SPOTLIGHT_TEXT_RE  = re.compile(r"\b(Spotlight|Featured|Sponsored)\b", re.I)

def extract_links_with_spotlight(html: str, base: str) -> List[Tuple[str, bool]]:
    """
    Returns [(absolute_url, is_spotlight)] for each /used-car/ link.
    Spotlight is TRUE iff a descendant with classes 'used-cars-label spotlight' exists.
    """
    soup = BeautifulSoup(html, "html.parser")
    found: Dict[str, Tuple[str, bool]] = {}

    # First pass: collect and mark spotlight based on the badge inside the <a>
    for a in soup.find_all("a", href=True):
        href = (a["href"] or "").strip()
        if "/used-car/" not in href:
            continue

        url = urljoin(base, href)
        lid = listing_id_from_url(url)
        if not lid:
            continue

        # Precise badge check: look for <* class="used-cars-label spotlight">…</*>
        badge = a.select_one(".used-cars-label.spotlight") or a.select_one(".used-cars-label.premium")
        is_spot = badge is not None

        # Also accept exact badge text if top doesnt catch all
        # if not is_spot:
        #     txt = (a.get_text(" ", strip=True) or "").lower()
        #     is_spot = "spotlight ad" in txt

        found[lid] = (url, is_spot)
    
    # preserve page order as much as possible
    # (BeautifulSoup iteration order is DOM order; rebuild list in that order)
    ordered: List[Tuple[str, bool]] = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = (a["href"] or "").strip()
        if "/used-car/" not in href:
            continue
        url = urljoin(base, href)
        lid = listing_id_from_url(url)
        if not lid or lid in seen or lid not in found:
            continue
        ordered.append(found[lid])
        seen.add(lid)
    return ordered

def get_updated_motorist_data(prev_df: pd.DataFrame, max_pages_sanity: int = 10000) -> pd.DataFrame:
    """
    Incrementally fetch new Motorist listings based on previous DataFrame.

    Rules (spotlight-aware):
      • Include a listing if its Posted Date > latest in prev_df, OR
        Posted Date == latest AND listing_id not in prev_df (same-day new).
      • STOP when we encounter a NON-SPOTLIGHT listing whose Posted Date < latest.
      • Spotlight/Featured/Sponsored cards never trigger the stop (but older spotlight items are skipped).

    Returns a combined DataFrame (prev + new, current wins on duplicates), sorted newest first.
    """

    # Build rows_by_id from prev_df
    rows_by_id: Dict[str, dict] = {}
    latest_date: Optional[date] = None

    if prev_df is not None and not prev_df.empty:
        # normalize url; ensure listing_id column
        if "url" in prev_df.columns:
            prev_df["url"] = prev_df["url"].astype(str).str.strip()
        if "listing_id" not in prev_df.columns:
            prev_df["listing_id"] = prev_df["url"].apply(listing_id_from_url)
        prev_df["listing_id"] = prev_df["listing_id"].astype(str).str.strip()

        # harvest rows and detect latest posted date
        for _, r in prev_df.iterrows():
            lid = r.get("listing_id") or ""
            if not lid:
                continue
            rd = r.to_dict()
            rows_by_id[lid] = rd
            d = parse_iso_date(rd.get(POSTED_COL, ""))
            if d and (latest_date is None or d > latest_date):
                latest_date = d

    dbg(f"[new] loaded {len(rows_by_id)} rows; latest Posted Date: {latest_date or 'None'}")

    """
    Append only *new* rows:
      • Posted Date > latest date in CSV, or
      • Posted Date == latest date in CSV AND id not in CSV (same-day later postings)

    STOP condition:
      • Encounter a NON-SPOTLIGHT listing whose Posted Date < latest date in CSV.

    Spotlight/Featured/Sponsored cards NEVER trigger the stop even if older.
    """
    existing_ids = set(prev_df["listing_id"])
    added = 0
    seen_this_run = set()

    page = 1
    hard_stop = False

    # Crawl index pages until stop condition
    while page <= max_pages_sanity and not hard_stop:
        params = {"page": page, "_": int(time.time())}
        dbg(f"[new] Page {page}")

        try:
            list_html = get_html(LIST_URL, params=params, retries=1)
        except RuntimeError:
            dbg(f"[new] {LIST_URL}?page={page} non-OK (likely 404). Stop.")
            break

        items = extract_links_with_spotlight(list_html, base=LIST_URL.rsplit("/", 1)[0])
        if not items:
            dbg(f"[new] No links on page {page}. Stop.")
            break

        # process index items in order (assumed newest first)
        for url, is_spotlight in items:
            lid = str(listing_id_from_url(url)).strip()
            if not lid or lid in seen_this_run:
                continue
            seen_this_run.add(lid)

            # CASE A: ID already in df
            if lid in existing_ids:
                known_date = parse_iso_date(rows_by_id[lid].get(POSTED_COL, ""))
                dbg(f"[new] listing's known_date = {known_date}")
                # A1) SAME-DAY guard:
                # If we hit any previously-scraped listing from the LATEST day, stop now
                # if latest_date and known_date and known_date == latest_date:
                #     dbg(f"[new] Reached known listing {lid} on latest date {known_date}. Stop.")
                #     hard_stop = True
                #     break

                # A2) OLDER-than-latest guard (non-spotlight only): stop
                if latest_date and known_date and (known_date < latest_date) and not is_spotlight:
                    dbg(f"[new] Hit older known NON-SPOTLIGHT {lid} ({known_date} < {latest_date}). Stop.")
                    hard_stop = True
                    break

                # Otherwise it's either spotlight or newer; skip (already saved)
                continue

            # CASE B: New ID → fetch detail once to get Posted Date
            row = parse_detail_page(url)
            row["listing_id"] = lid
            posted_str = (row.get(POSTED_COL) or "").strip()
            posted = parse_iso_date(posted_str)
            dbg(f"posted_date: {posted}")

            include = False
            if latest_date is None:
                include = True  # first run, take all
            elif posted is None:
                # Unknown date: include to avoid missing new data, but does NOT affect stopping
                include = True
            elif posted > latest_date:
                include = True
            elif posted == latest_date:
                include = True  # same-day new ID → include
            else:
                # posted < latest_date: stop on NON-SPOTLIGHT; spotlight → skip but continue
                if not is_spotlight:
                    dbg(f"[new] First older NON-SPOTLIGHT NEW listing {lid} ({posted} < {latest_date}). Stop.")
                    hard_stop = True
                    break
                include = False # spotlight+older → skip but keep going

            if include:
                rows_by_id[lid] = row
                added += 1
                dbg(f"[new] + added {lid} (Posted {posted_str or 'N.A.'})")
            
        if hard_stop:
            dbg(f"[new] Stopping after page {page} due to hard_stop.")
            break

        page += 1

    dbg(f"[new] total added this run: {added}")

    # Build DataFrame, sort newest first (date, then id)
    rows = list(rows_by_id.values())
    if not rows:
        # stable schema
        out = pd.DataFrame(columns=DEFAULT_COLUMNS + ["listing_id", "scrape_date"])
    else:
        out = pd.DataFrame(rows)
        for col in DEFAULT_COLUMNS:
            if col not in out.columns:
                out[col] = pd.NA
        if "url" in out.columns:
            out["url"] = out["url"].astype(str).str.strip()
        if "listing_id" not in out.columns:
            out["listing_id"] = out["url"].apply(listing_id_from_url)

        # sort by Posted Date DESC, then listing_id DESC
        out = out.sort_values(
            by=[POSTED_COL, "listing_id"],
            key=lambda col: (
                col.map(_date_for_sort)
                if col.name == POSTED_COL
                else pd.to_numeric(col, errors="coerce").fillna(-1)
            ),
            ascending=[False, False],
            ignore_index=True,
        )

        # add scrape date if it is empty
        out["scrape_date"] = pd.to_datetime(out["scrape_date"], format="%Y-%m-%d", errors="coerce").dt.strftime("%Y-%m-%d")
        today = pd.Timestamp.now().strftime("%Y-%m-%d")
        out["scrape_date"] = out["scrape_date"].fillna(today)

    # # add scrape date
    # out['scrape_date'] = pd.Timestamp.now().strftime('%Y-%m-%d')

    save_to_csv(out, filename=None)
    return out

# # CLI 
# def main():
#     import argparse
#     parser = argparse.ArgumentParser(
#         description="Append only new Motorist listings since the latest Posted Date in the CSV (spotlight-aware)."
#     )
#     parser.add_argument("--csv-path", default="motorist_used_cars.csv",
#                         help="Path to existing CSV (updated in-place).")
#     parser.add_argument("--max-pages", type=int, default=10000,
#                         help="Sanity cap on pages to scan (default 10000).")
#     args = parser.parse_args()

#     os.makedirs(DEBUG_DIR, exist_ok=True)
#     added = scan_new_since_latest_spotlight_aware(
#         csv_path=args.csv_path,
#         max_pages_sanity=args.max_pages
#     )
#     print(f"Added {added} new rows.")

# if __name__ == "__main__":
#     main()
