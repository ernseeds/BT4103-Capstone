import os, time, random, requests, threading
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from apis.sgcarmart_scrape import SGCarMartScraper
from apis.motorist_webscraping import get_html, extract_sold_flag

# =========================
# WEBSITE CHECKER CONFIG
# =========================
BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# =========================
# PRINT CSV HELPER
# =========================
def save_to_csv(df, filename=None):
    os.makedirs("./final_datasets", exist_ok=True)
    if filename is None:
        filename = f"final_cleaned_dashboard_datasets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join("final_datasets", filename)
    df.to_csv(filepath, index=False)
    print(f"Saved file: {filename}")


# =========================
# LOW-LEVEL RETRY WRAPPER
# =========================
def with_retries(func, *, tries=3, base_sleep=0.8, jitter=0.3, **kwargs):
    """
    Call func(**kwargs) with retries; return (ok, value) where
    ok=False means all attempts failed.
    """
    for attempt in range(1, tries + 1):
        try:
            val = func(**kwargs)
            return True, val
        except Exception as e:
            sleep_for = base_sleep * attempt + random.random() * jitter
            print(f"[retry {attempt}/{tries}] {func.__name__} failed: {e} → sleep {sleep_for:.2f}s")
            time.sleep(sleep_for)
    return False, None


# =========================
# SITE: SGCARMART
# =========================
def process_sgcarmart(df_site: pd.DataFrame, master_df: pd.DataFrame, prev_df:pd.DataFrame, max_workers: int = 2):
    """
    Parallel-ish SGCM checker.
    Uses small pool (default 2) to avoid hitting SGCM too hard.
    """
    if df_site.empty:
        return 0

    sold_count = 0
    lock = threading.Lock()
    futures = {}

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for i, row in enumerate(df_site.itertuples(index=False)):
            url = getattr(row, "URL", None)
            if not isinstance(url, str) or not url.strip():
                continue

            def job(u=url, idx=i):
                # each worker gets its own scraper, so no shared state
                tid = threading.get_ident()
                scraper = SGCarMartScraper()

                def _inner_call():
                    available = scraper.get_availability(u)
                    return not available  # True -> sold

                ok, is_sold = with_retries(_inner_call, tries=3)
                if not ok:
                    print(f"<{tid}> [SGCM] FAIL → {u}")
                    return u, False, tid

                return u, is_sold, tid

            fut = ex.submit(job)
            futures[fut] = url

        for fut in as_completed(futures):
            url, is_sold, tid = fut.result()
            if is_sold:
                with lock:
                    master_df.loc[master_df["URL"] == url, "Sold"] = True
                    prev_df.loc[prev_df["url"] == url, "status"] = "Sold"
                    sold_count += 1
                print(f"<{tid}> [SGCM] SOLD → {url}")
            else:
                print(f"<{tid}> [SGCM] OK → {url}")

    print(f"[SGCM] Finished, marked {sold_count} as sold.")
    return sold_count


# =========================
# SITE: CARRO
# =========================
def carro_check_once(url: str) -> bool:
    """
    Fetch a Carro detail page and read the status header.
    Returns True if SOLD / PENDING / RESERVED / ON HOLD, else False.
    """
    r = requests.get(url, headers=BASE_HEADERS, timeout=12, allow_redirects=True)
    if r.status_code in (404, 410):
        return True  # definitely gone
    soup = BeautifulSoup(r.text, "html.parser")

    status_tag = soup.select_one("div.styles__StyledStatusHeader-sc-7efdfd35-5")
    if status_tag:
        status_text = status_tag.get_text(strip=True)
        if status_text in {"Sold", "Pending Sale", "Reserved", "On Hold"}:
            return True
    return False

