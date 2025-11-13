import requests
from bs4 import BeautifulSoup
import re
import json
# import ast
import os
import pandas as pd
from datetime import datetime
from tqdm import tqdm
import time, random

class SGCarMartScraper:

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }

    def get_brands(self):
        url = "https://www.sgcarmart.com/used-cars/listing?q=&avl=a"
        response = requests.get(url, headers=self.headers)
        html = response.text

        soup = BeautifulSoup(html, 'html.parser')
        scripts = [script.string for script in soup.find_all('script') if script.string]
        target_script = scripts[-2]   # THIRD last one

        cleaned = target_script.encode('utf-8').decode('unicode_escape')
        pattern = r'"value":"(.*?)","text":"(.*?)"'
        matches = re.findall(pattern, cleaned)
        
        start_printing = False
        brands = []
        for match in matches:
            if match[1] == 'All Makes':
                start_printing = True
                continue
            if start_printing and match[1] == 'Any Status':
                start_printing = False
                continue
            if start_printing:
                words = match[1].split(" ")
                brand = "+".join(words)
                brands.append(brand)
        return brands
        # return ["Toyota"] #To pull specific brands if got problem
    

    def get_urls(self, brand, start_date):
        def extract_listing_data(cleaned):
            key = '"listing_data":{"data":'
            start = cleaned.find(key)
            if start == -1:
                return None

            # # start index of the list
            # start += len(key)
            # depth = 0
            # in_list = False

            # for i, ch in enumerate(cleaned[start:], start=start):
            #     if ch == '[' and not in_list:
            #         in_list = True
            #         depth = 1
            #         list_start = i
            #     elif ch == '[' and in_list:
            #         depth += 1
            #     elif ch == ']' and in_list:
            #         depth -= 1
            #         if depth == 0:
            #             return cleaned[list_start:i+1]  # returns the full list as string

            # return None  # if no balanced list found

            i = start + len(key)
            n = len(cleaned)

            # find first '['
            while i < n and cleaned[i] != '[':
                i += 1
            if i >= n:
                return None

            list_start = i
            depth = 0
            in_string = False
            string_char = ''
            escaped = False

            while i < n:
                ch = cleaned[i]
                if in_string:
                    if escaped:
                        escaped = False
                    elif ch == '\\':
                        escaped = True
                    elif ch == string_char:
                        in_string = False
                else:
                    if ch == '"' or ch == "'":
                        in_string = True
                        string_char = ch
                    elif ch == '[':
                        depth += 1
                    elif ch == ']':
                        depth -= 1
                        if depth == 0:
                            # found matching closing bracket
                            return cleaned[list_start:i+1]
                i += 1

            # if no matching bracket found
            return None
        
        page = 1
        cars = []
        retry_count = 0

        while True:
            url = f"https://www.sgcarmart.com/used-cars/listing?q={brand}&avl=a&limit=100&page={page}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"}
            # response = requests.get(url, headers=headers)
            # html = response.text
            for attempt in range(3):
                try:
                    response = requests.get(
                        url,
                        headers=headers,
                        timeout=15,
                        stream=False
                    )
                    response.raise_for_status()
                    html = response.text
                    break
                except (requests.exceptions.ChunkedEncodingError,
                        requests.exceptions.ConnectionError,
                        requests.exceptions.ReadTimeout) as e:
                    print(f"List page error ({attempt+1}/3) for {url}: {e}")
                    if attempt == 2:
                        # can't read this brand page -> stop this brand gracefully
                        print(f"List page error for {url} and couldn't be added: {e}")
                        return pd.DataFrame([])   # or `break` if you prefer
                    time.sleep(30)
                except requests.HTTPError as e:
                    print(f"HTTP error on list page {url}: {e}")
                    return pd.DataFrame([])
            print(url)
            scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, flags=re.S)
            # print(scripts)
            target_script = scripts[-2]   # second last one
            cleaned = target_script.encode('utf-8').decode('unicode_escape')
            list_str = extract_listing_data(cleaned)
            finished = False
            # print(list_str)
            try:
                if list_str:
                    data_list = json.loads(list_str)
                    # print(f"Found {len(data_list)} items in the list")
                else:
                    print("No listing data found")
                    break
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                retry_count += 1
                if retry_count < 4:
                    print(f"No listing data found on page {page} for {brand}. Retrying ({retry_count}/3)...")
                    continue
                else:
                    print(f"Failed after 3 attempts on {brand} page {page}. Skipping page.")
                    page += 1
                    retry_count = 0
                    continue
            retry_count = 0
            
            if data_list:
                print(f"Processing {len(data_list)} items on page {page}")
            else:
                print("No more data found, ending.")
                break
                
            for data in data_list:
                date_posted = data['date']
                url = data['link']
                # convert string to datetime
                date_posted = datetime.strptime(date_posted, '%d-%b-%Y')

                if date_posted >= start_date:  # more recent than start_date
                    details = self.get_details(url)
                    cars.extend(details)
                    # do something
                    # print(f"{date_posted} is after {start_date}, url = {url}")
                else:
                    finished = True
                    break
            if finished:
                break
            
            page += 1
            
        df = pd.DataFrame(cars)
            
        return df
    
    def get_details(self, url):
        def extract_json(script):
            start = script.find('{')
            if start == -1:
                return None
            depth = 0
            for i, ch in enumerate(script[start:], start=start):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        return script[start:i+1]
            return None
        
        # response = requests.get(url, headers=self.headers)
        # html = response.text

        # Try pulling 3 times
        for attempt in range(3):
            try:
                resp = requests.get(
                    url,
                    headers=self.headers,
                    timeout=15,
                    stream=False
                )
                resp.raise_for_status()
                html = resp.text
                break
            except (requests.exceptions.ChunkedEncodingError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.ReadTimeout) as e:
                print(f"Fetch error ({attempt+1}/3) for {url}: {e}")
                if attempt == 2:
                    # give up on this listing but don't kill the whole run
                    return []
                time.sleep(1.2)
            except requests.HTTPError as e:
                print(f"HTTP error for {url}: {e}")
                return []

        soup = BeautifulSoup(html, 'html.parser')
        scripts = [script.string for script in soup.find_all('script') if script.string]

        results = []
        # print(url)
        # data['ucInfoDetailData']['data']['status'] == 'Available for sale':
        try:
            for i, script in enumerate(scripts):
                if 'infoUrlData' in script[:100]:
                    cleaned = script.encode('utf-8').decode('unicode_escape')
                    cleaned = extract_json(cleaned)
                    data = json.loads(cleaned)
                    price = data.get("ucInfoPageData", {}).get('data', {}).get('price', {})
                    ucInfoDetailData = data.get("ucInfoDetailData", {}).get('data', {})
                    # print(ucInfoDetailData)
                    coe_left = data.get("ucInfoPageData", {}).get('data', {}).get('coe_left', {})
                    # print(data.get("ucInfoPageData", {}))
                    fields = [
                        "car_model", "depreciation", "reg_date", "mileage", "manufactured",
                        "road_tax", "transmission", "dereg_value", "omv", "coe", "arf",
                        "engine_cap", "power", "curb_weight", "owners", "posted_on",
                        "drive_range", "lifespan", "original_reg_date", "indicative_price",
                        "auction_closing", 'status', 'fuel_type'
                    ]
                    extracted = {field: ucInfoDetailData.get(field) for field in fields}
                    extracted["type_of_vehicle"] = ucInfoDetailData.get("type_of_vehicle", {}).get("text")
                    extracted['price'] = price
                    extracted['url'] = url  # Add the url field
                    extracted['date_scraped'] = pd.Timestamp.now().strftime('%Y-%m-%d')
                    extracted['coe_left'] = coe_left
                    results.append(extracted)
                    # print(extracted)
                    time.sleep(random.uniform(0.25, 0.5))
                    break
        except Exception as e:
            print(f"Error processing {url}: {e}")

        if not results:
            print(f"No match in {url}")

        return results
    
    def scrape_from_scratch(self, cache_dir):
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        else:
            # Clear existing cache files
            existing_brands = set()
            for file in os.listdir(cache_dir):
                existing_brands.add(file.replace("sgcarmart_", "").replace(".csv", ""))
        brands = self.get_brands()
        start_time = pd.Timestamp.now()
        count = 0       
        start_date = datetime.strptime('1600-09-24', '%Y-%m-%d')
        # all_cars = []

        for brand in brands:
            if brand == 'Mitsubish':
                continue
            if brand not in existing_brands:
                print(f"Getting URLs for brand: {brand}")
               
                df = self.get_urls(brand, start_date=start_date)
                
                if not df.empty:
                    df['brand'] = brand.replace("+", " ")
                    df.to_csv(os.path.join(cache_dir, f"sgcarmart_{brand}.csv"), index=False)
                    # all_cars.extend(df.to_dict(orient='records'))
                    print(f"Added data for brand: {brand} with {len(df)} records")
                    count += len(df)
                elapsed_time = pd.Timestamp.now() - start_time
                print(f"Time taken so far: {elapsed_time}")
                print(f"Total records so far: {count}")
                print()
            else:
                print(f"Skipping brand {brand}, already scraped.")

        # Create one final DataFrame and save once at the end
        all_dfs = []

        for file in os.listdir(cache_dir):
            if file.endswith(".csv"):
                file_path = os.path.join(cache_dir, file)
                df = pd.read_csv(file_path)
                all_dfs.append(df)

        final_df = pd.concat(all_dfs, ignore_index=True)

        for file in os.listdir(cache_dir):
            if file.endswith(".csv"):
                file_path = os.path.join(cache_dir, file)
                os.remove(file_path)  # deletes the file
        
        return final_df

    def get_availability(self, url):
        def extract_json(script):
            start = script.find('{')
            if start == -1:
                return None
            depth = 0
            for i, ch in enumerate(script[start:], start=start):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        return script[start:i+1]
            return None
        
        # response = requests.get(url, headers=self.headers)
        # html = response.text

        # Try pulling 3 times
        for attempt in range(3):
            try:
                resp = requests.get(
                    url,
                    headers=self.headers,
                    timeout=15,
                    stream=False
                )
                # special case: page genuinely gone = sold
                if resp.status_code in (404, 410):
                    print(f"[SGCM] {resp.status_code} for {url} → treat as SOLD")
                    return False
                resp.raise_for_status()
                html = resp.text
                break
            except (requests.exceptions.ChunkedEncodingError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.ReadTimeout) as e:
                print(f"Fetch error ({attempt+1}/3) for {url}: {e}")
                if attempt == 2:
                    # give up on this listing but don't kill the whole run
                    time.sleep(300)
                    return True
                time.sleep(1.2)
            except requests.HTTPError as e:
                print(f"HTTP error for {url}: {e}")
                return True

        soup = BeautifulSoup(html, 'html.parser')
        scripts = [script.string for script in soup.find_all('script') if script.string]
        # print(f'URL: {url}')
        try:
            for i, script in enumerate(scripts):
                if 'infoUrlData' in script[:100]:
                    cleaned = script.encode('utf-8').decode('unicode_escape')
                    cleaned = extract_json(cleaned)
                    
                    data = json.loads(cleaned)
                    # print(data['ucInfoDetailData']['data']['status'])
                    if data['ucInfoDetailData']['data']['status'] == 'Available for sale':
                        # print()
                        return True
                    elif data['ucInfoDetailData']['data']['status'] == 'SOLD' or data['ucInfoDetailData']['data']['status'] == 'Expired':
                        # print()
                        return False
                    else:
                        print(f"Unknown status for {url}: {data['ucInfoDetailData']['data']['status']}")
                        return True

        except Exception as e:
            print(f"Error processing {url}: {e}")
        # print()
        return True
    
    def get_recent_listings(self, date):
        brands = self.get_brands()
        start_time = pd.Timestamp.now()
        count = 0       
        all_cars = []

        for brand in brands:
            if brand == 'Mitsubish':
                continue
           
            print(f"Getting URLs for brand: {brand}")
            
            df = self.get_urls(brand, start_date=date)
            
            if not df.empty:
                df['brand'] = brand.replace("+", " ")
                all_cars.extend(df.to_dict(orient='records'))
                print(f"Added data for brand: {brand} with {len(df)} records")
                count += len(df)
            elapsed_time = pd.Timestamp.now() - start_time
            print(f"Time taken so far: {elapsed_time}")
            print(f"Total records so far: {count}")
            print()
        # Merge all records into a single DataFrame
        final_df = pd.DataFrame(all_cars)
        # Optionally, save to CSV
        # final_df.to_csv("./data/sgcarmart_recent_listings.csv", index=False)
        # print(f"Saved merged DataFrame with {len(final_df)} rows.")
        return final_df
        # merge all dfs

    def update_df(self, old_df):
        # print(old_df.columns)

        old_df['date_scraped'] = pd.to_datetime(
            old_df['date_scraped'].astype(str).str.strip(), format="%Y-%m-%d", errors="coerce"
        )
        latest_date = old_df['date_scraped'].max() - pd.Timedelta(days=1)
        print(f"Latest date_scraped minus 1 day: {latest_date}")

        new_df = self.get_recent_listings(latest_date)
        
        today = pd.Timestamp.now().strftime('%Y-%m-%d')
        new_df['date_scraped'] = today
        # add status column
        new_df['status'] = 'Available for sale'

        final_df = pd.concat([old_df, new_df], ignore_index=True)
        final_df = final_df.drop_duplicates(subset=['url']).reset_index(drop=True)
        print(f"Updated SgCarmart: Rows added {len(final_df) - len(old_df)}")
        final_df['date_scraped'] = pd.to_datetime(final_df['date_scraped'], errors='coerce').dt.strftime('%Y-%m-%d')
        final_df = final_df[final_df['car_model'].notna() & (final_df['car_model'].astype(str).str.strip() != "")]

        # for brand in final_df['brand'].unique():
        #     df_brand = final_df[(final_df['brand'] == brand) & (final_df['Available'] == True)].copy()
        #     print(f"Processing brand: {brand}, {len(df_brand)} entries to check")
        #     availability = []
        #     for idx, url in tqdm(zip(df_brand.index, df_brand['url']), desc=f"Checking availability for {brand}", total=len(df_brand)):
        #         try:
        #             is_available = self.get_availability(url)
        #         except Exception as e:
        #             print(url)
        #             is_available = False
        #         availability.append(is_available)
        #         # Update the main DataFrame directly
        #         final_df.loc[idx, 'Available'] = is_available

        
        # final_df.to_csv(f"./data/sgcarmart_all_brands_{today}.csv", index=False)
        # print(f"Final DataFrame saved with {len(final_df)} rows and date_scraped = {today}.")
        return final_df

