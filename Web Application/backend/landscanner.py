import os, time, re, json, requests
from datetime import datetime
import pandas as pd
import numpy as np
from pandas_gbq import read_gbq
from google.oauth2 import service_account
from google.cloud import storage
from google.api_core.exceptions import NotFound
from bs4 import BeautifulSoup
from pathlib import Path

# ===============================
# Get GCS Key From Firebase / Local File
# ===============================
LOCAL_KEY = Path(__file__).with_name("car-resale-capstone-81cd3a4d7939.json")
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

def _is_managed_env():
    return any(os.getenv(k) for k in ("K_SERVICE", "FUNCTION_TARGET", "FIREBASE_CONFIG"))

def load_sa_credentials():
    # 1) If a secret is present, use it everywhere (local or prod)
    key_json = os.getenv("GCP_SA_JSON")
    if key_json:
        info = json.loads(key_json)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)

    # 2) Managed envs must use a secret
    if _is_managed_env():
        raise RuntimeError("Managed runtime detected; set GCP_SA_JSON (Secret Manager).")

    # 3) Run Local Key
    if LOCAL_KEY.exists():
        return service_account.Credentials.from_service_account_file(str(LOCAL_KEY), scopes=SCOPES)

    # 4) Fail Everything
    raise RuntimeError(f"Missing {LOCAL_KEY.name} at {LOCAL_KEY}")

creds = load_sa_credentials()

PROJECT_ID = "car-resale-capstone"
BQ_DATASET = "car_resale_bigquery"
GCS_BUCKET_NAME = "car-resale-bucket"
BQ_LOCATION = "asia-southeast1"

DATA_DIR = "datasets"
TEMP_DIR = "temporary" 

# ===============================
# 0) Google Cloud Helpers
# ===============================

def _gcs_client() -> storage.Client:
    return storage.Client(project=PROJECT_ID, credentials=creds)

def _download_from_gcs(name: str, subdir: str = DATA_DIR) -> pd.DataFrame:
    """
    Download gs://<bucket>/<subdir>/<name>.csv to a temp local path,
    load into a DataFrame, then delete the local file/folder like your original.
    Returns empty DataFrame if object does not exist.
    """
    gcs_path   = f"{subdir}/{name}.csv"
    local_dir  = subdir
    local_path = os.path.join(local_dir, f"{name}.csv")

    os.makedirs(local_dir, exist_ok=True)
    client = _gcs_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob   = bucket.blob(gcs_path)
    try:
        blob.download_to_filename(local_path)
        print(f"Downloaded {gcs_path} → {local_path}")
        df = pd.read_csv(local_path)
        print(f"Loaded {len(df)} rows from {name}.csv")
        return df
    except NotFound as e:
        print(f"No existing {gcs_path} found in GCS — returning empty DataFrame. ({e})")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error downloading/parsing {gcs_path}: {e}")
        return pd.DataFrame()
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)
            print(f"Deleted local file: {local_path}")
        if os.path.isdir(local_dir) and not os.listdir(local_dir):
            os.rmdir(local_dir)
            print(f"Deleted empty folder: {local_dir}")

def _upload_to_gcs(df: pd.DataFrame, name: str, subdir: str = DATA_DIR, encoding: str = "utf-8-sig"):
    """
    Save DataFrame to CSV locally, upload to gs://<bucket>/<subdir>/<name>.csv,
    then delete the local file/folder. UTF-8 with BOM helps Excel users.
    """
    os.makedirs(subdir, exist_ok=True)
    local_path = os.path.join(subdir, f"{name}.csv")
    gcs_path   = f"{subdir}/{name}.csv"

    # Write CSV locally first
    df.to_csv(local_path, index=False, encoding=encoding)

    # Upload to GCS
    client = _gcs_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob   = bucket.blob(gcs_path)

    try:
        blob.content_type = "text/csv"
        blob.upload_from_filename(local_path)
        print(f"Uploaded {name}.csv → gs://{GCS_BUCKET_NAME}/{gcs_path}")
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)
            print(f"Deleted local file: {local_path}")
        if os.path.isdir(subdir) and not os.listdir(subdir):
            os.rmdir(subdir)
            print(f"Deleted empty folder: {subdir}")