def process_carro(df_site: pd.DataFrame, master_df: pd.DataFrame, prev_df:pd.DataFrame, max_workers: int = 5):
    if df_site.empty:
        return 0

    sold_count = 0
    futures = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for row in df_site.itertuples(index=False):
            url = getattr(row, "URL", None)
            if not isinstance(url, str) or not url.strip():
                continue

            def job(u=url):
                tid = threading.get_ident()
                ok, val = with_retries(carro_check_once, tries=3, url=u)
                if val:
                    print(f"<{tid}> [CARRO] SOLD → {u}")
                else:
                    print(f"<{tid}> [CARRO] OK → {u}")
                return u, (val if ok else False)

            fut = ex.submit(job)
            futures[fut] = url

        for fut in as_completed(futures):
            url, is_sold = fut.result()
            if is_sold:
                master_df.loc[master_df["URL"] == url, "Sold"] = True
                prev_df.loc[prev_df["url"] == url, "sold"] = True
                sold_count += 1
                print(f"[CARRO] SOLD → {url}")

    print(f"[CARRO] Finished, marked {sold_count} as sold.")
    return sold_count


# =========================
# SITE: MOTORIST
# =========================
def motorist_check_once(url: str) -> bool:
    """
    Use your motorist_webscraping helpers:
    - get_html(url) already has retries
    - extract_sold_flag(soup) checks “Vehicle Sold”
    """
    # 1) fast check: is the page gone?
    try:
        r = requests.get(url, headers=BASE_HEADERS, timeout=10, allow_redirects=True)
        if r.status_code in (404, 410):
            print(f"[MOTORIST] {r.status_code} for {url} → treat as SOLD")
            return True
    except Exception as e:
        print(f"[MOTORIST] fetch error for {url}: {e}")
        return False

    # 2) fall back to existing HTML+parser flow
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    status = extract_sold_flag(soup)
    return str(status).lower().startswith("sold")


def process_motorist(df_site: pd.DataFrame, master_df: pd.DataFrame, prev_df:pd.DataFrame, max_workers: int = 5):
    if df_site.empty:
        return 0

    sold_count = 0
    futures = {}

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for row in df_site.itertuples(index=False):
            url = getattr(row, "URL", None)
            if not isinstance(url, str) or not url.strip():
                continue

            def job(u=url):
                # wrap with our retry too, to be consistent
                tid = threading.get_ident()
                ok, val = with_retries(motorist_check_once, tries=3, url=u)
                if val:
                    print(f"<{tid}> [MOTORIST] SOLD → {u}")
                else:
                    print(f"<{tid}> [MOTORIST] OK → {u}")
                return u, (val if ok else False)

            fut = ex.submit(job)
            futures[fut] = url

        for fut in as_completed(futures):
            url, is_sold = fut.result()
            if is_sold:
                master_df.loc[master_df["URL"] == url, "Sold"] = True
                prev_df.loc[prev_df["url"] == url, "Status"] = "Sold"
                sold_count += 1
                print(f"[MOTORIST] SOLD → {url}")

    print(f"[MOTORIST] Finished, marked {sold_count} as sold.")
    return sold_count


# =========================
# MAIN ENTRY
# =========================
def run_sold_check(df, prev_sgcm_df, prev_motor_df, prev_carro_df):
    # normalise
    df["Website"] = df["Website"].astype(str)
    df["URL"] = df["URL"].astype(str)

    # only check those not already sold
    pending = df[df["Sold"] == False].copy()
    pending["website_lc"] = pending["Website"].str.lower()

    sgcm_df = pending[pending["website_lc"] == "sgcarmart.com"]
    carro_df = pending[pending["website_lc"] == "carro.co"]
    motor_df = pending[pending["website_lc"] == "motorist.sg"]

    print(f"[MAIN] To check → SGCM: {len(sgcm_df)}, CARRO: {len(carro_df)}, MOTORIST: {len(motor_df)}")

    total_sold = 0
    total_sold += process_sgcarmart(sgcm_df, df, prev_sgcm_df, max_workers=1)
    total_sold += process_carro(carro_df, df, prev_carro_df, max_workers=5)
    total_sold += process_motorist(motor_df, df, prev_motor_df, max_workers=5)

    print(f"[MAIN] Total newly-marked SOLD = {total_sold}")

    save_to_csv(df)
    return df, prev_sgcm_df, prev_motor_df, prev_carro_df
    # _upload_to_gcs(df, FINAL_NAME, subdir=FINAL_SUBDIR)


# if __name__ == "__main__":
#     run_sold_check()