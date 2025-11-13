import os
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup as bs
import pandas as pd
from datetime import datetime
import random, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import requests
from urllib.parse import urlparse

# -----------------------------
# Click individual listings (More Details Version)
# -----------------------------

def run_scraper_with_clicks(prev_df, unlimited_clicker=False, max_clicks=3, max_workers=10, headless=True):
    """
    Clicks into each car listing on a specific page on SgCarMart.
    Extracts details from styles_container__ezmR5 on the detail page.
    Returns a list of dictionaries with detailed info.
    """
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "Opera/9.80 (Windows NT 6.1; WOW64) Presto/2.12.388 Version/12.18"
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=random.choice(user_agents),
            viewport={"width": random.randint(1280, 1920), "height": random.randint(720, 1080)},
            device_scale_factor=1,
            is_mobile=False,
        )
        page = context.new_page()

        all_links = []
        
        # -------------------------
        # Phase 1: Collect all Carro Certified links
        # -------------------------
        base_url = "https://carro.co/sg/en"
        print(f"Opening Carro listing page: {base_url}")
        page.goto(base_url, timeout=60000)
        time.sleep(random.uniform(1, 2))

        # Keep clicking "Show More Cars" and scrape page as we go
        click_count = 0
        prev_scroll_height = 0
        stop_pull_boolean = False
        while ((click_count < max_clicks) or unlimited_clicker) and not stop_pull_boolean:
            all_links, prev_scroll_height, stop_pull_boolean = scroll_to_bottom(prev_df, page, all_links, prev_scroll_height)
            if stop_pull_boolean:
                break
            try:
                show_more_button = page.query_selector("button:has-text('Show More Cars')")
                if show_more_button:
                    print(f"Clicking 'Show More Cars' [{click_count+1}]...")
                    show_more_button.click()
                    click_count += 1
                else:
                    print("No more 'Show More Cars' button found.")
                    break
            except Exception as e:
                print(f"No more cars to load or button missing: {e}")
                break

        print(f"Found {len(all_links)} Carro additional used car links.")

        context.close()
        browser.close()

        # Get the URLs of all links scrapped (for debugging)
        # url_df = pd.DataFrame(all_links)
        # save_to_excel(url_df, filename=f"carro_urls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

        # -------------------------
        # Phase 2: Scrape each link with parallelizing
        # -------------------------
        final_data = []
        chunks = chunk_list(all_links, max_workers)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chunk = {
                executor.submit(scrape_worker_chunk, chunk, user_agents, headless): idx
                for idx, chunk in enumerate(chunks)
            }
            for future in as_completed(future_to_chunk):
                data = future.result()
                final_data.extend(data)

        df = pd.DataFrame(final_data)
        df["scrape_date"] = datetime.today().strftime("%Y-%m-%d")

        if not prev_df.empty:
            df = pd.concat([prev_df, df], ignore_index=True, sort=False)

        return df

# -----------------------------
# Scraper for each list chunk to help with parallelizing
# -----------------------------
def scrape_worker_chunk(links_chunk, user_agents, headless=True):
    # Unique thread id
    thread_id = threading.get_ident() 

    # Open a browser for each parallel process
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=random.choice(user_agents),
            viewport={"width": random.randint(1280, 1920), "height": random.randint(720, 1080)},
            device_scale_factor=1,
            is_mobile=False,
        )

        all_data = []
        i = 0
        while i < len(links_chunk):
            link = links_chunk[i]
            time.sleep(random.uniform(2, 5))
            retries = 0
            success = False

            while retries < 3 and not success:
                try:
                    new_page = context.new_page()
                    new_page.goto(link, timeout=60000)
                    time.sleep(random.uniform(1.5, 3.5))
                    new_page.mouse.wheel(0, random.randint(500, 1500))
                    new_page.wait_for_selector("div.DetailOverview__StyledMetaCard-sc-5e76af8e-7")

                    html = new_page.content()
                    soup = bs(html, "html.parser")

                    # Title
                    name_el = soup.select_one("h1.detailTitle")
                    car_name = name_el.get_text(strip=True) if name_el else "N.A"

                    # Car Price
                    price_tag = soup.select_one("span.carPrice")
                    car_price = price_tag.get_text(strip=True) if price_tag else "N.A"

                    # Car Sold Boolean
                    status_tag = soup.select_one("div.styles__StyledStatusHeader-sc-7efdfd35-5")
                    status_text = status_tag.get_text(strip=True) if status_tag else ""
                    is_sold = status_text in ["Sold", "Pending Sale", "Reserved", "On Hold"]

                    # Collect cards (Number of Owners, Reg. Date, COE Left, etc.)
                    detail_dict = {}
                    cards = soup.select("div.DetailOverview__StyledMetaCard-sc-5e76af8e-7")
                    for card in cards:
                        label_tag = card.select_one("span.DetailOverview__StyleCardTitle-sc-5e76af8e-6")
                        value_tag = card.select_one("div.font-family-bold")
                        if label_tag and value_tag:
                            label = label_tag.get_text(strip=True)
                            value = value_tag.get_text(strip=True)
                            detail_dict[label] = value

                    # Collect meta-rows (Transmission, Engine CC, Fuel Type, etc.)
                    meta_rows = soup.select("div.meta-row")
                    for row in meta_rows:
                        name_tag = row.select_one("div.meta-name")
                        value_tag = row.select_one("div.meta-value")
                        if name_tag and value_tag:
                            label = name_tag.get_text(strip=True)
                            value = value_tag.get_text(strip=True)
                            detail_dict[label] = value

                    # Combine all info
                    car_data = {
                        "name": car_name,
                        "price": car_price,
                        "url": link,
                        "sold": is_sold,
                    }
                    
                    car_data.update(detail_dict)
                    posted_on_date, asking_price_updated_at = posted_on(slug_from(link))
                    car_data["posted_on"] = posted_on_date.split(" ")[0] # Add posted_on date
                    car_data["price_updated_on"] = asking_price_updated_at.split(" ")[0] # Add price updated date
                    all_data.append(car_data)

                    # Go back to listing
                    time.sleep(random.uniform(2, 5))  # random pause before closing
                    new_page.close()

                    success = True
                    print(f"[Thread {thread_id}] Succesfully scraped listing {i+1}")
                    i += 1 # only increment if we are succesful in pulling data

                except Exception as e:
                    print(f"[Thread {thread_id}] Failed to scrape listing {i+1}: {e}")
                    retries += 1
                    try:
                        context.close()
                        browser.close()
                    except:
                        pass
                    # restart browser/context here
                    browser = p.chromium.launch(headless=headless)
                    context = browser.new_context(
                        user_agent=random.choice(user_agents),
                        viewport={"width": random.randint(1280, 1920), "height": random.randint(720, 1080)},
                        device_scale_factor=1,
                        is_mobile=False,
                    )
                    time.sleep(2)
        
            if not success:
                print(f"[Thread {thread_id}] Skipping listing {i+1} after 3 failed attempts.")
                i += 1

        context.close()
        browser.close()
    return all_data