# For Dashboard Data
# def landscanner_bq_df():
#     df = read_gbq(
#         "SELECT URL, Brand, Make, Price, Registration_Date, Sold, " \
#         "Number_of_Previous_Owners, Mileage_km, Previous_COE, OMV," \
#         "Road_Tax_Payable, COE_Expiry_Date, Transmission, Fuel_Type," \
#         "Engine_Capacity_cc, Horse_Power_kW, Posted_Date," \
#         "Vehicle_Age_Years, COE_Left_Days," \
#         "COE_Category, COE_Renewed, Premium_Current_COE," \
#         "Previous_COE_Per_Month_Remaining, " \
#         "Five_Year_COE, Classic_Car, Website " \
#         "FROM `car-resale-capstone.car_resale_bigquery.final_dashboard_data`",
#         project_id=PROJECT_ID,
#         credentials=creds,
#     ) 
#     return df

def landscanner_bq_df():
    df = read_gbq(
        "SELECT URL, Brand, Make, Price, Registration_Date, Sold, " \
        "Number_of_Previous_Owners, Mileage_km, Previous_COE, OMV," \
        "Road_Tax_Payable, COE_Expiry_Date, Transmission, Fuel_Type," \
        "Engine_Capacity_cc, Horse_Power_kW, Posted_Date," \
        "Vehicle_Age_Years, COE_Left_Days," \
        "COE_Category, COE_Renewed, Premium_Current_COE," \
        "Previous_COE_Per_Month_Remaining, " \
        "Five_Year_COE, Classic_Car, Website " \
        "FROM `car-resale-capstone.car_resale_bigquery.final_dashboard_data`",
        project_id=PROJECT_ID,
        credentials=creds,
        location=BQ_LOCATION,
    ) 
    return df

def coe_gcs_df():
    coe_gcs_df = _download_from_gcs("final_coe_data", subdir="final_datasets")
    return coe_gcs_df

def dashboard_gcs_df():
    dashboard_gcs_df = _download_from_gcs("final_dashboard_data", subdir="final_datasets")
    return dashboard_gcs_df

def ml_gcs_df():
    ml_gcs_df = _download_from_gcs("final_ml_data", subdir="final_datasets")
    return ml_gcs_df

def get_all_omv():
    omv_gcs_df = _download_from_gcs("final_omv_data", subdir="final_datasets")
    return omv_gcs_df
# # Print CSV Helper
# def save_to_csv(df, filename=None):
#     os.makedirs("./landscanner_data", exist_ok=True)
#     if filename is None:
#         filename = f"pretty_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
#     filepath = os.path.join("landscanner_data", filename)
#     df.to_csv(filepath, index=False)
#     print(f"Saved file: {filename}")

# ===============================
# 1) Derived columns (once)
# ===============================
def prepare_derived(df: pd.DataFrame, today=None) -> pd.DataFrame:
    out = df.copy()

    # Date parsing (BigQuery dbdate comes in as str/object usually)
    for c in ["Registration_Date", "COE_Expiry_Date", "Posted_Date"]:
        if c in out.columns:
            out[c] = pd.to_datetime(out[c], errors="coerce")

    # Today baseline
    today = pd.to_datetime(today) if today is not None else pd.Timestamp.today().normalize()

    # Derived: months left, DPY/DPM, Freshness, Mileage/Year
    out["COE_Left_Months"] = (out["COE_Left_Days"] / 30.44).round().astype("Int64")

    # Depreciation
    out["DPY"] = out["Price"] / (out["COE_Left_Days"] / 365.0)
    out["DPM"] = out["Price"] / (out["COE_Left_Days"] / 30.44)

    posted = out["Posted_Date"]
    out["Freshness_Days"] = (today - posted).dt.days.astype("Int64")

    out["Mileage_per_Year"] = (out["Mileage_km"] / out["Vehicle_Age_Years"]).replace([np.inf, -np.inf], np.nan)

    # # Clean facets
    # for c in ["Brand", "Make", "Fuel_Type", "Transmission", "Website", "COE_Category"]:
    #     if c in out.columns:
    #         out[c] = out[c].astype("string").str.strip()

    return out

#dfp = prepare_derived(df)