def _normalize_url_series(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip()

def save_to_csv(df, filename=None):
    os.makedirs("./data", exist_ok=True)
    if filename is None:
        filename = f"sgcarmart_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join("data", filename)
    df.to_csv(filepath, index=False)
    print(f"Saved file: {filename}")

def get_sgcarmart_data(prev_df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a DataFrame of SGCarmart listings suitable for the DAG.
    - If prev_df is empty  -> full scrape (brand-by-brand) then merge results.
    - If prev_df has rows  -> incremental update since the last 'date_scraped'.
    Ensures:
      * 'url' is present, normalized, and unique (drops duplicate URLs)
      * 'date_scraped' exists (YYYY-MM-DD)
    """
    scraper = SGCarMartScraper()
    # Run scrape (full vs incremental)
    if not prev_df.empty:
        # incremental
        df = scraper.update_df(prev_df.copy())
    else:
        # full scrape into a cache dir (then merged by your class)
        cache_dir = "./data/sgcarmart/cache"
        os.makedirs(cache_dir, exist_ok=True)
        df = scraper.scrape_from_scratch(cache_dir=cache_dir)
    # Normalise & dedupe
    if df.empty:
        return df
    if "url" not in df.columns:
        raise ValueError("SGCarmart scrape missing 'url' column")
    df["url"] = _normalize_url_series(df["url"])
    df = df.drop_duplicates(subset=["url"], keep="last").reset_index(drop=True)

    # Guarantee a 'date_scraped' column (your class already sets it on new rows)
    if "date_scraped" not in df.columns or df["date_scraped"].isna().all():
        df["date_scraped"] = pd.Timestamp.now().strftime("%Y-%m-%d")
    else:
        # coerce to YYYY-MM-DD strings
        df["date_scraped"] = pd.to_datetime(df["date_scraped"], errors="coerce").dt.strftime("%Y-%m-%d")
    
    save_to_csv(df)
    return df