# -----------------------------
# Scroll to button of the page while pulling urls:
# -----------------------------

def scroll_to_bottom(prev_df, page, all_links, prev_scroll_height, step=1500, pause_range=(0.25, 0.5)):
    previous_height = prev_scroll_height
    unique_stop_urls = set(prev_df["url"].tolist()) if (prev_df is not None and not prev_df.empty and "url" in prev_df.columns) else None
    stop_pull_boolean = False
    while True:
        height = page.evaluate("() => document.body.scrollHeight")
        if previous_height == height:
            break
        if stop_pull_boolean:
            break
        for _ in range(previous_height, height, step):
            page.mouse.wheel(0, step)
            # time.sleep(random.uniform(*pause_range))
            cards = page.query_selector_all("div.ant-col-8 div.LazyRenderCard__StyleCardWrapper-sc-d4ea256-0")
            latest_link_saved = all_links[-1] if all_links else None
            link_pull_boolean = latest_link_saved is None
            if stop_pull_boolean:
                break
            for card in cards:
                link_el = card.query_selector("a")
                if not link_el:
                    continue
                href = link_el.get_attribute("href")
                link = "https://carro.co" + href
                if unique_stop_urls and link in unique_stop_urls:
                    print(f"Carro: Reached old listing url {link}")
                    stop_pull_boolean = True
                    break
                if not link_pull_boolean:
                    if link == latest_link_saved:
                        link_pull_boolean = True
                    continue
                # Skip New Cars
                if "/cars/" in link:
                    all_links.append(link)
        previous_height = height
    return all_links, previous_height, stop_pull_boolean

# -----------------------------
# Split all website links into chunks:
# -----------------------------

def chunk_list(lst, n):
    k, m = divmod(len(lst), n)
    return [lst[i*k + min(i, m):(i+1)*k + min(i+1, m)] for i in range(n)]

# -----------------------------
# Helper to get car listing dates
# -----------------------------

def slug_from(url):
    return urlparse(url).path.rstrip("/").split("/")[-1]

def posted_on(slug):
    try:
        r = requests.get(
            f"https://crazy-rabbit-api.carro.sg/api/v1/rabbit/sg/listings/{slug}?lang=en",
            timeout=12
        )
        posted_date = r.json()["data"].get("listed_at")
        asking_price_updated_at  = r.json()["data"].get("asking_price_updated_at")
        return posted_date, asking_price_updated_at
    except Exception:
        return None, None

# -----------------------------
# Saves a DataFrame to Excel, uses current timestamp.
# -----------------------------

def save_to_csv(df, filename=None):
    os.makedirs("./data", exist_ok=True)
    if filename is None:
        filename = f"carro_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join("data", filename)
    df.to_csv(filepath, index=False)
    print(f"Saved file: {filename}")

def get_carro_data(prev_df): #If unlimited_clicker is set to True, it ignores max_clicks
    df = run_scraper_with_clicks(prev_df, unlimited_clicker=True, max_clicks=2, max_workers=20, headless=True)
    save_to_csv(df, filename=None)
    return df

# Daily scrape with clicks
# daily_df = run_scraper_with_clicks(unlimited_clicker=True, max_clicks=2, max_workers=20) 
# save_to_excel(daily_df)
# print("-----------------------------")
# print("Daily Scraper: ")
# print(daily_df.head())
# print(daily_df.tail())