# ===============================
# 2) Filter & Order helpers
# ===============================
def filter_by(d: pd.DataFrame, **f) -> pd.DataFrame:
    """
    Supported (all optional):
      price_min / price_max
      brand_in (list[str]) / make_contains (str) / website_in (list[str])
      mileage_max, owners_max, age_min, age_max
      coe_cat_in (['A','B']), coe_months_min, coe_renewed (bool),
      five_year (bool), classic (bool)
      fuel_in (list[str]), trans_in (list[str]),
      engine_cc_min / engine_cc_max, hp_kw_min / hp_kw_max
      sold (bool), freshness_max (int days)
    """
    out = d.copy()

    def _in(col, vals):
        if vals is None or vals == "": return pd.Series(True, index=out.index)
        return out[col].isin(vals)

    def _contains(col, s):
        if not s: return pd.Series(True, index=out.index)
        return out[col].str.contains(str(s), case=False, na=False)

    def _ge(col, v):
        if v is None or v == "": return pd.Series(True, index=out.index)
        return out[col].fillna(np.inf) >= v

    def _le(col, v):
        if v is None or v =="": return pd.Series(True, index=out.index)
        return out[col].fillna(-np.inf) <= v

    def _eq(col, v):
        if v is None or v =="": return pd.Series(True, index=out.index)
        return out[col] == v

    mask = (
        _ge("Price", f.get("price_min")) &
        _le("Price", f.get("price_max")) &
        _in("Brand", f.get("brand_in")) &
        _contains("Make", f.get("make_contains")) &
        _in("Website", f.get("website_in")) &
        _le("Mileage_km", f.get("mileage_max")) &
        _le("Number_of_Previous_Owners", f.get("owners_max")) &
        _ge("Vehicle_Age_Years", f.get("age_min")) &
        _le("Vehicle_Age_Years", f.get("age_max")) &
        _in("COE_Category", f.get("coe_cat_in")) &
        _ge("COE_Left_Months", f.get("coe_months_min")) &
        _eq("COE_Renewed", f.get("coe_renewed")) &
        _eq("Five_Year_COE", f.get("five_year")) &
        _eq("Classic_Car", f.get("classic")) &
        _in("Fuel_Type", f.get("fuel_in")) &
        _in("Transmission", f.get("trans_in")) &
        _ge("Engine_Capacity_cc", f.get("engine_cc_min")) &
        _le("Engine_Capacity_cc", f.get("engine_cc_max")) &
        _ge("Horse_Power_kW", f.get("hp_kw_min")) &
        _le("Horse_Power_kW", f.get("hp_kw_max")) &
        _eq("Sold", f.get("sold")) &
        _le("Freshness_Days", f.get("freshness_max"))
    )
    return out.loc[mask].copy()


def order_by(d: pd.DataFrame, key: str, limit=20, offset=0) -> pd.DataFrame:
    """
    key options:
      'best_value'       (composite; see below)
      'dpy_asc', 'dpm_asc'
      'price_asc', 'price_desc'
      'coe_months_desc'
      'mileage_asc', 'mileage_desc'
      'owners_asc'
      'posted_newest'    (Freshness_Days ascending)
    """
    data = d.copy()

    if key == "best_value":
        # Minimal, transparent composite on current set
        def _minmax(s):
            s = s.astype(float)
            if s.notna().any():
                lo, hi = np.nanmin(s), np.nanmax(s)
                if np.isfinite(lo) and np.isfinite(hi) and hi > lo:
                    return (s - lo) / (hi - lo)
            return pd.Series(0.5, index=s.index)  # neutral if degenerate

        valid = data[(data["COE_Left_Days"] > 0) & (data["Price"] > 0)].copy()
        s_dpy = 1 - _minmax(valid["DPY"])
        s_coe = _minmax(valid["COE_Left_Months"])
        s_mpy = 1 - _minmax(valid["Mileage_per_Year"])
        s_own = 1 - _minmax(valid["Number_of_Previous_Owners"].astype(float))

        valid["BestValue"] = 0.50*s_dpy + 0.20*s_coe + 0.20*s_mpy + 0.10*s_own
        data = valid.sort_values(["BestValue", "DPY"], ascending=[False, True])

    elif key == "dpy_asc":
        data = data[(data["COE_Left_Days"] > 0) & (data["Price"] > 0)].sort_values("DPY", ascending=True)
    elif key == "dpm_desc":
        data = data[(data["COE_Left_Days"] > 0) & (data["Price"] > 0)].sort_values("DPM", ascending=False)
    elif key == "dpm_asc":
        data = data[(data["COE_Left_Days"] > 0) & (data["Price"] > 0)].sort_values("DPM", ascending=True)
    elif key == "price_asc":
        data = data.sort_values("Price", ascending=True)
    elif key == "price_desc":
        data = data.sort_values("Price", ascending=False)
    elif key == "coe_months_desc":
        data = data.sort_values("COE_Left_Months", ascending=False)
    elif key == "coe_months_asc":
        data = data.sort_values("COE_Left_Months", ascending=True)
    elif key == "mileage_asc":
        data = data.sort_values("Mileage_km", ascending=True)
    elif key == "mileage_desc":
        data = data.sort_values("Mileage_km", ascending=False)
    elif key == "owners_asc":
        data = data.sort_values("Number_of_Previous_Owners", ascending=True)
    elif key == "posted_date_asc":
        data = data.sort_values("Freshness_Days", ascending=True)
    elif key == "posted_date_desc":
        data = data.sort_values("Freshness_Days", ascending=False)
    elif key == "age_asc":
        data = data.sort_values("Vehicle_Age_Years", ascending=True)
    elif key == "age_desc":
        data = data.sort_values("Vehicle_Age_Years", ascending=False)
    else:
        data = data.sort_values("Price", ascending=True)  # fallback

    if offset:
        data = data.iloc[offset:]
    if limit:
        data = data.head(limit)
    return data

def order_by_multi(d: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """
    Multi-column sorting that understands the same keys as order_by().
    Example:
        ["best_value", "price_asc"]
        ["price_asc", "mileage_asc"]
        ["posted_date_desc", "price_asc"]
    """
    data = d.copy()

    # If any key needs derived "BestValue", compute once
    needs_best = any(k in ("best_value", "best", "best_value_desc") for k in keys)
    if needs_best:
        valid = data[(data["COE_Left_Days"] > 0) & (data["Price"] > 0)].copy()

        def _minmax(s):
            s = s.astype(float)
            if s.notna().any():
                lo, hi = np.nanmin(s), np.nanmax(s)
                if np.isfinite(lo) and np.isfinite(hi) and hi > lo:
                    return (s - lo) / (hi - lo)
            return pd.Series(0.5, index=s.index)

        s_dpy = 1 - _minmax(valid["DPY"])
        s_coe = _minmax(valid["COE_Left_Months"])
        s_mpy = 1 - _minmax(valid["Mileage_per_Year"])
        s_own = 1 - _minmax(valid["Number_of_Previous_Owners"].astype(float))

        valid["BestValue"] = 0.50*s_dpy + 0.20*s_coe + 0.20*s_mpy + 0.10*s_own

        # put back only rows we scored
        data = valid.combine_first(data)

    cols = []
    ascendings = []

    for k in keys:
        if k in ("best_value", "best", "best_value_desc"):
            cols.append("BestValue")
            ascendings.append(False)  # higher is better
        elif k == "dpy_asc":
            cols.append("DPY"); ascendings.append(True)
        elif k == "dpm_asc":
            cols.append("DPM"); ascendings.append(True)
        elif k == "dpm_desc":
            cols.append("DPM"); ascendings.append(False)
        elif k == "price_asc":
            cols.append("Price"); ascendings.append(True)
        elif k == "price_desc":
            cols.append("Price"); ascendings.append(False)
        elif k == "coe_months_desc":
            cols.append("COE_Left_Months"); ascendings.append(False)
        elif k == "coe_months_asc":
            cols.append("COE_Left_Months"); ascendings.append(True)
        elif k == "mileage_asc":
            cols.append("Mileage_km"); ascendings.append(True)
        elif k == "mileage_desc":
            cols.append("Mileage_km"); ascendings.append(False)
        elif k == "owners_asc":
            cols.append("Number_of_Previous_Owners"); ascendings.append(True)
        elif k == "posted_date_asc":
            cols.append("Freshness_Days"); ascendings.append(True)
        elif k == "posted_date_desc":
            cols.append("Freshness_Days"); ascendings.append(False)
        elif k == "age_asc":
            cols.append("Vehicle_Age_Years"); ascendings.append(True)
        elif k == "age_desc":
            cols.append("Vehicle_Age_Years"); ascendings.append(False)
        # ignore unknown keys silently

    if cols:
        data = data.sort_values(cols, ascending=ascendings)

    return data


# # ===============================
# # 3) Pretty print
# # ===============================
# def _fmt_money(x, dp=0):
#     return "—" if pd.isna(x) or not np.isfinite(x) else f"{x:,.{dp}f}"

# def _fmt_int(x):
#     try:
#         return f"{int(x):,}"
#     except Exception:
#         return "—"

# def _fmt_dt(d, ym=False):
#     if pd.isna(d): return "—"
#     return pd.to_datetime(d).strftime("%Y-%m" if ym else "%Y-%m-%d")

# def print_list(d: pd.DataFrame):
#     for _, r in d.iterrows():
#         title = f"{(r['Brand'] or '')} {(r['Make'] or '')}".strip()
#         specs = f"{r.get('Fuel_Type') or '—'} • {r.get('Transmission') or '—'} • Cat {r.get('COE_Category') or '—'}"
#         line1 = title
#         line2 = (
#             f"Price ${_fmt_money(r['Price'])} • DPY ${_fmt_money(r.get('DPY'),0)} • "
#             f"COE left {_fmt_int(r.get('COE_Left_Months'))} m • "
#             f"Mileage {_fmt_int(r['Mileage_km'])} km • Owners {_fmt_int(r['Number_of_Previous_Owners'])}"
#         )
#         line3 = (
#             f"Reg {_fmt_dt(r['Registration_Date'], ym=True)} • "
#             f"COE Exp {_fmt_dt(r['COE_Expiry_Date'], ym=True)} • "
#             f"Posted {_fmt_int(r['Freshness_Days'])} d ago • {specs} • {r.get('Website') or '—'}"
#         )
#         print(line1)
#         print(line2)
#         print(line3)
#         print(f"URL: {r['URL']}")
#         print("-"*100)

# def pretty_df(d: pd.DataFrame, keep_raw: bool = True, only_pretty: bool = False) -> pd.DataFrame:
#     """
#     Return a DataFrame with human-friendly display columns added (vectorized).
#     - keep_raw=True keeps original typed columns alongside pretty strings.
#     - only_pretty=True returns only the curated pretty/display columns.
#     """
#     df = d.copy()

#     # ---- Vectorized helpers ----
#     def fmt_money_series(s: pd.Series, dp=0):
#         s = pd.to_numeric(s, errors="coerce")
#         return s.apply(lambda x: f"{x:,.{dp}f}" if pd.notna(x) and np.isfinite(x) else " ")

#     def fmt_int_series(s: pd.Series):
#         s = pd.to_numeric(s, errors="coerce")
#         return s.apply(lambda x: f"{int(x):,}" if pd.notna(x) and np.isfinite(x) else " ")

#     def fmt_dt_ym_series(s: pd.Series):
#         s = pd.to_datetime(s, errors="coerce")
#         return s.dt.strftime("%Y-%m").fillna(" ")

#     # ---- Derived display columns ----
#     title = (df["Brand"].fillna("") + " " + df["Make"].fillna("")).str.strip()

#     df["Title"]         = title
#     df["Price_str"]     = "S$" + fmt_money_series(df["Price"], dp=0)
#     df["DPY_str"]       = "S$" + fmt_money_series(df["DPY"], dp=0)
#     df["DPM_str"]       = "S$" + fmt_money_series(df["DPM"], dp=0)
#     df["COE_Left_str"]  = fmt_int_series(df["COE_Left_Months"]//12) + " yrs " + fmt_int_series(df["COE_Left_Months"]%12) + " mths"
#     df["Mileage_str"]   = fmt_int_series(df["Mileage_km"]) + " km"
#     df["Owners_str"]    = fmt_int_series(df["Number_of_Previous_Owners"])
#     df["Reg_ym"]        = fmt_dt_ym_series(df["Registration_Date"])
#     df["COE_Exp_ym"]    = fmt_dt_ym_series(df["COE_Expiry_Date"])
#     df["Posted_str"]    = fmt_int_series(df["Freshness_Days"]) + " d ago"

#     # Optional curated order for the top (pretty) block
#     pretty_cols = [
#         "Title", "Price_str", "DPY_str", "DPM_str", "COE_Left_str",
#         "Mileage_str", "Owners_str", "Reg_ym", "COE_Exp_ym", "Posted_str",
#         "COE_Category", "Fuel_Type", "Transmission", "Website", "URL"
#     ]

#     if only_pretty:
#         # Only pretty block (good for a simple UI table)
#         return df[pretty_cols]

#     if keep_raw:
#         # Put pretty block first, then raw columns (dedup while preserving order)
#         # Keep all existing columns after pretty block
#         raw_cols = [c for c in df.columns if c not in pretty_cols]
#         ordered = pretty_cols + raw_cols
#         return df[ordered]

#     # If not keeping raw, but also not only_pretty, return pretty plus a few key raw fields
#     minimal_raw = [
#         "Price", "DPY", "DPM", "COE_Left_Months", "Mileage_km",
#         "Number_of_Previous_Owners", "Registration_Date", "COE_Expiry_Date",
#         "Freshness_Days"
#     ]
#     keep_cols = pretty_cols + [c for c in minimal_raw if c in df.columns]
#     return df[keep_cols]

# # ===============================
# # 4) Sold Checker
# # ===============================
# _HEADERS = {
#     "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
#                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
# }
# _TIMEOUT = 10

# # sgcarmart sold checker
# def _check_sgcarmart(url: str) -> tuple[bool, str]:
#     def extract_json(script: str):
#         start = script.find('{')
#         if start == -1:
#             return None
#         depth = 0
#         for i, ch in enumerate(script[start:], start=start):
#             if ch == '{':
#                 depth += 1
#             elif ch == '}':
#                 depth -= 1
#                 if depth == 0:
#                     return script[start:i+1]
#         return None

#     try:
#         r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
#         if r.status_code in (404, 410):
#             return (True, f"HTTP {r.status_code}")
#         html = r.text
#         soup = BeautifulSoup(html, "html.parser")
#         scripts = [s.string for s in soup.find_all("script") if s.string]

#         for script in scripts:
#             if script and "infoUrlData" in script[:100]:
#                 cleaned = script.encode("utf-8").decode("unicode_escape")
#                 cleaned = extract_json(cleaned)
#                 if not cleaned:
#                     break
#                 data = json.loads(cleaned)
#                 status = data["ucInfoDetailData"]["data"]["status"]
#                 if status == "Available for sale":
#                     return (False, "JSON: Available for sale")
#                 elif status in ("SOLD", "Expired"):
#                     return (True, "JSON: Sold/Expired/Unknown")
#                 else:
#                     return (False, f"Unknown status for {url}: {status}")
#     except Exception as e:
#         return (False, f"Fetch error: {e.__class__.__name__}")

# # motorist sold checker
# def _check_motorist(url: str) -> tuple[bool, str]:
#     SOLD_RE = re.compile(r'^\s*Vehicle\s+Sold\s*$', re.I)
#     try:
#         r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT, allow_redirects=True)
#         if r.status_code in (404, 410):
#             return (True, f"HTTP {r.status_code}")
#         soup = BeautifulSoup(r.text, "html.parser")
#         # EXACT badge/text match, same as extract_sold_flag()
#         if soup.find(string=SOLD_RE):
#             return (True, "Badge: Vehicle Sold")
#         # Optional: also check sidebar block, like your helper does
#         seller_hdr = soup.find(string=re.compile(r'^\s*Seller Information\s*$', re.I))
#         if seller_hdr:
#             sidebar = seller_hdr.find_parent(['aside','section','div','article'])
#             if sidebar and sidebar.find(string=SOLD_RE):
#                 return (True, "Badge: Vehicle Sold (sidebar)")
#         # Otherwise treat as available (unsold), same as original
#         return (False, "Available (no Vehicle Sold badge)")
#     except Exception as e:
#         # Lazy default: don’t flip to sold on errors
#         return (False, f"Fetch error: {e.__class__.__name__}")

# # carro sold checker
# def _check_carro(url: str) -> tuple[bool|None, str]:
#     try:
#         r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT, allow_redirects=True)
#         if r.status_code in (404, 410):
#             return (True, f"HTTP {r.status_code}")
#         soup = BeautifulSoup(r.text, "html.parser")
#         hdr = soup.select_one("div.styles__StyledStatusHeader-sc-7efdfd35-5")
#         if hdr:
#             status_text = hdr.get_text(strip=True)
#             if status_text in {"Sold", "Pending Sale", "Reserved", "On Hold"}:
#                 return (True, f"Badge: {status_text}")
#         return (False, "Looks active")
#     except Exception as e:
#         return (False, f"Fetch error: {e.__class__.__name__}")

# def sold_checker(website_df: pd.DataFrame):
#     """
#     Takes your (already filtered) top-N DataFrame and returns (unsold_df, sold_df).
#     Does NOT modify any files; just checks synchronously and splits.
#     """
#     gcs_df = _download_from_gcs("final_dashboard_data", subdir="final_datasets")
#     gcs_df["Sold"] = gcs_df["Sold"].astype(bool)
#     gcs_df["URL"]  = gcs_df["URL"].astype(str)
#     if website_df.empty:
#         return website_df.copy(), website_df.copy()

#     unsold_rows = []
#     sold_count = 0

#     for _, r in website_df.iterrows():
#         url = r.get("URL","")
#         site = r.get("Website","")

#         # pick checker by site/host
#         if site.lower() in ("sgcarmart.com",):
#             is_sold, reason = _check_sgcarmart(url)
#         elif site.lower() in ("motorist.sg",):
#             is_sold, reason = _check_motorist(url)
#         elif site.lower() in ("carro.co",):
#             is_sold, reason = _check_carro(url)
#         else:
#             try:
#                 resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT, allow_redirects=True)
#                 is_sold = resp.status_code in (404,410)
#                 reason  = f"HTTP {resp.status_code}"
#             except Exception as e:
#                 is_sold, reason = None, f"Fetch error: {e.__class__.__name__}"

#         # tiny courtesy pause to avoid hammering
#         time.sleep(0.15)

#         # default inconclusive → treat as unsold (lazy checker)
#         row = r.copy()
#         # row["Sold_Check_Reason"] = reason
#         if is_sold is True:
#             sold_count += 1
#             gcs_df.loc[gcs_df["URL"].eq(str(url)), "Sold"] = True
#         else:
#             unsold_rows.append(row)

#     unsold_df = pd.DataFrame(unsold_rows, columns=list(website_df.columns)) if unsold_rows else website_df.iloc[0:0].copy()
#     print(f"Sold Car Listings Updated: {sold_count}")
#     _upload_to_gcs(gcs_df, "final_dashboard_data", subdir="final_datasets")
#     return unsold_df
    


# if __name__ == "__main__":
#     # put your Example 1/2/3 demo runs here so they DON’T execute on import
#     # ===============================
#     # 5) Use it (pick filters & order)
#     # ===============================

#     # # Example 1: Cat A EVs under $90k, ≤1 owner, sort by DPY (top 20)
#     # view1 = filter_by(
#     #     dfp,
#     #     price_max=90000,
#     #     coe_cat_in=["A"],
#     #     fuel_in=["Electric"],
#     #     owners_max=1,
#     #     sold=False
#     # )
#     # out1 = order_by(view1, key="dpy_asc", limit=25)
#     # print("=== Example 1: Cat A EVs under $90k, ≤1 owner, DPY ascending ===")
#     # unsold_df = sold_checker(out1)
#     # final_df = pretty_df(unsold_df, keep_raw = True, only_pretty = False)
#     # save_to_csv(final_df) # Change to list to df

#     # # Example 2: Honda Fit, ≥48 months COE left, mileage highest first
#     # view2 = filter_by(
#     #     dfp,
#     #     brand_in=["Honda"],
#     #     make_contains="Fit",
#     #     coe_months_min=48,
#     #     sold=False
#     # )
#     # out2 = order_by(view2, key="mileage_desc", limit=25)
#     # print("=== Example 2: Honda Fit, ≥48 months COE left, mileage asscending ===")
#     # unsold_df = sold_checker(out2)
#     # final_df = pretty_df(unsold_df, keep_raw = True, only_pretty = False)
#     # save_to_csv(final_df)

#     # # Example 3: Fresh (≤14 days), any site, BestValue ranking
#     # view3 = filter_by(
#     #     dfp,
#     #     freshness_max=14,
#     #     sold=False
#     # )
#     # out3 = order_by(view3, key="best_value", limit=20)
#     # print("=== Example 3: Fresh listings (≤14d), Best Value ranking ===")
#     # unsold_df = sold_checker(out3)
#     # final_df = pretty_df(unsold_df, keep_raw = True, only_pretty = False)
#     # save_to_csv(final_df)
#     pass