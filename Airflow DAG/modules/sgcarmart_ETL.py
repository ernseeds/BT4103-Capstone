import os, re
from datetime import datetime
import numpy as np
import pandas as pd

def ETL_sgcarmart(df):
    #Standardise Headers
    df = df.rename(columns={"price":"Price",
                            "url": "URL",
                            "owners":"Number_of_Previous_Owners", 
                            "mileage":"Mileage_km",
                            "engine_cap":"Engine_Capacity_cc",
                            "arf":"ARF",
                            "coe":"COE",
                            "omv":"OMV",
                            "transmission":"Transmission",
                            "reg_date":"Registration_Date",
                            "coe_left":"COE_Left_Days",
                            "fuel_type":"Fuel_Type",
                            "road_tax":"Road_Tax_Payable",
                            "power":"Horse_Power_kW",
                            "date_scraped":"Scrape_Date",
                            "COE Amount":"COE",
                            "brand":"Brand",
                            "status":"Sold",
                            "posted_on":"Posted_Date",
                            "date_scraped":"Scrape_Date",}
    )
    #Standardise Transmission, Sold, Fuel_Type inputs
    df['Transmission'] = df['Transmission'].replace({
        'Auto': 'Automatic',
        'Manual': 'Manual'
    })
    df['Sold'] = df['Sold'].apply(lambda x: False if str(x).strip().lower() == 'available for sale' else True)
    df['Fuel_Type'] = df['Fuel_Type'].replace('Petrol-Electric', 'Hybrid')
    df['Fuel_Type'] = df['Fuel_Type'].replace(
        {r'(?i)^diesel.*$': 'Diesel'}, 
        regex=True
    )
    df['Fuel_Type'] = df['Fuel_Type'].replace('Petrol-Electric', 'Hybrid')

    #Extract just kW and remove bhp, convert to numeric (use to_numeric instead of astype(float) to avoid error if there are invalid values) 
    df['Horse_Power_kW'] = pd.to_numeric(
        df['Horse_Power_kW'].str.extract(r'([\d\.]+)\s*kW')[0],
        errors='coerce'
    )

    #Remove vans, trucks, buses
    exclude_types = ["BUS/MINI BUS", "TRUCK", "VAN"]
    df = df[~df['type_of_vehicle'].str.upper().isin(exclude_types)]

    #Remove columns that motorist and carro do not have
    df = df.drop(columns=["depreciation", 
                        "manufactured",
                        "dereg_value", 
                        "curb_weight",
                        "type_of_vehicle",
                        "original_reg_date",
                        "indicative_price",
                        "auction_closing",
                        "drive_range",
                        "lifespan",
                        "ARF"])

    #Extract Make (remove brand from front)
    df['Make'] = df.apply(
        lambda row: re.sub(rf'^{re.escape(str(row["Brand"]))}\s*', '', str(row["car_model"]), flags=re.I)
        if pd.notna(row["Brand"]) and pd.notna(row["car_model"]) else pd.NA,
        axis=1
    )

    #Remove units and convert to numeric
    money_cols = ['Price', 'COE', 'OMV']
    for col in money_cols:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(r'[\$,]', '', regex=True).str.strip(),
            errors='coerce'
        )

    #Drop rows where Price is NaN or 0
    df = df[df['Price'].notna() & (df['Price'] != 0)]

    #Drop rows where COE is missing as COE is important for analysis
    df = df.dropna(subset=['COE'])
    df = df[pd.to_numeric(df['COE'], errors='coerce').notna()]

    #Remove units, convert to numeric
    df['Road_Tax_Payable'] = clean_numeric_sgcarmart(df['Road_Tax_Payable'])
    df['Mileage_km'] = clean_numeric_sgcarmart(df['Mileage_km'], r'([\d,]+)')
    df['Engine_Capacity_cc'] = clean_numeric_sgcarmart(df['Engine_Capacity_cc'])
    df['Engine_Capacity_cc'] = df['Engine_Capacity_cc'].fillna(0) #any missing values become 0 
    df['Engine_Capacity_cc'] = df['Engine_Capacity_cc'].apply( #if human errors of using decimal instead of comma
        lambda x: int(x * 1000) if pd.notnull(x) and 0.5 <= x < 10 else int(x)
    )
    df['OMV'] = df['OMV'].fillna(0) #any missing values become 0 

    #Replace "more than 5" with 6, and convert to numeric 
    df['Number_of_Previous_Owners'] = df['Number_of_Previous_Owners'].apply(
        lambda x: 7 if str(x).strip().lower() == "more than 6"
        else pd.to_numeric(str(x).split()[0], errors='coerce')
    )
    df['Number_of_Previous_Owners'] = df['Number_of_Previous_Owners'].replace(0, 1)

    #Convert to datetime
    for col in ['Registration_Date', 'Scrape_Date', 'Posted_Date']:
        df[col] = clean_date_column(df, col)
    # df['Registration_Date'] = pd.to_datetime(df['Registration_Date'], format='%d-%b-%y', errors='coerce')
    df['Posted_Date'] = parse_date_multi(df['Posted_Date']).dt.normalize()
    df['Scrape_Date'] = parse_date_multi(df['Scrape_Date']).dt.normalize()
    df['Registration_Date'] = parse_date_multi(df['Registration_Date']).dt.normalize()

    #If any two-digit years were interpreted into the future, push them back 100 years
    today = pd.Timestamp.today().normalize()
    mask = df['Registration_Date'].dt.year > today.year
    df.loc[mask, 'Registration_Date'] = df.loc[mask, 'Registration_Date'] - pd.DateOffset(years=100)
    # df['Scrape_Date'] = pd.to_datetime(df['Scrape_Date'], dayfirst=True, errors='coerce')
    # df['Posted_Date'] = pd.to_datetime(df['Posted_Date'], format='%d-%b-%y', errors='coerce')
    
    #Calculate COE left to days 
    mask = df['COE_Left_Days'].astype('string').str.strip().str.fullmatch(r'(?:N\.?A\.?|NA|N\/A|--|-)')
    df.loc[mask, 'COE_Left_Days'] = pd.NA
    df = df.dropna(subset=['COE_Left_Days'])
    df['COE_Left_Days'] = df['COE_Left_Days'].apply(coe_left_to_days_sgcarmart)

    #Calculate COE Expiry Date
    df['COE_Expiry_Date'] = df['Scrape_Date'] + pd.to_timedelta(df['COE_Left_Days'])

    #New feature: Age of Vehicle
    today = pd.to_datetime(datetime.now().date())
    df['Vehicle_Age_Years'] = (((today - df['Registration_Date']).dt.days / 365.25)
                           .round().astype('Int64'))


    today = pd.Timestamp.today().normalize() #Strip away hours/minutes
    df['Vehicle_Age_Days'] = (today - df['Registration_Date']).dt.days #Days too to differentiate between less than 1 year old cars

    #New Feature: Number of COE cycles
    age_years_exact = (today - df['Registration_Date']).dt.days / 365.25
    cycles = np.floor(age_years_exact / 10).astype("Int64") + 1
    cycles = cycles.where(age_years_exact.notna(), pd.NA)

    #New Feature: COE Category
    df['Fuel_Type'] = df['Fuel_Type'].fillna('Petrol')
    df = coe_category_sgcarmart(df)

    #New Feature: Number of COE cycles
    df['COE_Cycles'] = pd.Series(cycles, index=df.index).astype('Int64')

    #New Feature: Binary indicator about whether the car has COE renewed
    df['COE_Renewed'] = df['COE_Cycles'].apply(lambda x: 'Y' if (pd.notna(x) and x > 1) else 'N')
    
    #New Feature: Website scrapped
    df['Website'] = "sgcarmart.com"

    #Only want the date, not the time
    # df['Registration_Date'] = df['Registration_Date'].dt.normalize()
    df['COE_Expiry_Date'] = df['COE_Expiry_Date'].dt.normalize()
    # df['Scrape_Date'] = df['Scrape_Date'].dt.normalize()
    # df['Posted_Date'] = df['Posted_Date'].dt.normalize()

    df = df.drop(columns=["car_model"])

    column_order = [
        "URL",
        "Brand",
        "Make",
        "Price",
        "Registration_Date",
        "Sold",
        "Number_of_Previous_Owners",
        "Mileage_km",
        "COE",
        "OMV",
        "Road_Tax_Payable",
        "COE_Expiry_Date",
        "Transmission",
        "Fuel_Type",
        "Engine_Capacity_cc",
        "Horse_Power_kW",
        "Scrape_Date",
        "Posted_Date",
        "Vehicle_Age_Years",
        "Vehicle_Age_Days",
        "COE_Left_Days",
        "COE_Category",
        "COE_Cycles",
        "COE_Renewed",
        "Website"
    ]
    df = df[column_order]
    save_to_csv(df, filename=None)

    return df

def coe_category_sgcarmart(df):
    # Helpers
    cut_2014 = pd.Timestamp("2014-02-01")
    cut_2022 = pd.Timestamp("2022-05-01")

    reg = pd.to_datetime(df["Registration_Date"], errors="coerce")
    is_ev = df["Fuel_Type"].astype(str).str.strip().eq("Electric")
    cc = pd.to_numeric(df["Engine_Capacity_cc"], errors="coerce")
    kw = pd.to_numeric(df["Horse_Power_kW"], errors="coerce")

    conditions = [
        # Pre-2014-02-01: cc rule only (no power cap), any fuel
        (reg < cut_2014) & (cc <= 1600),
        (reg < cut_2014) & (cc > 1600),
        # 2014-02-01 to 2022-04-30: EV 97 kW cap
        (reg >= cut_2014) & (reg < cut_2022) & is_ev & (kw <= 97),
        (reg >= cut_2014) & (reg < cut_2022) & is_ev & (kw > 97),
        # 2014-02-01 to 2022-04-30: Non-EV needs cc≤1600 AND kW≤97
        (reg >= cut_2014) & (reg < cut_2022) & (~is_ev) & (cc <= 1600) & (kw <= 97),
        (reg >= cut_2014) & (reg < cut_2022) & (~is_ev) & (~((cc <= 1600) & (kw <= 97))),
        # 2022-05-01 and later: EV 110 kW cap
        (reg >= cut_2022) & is_ev & (kw <= 110),
        (reg >= cut_2022) & is_ev & (kw > 110),
        # 2022-05-01 and later: Non-EV unchanged (cc≤1600 AND kW≤97)
        (reg >= cut_2022) & (~is_ev) & (cc <= 1600) & (kw <= 97),
        (reg >= cut_2022) & (~is_ev) & (~((cc <= 1600) & (kw <= 97))),
    ]
    categories = ['A','B','A','B','A','B','A','B','A','B']

    df['COE_Category'] = np.select(conditions, categories, default='A')
    return df

def clean_numeric_sgcarmart(series, regex=r'([\d,\.]+)'):
    return pd.to_numeric(
        series.astype(str)
              .str.extract(regex)[0]
              .str.replace(',', '', regex=False),
        errors='coerce'
    )

def coe_left_to_days_sgcarmart(text):
    if pd.isna(text):
        return None
    match = re.match(r'(?:(\d+)\s*y)?\s*(?:(\d+)\s*m)?\s*(?:(\d+)\s*d)?', str(text).lower())
    if not match:
        return None
    yrs, mths, days = match.groups(default='0')
    total_days = int(yrs) * 365 + int(mths) * 30 + int(days)
    return total_days

def clean_date_column(df, colname):
    return (
        df[colname]
        .astype(str)
        .str.replace('\u00A0', ' ', regex=False)            # standardise spaces
        .str.replace(r'[\u2010-\u2015\u2212]', '-', regex=True)  # standardise dashes
        .str.replace(r'\bSept\b', 'Sep', regex=True)
        .str.strip()
    )

def parse_date_multi(series):
    s = series.astype(str).str.strip()

    # 1) ISO: 2025-10-17
    dt = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")

    # 2) DD-Mon-YYYY: 17-Oct-2025
    m = dt.isna()
    if m.any():
        dt.loc[m] = pd.to_datetime(s[m], format="%d-%b-%Y", errors="coerce")

    # 3) DD-Mon-YY: 17-Oct-05
    m = dt.isna()
    if m.any():
        dt.loc[m] = pd.to_datetime(s[m], format="%d-%b-%y", errors="coerce")

    # 4) Fallback for DD/MM/YYYY or DD-MM-YYYY, etc.
    m = dt.isna()
    if m.any():
        dt.loc[m] = pd.to_datetime(s[m], dayfirst=True, errors="coerce")

    return dt

    # # #New Feature: COE_5_Years (binary indicator about whether the car is in the 5-year COE category)
    # # year_diff = (df['COE_Expiry_Date'].dt.year - df['Registration_Date'].dt.year) 
    # # #1 if 5–7 years, else 0
    # # df['COE_5_Years'] = np.where((year_diff >= 5) & (year_diff <= 7), 1, 0)

def save_to_csv(df, filename=None):
    os.makedirs("./cleaned_datasets", exist_ok=True)
    if filename is None:
        filename = f"sgcarmart_cleaned_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join("cleaned_datasets", filename)
    df.to_csv(filepath, index=False)
    print(f"Saved file: {filename}")

# ETL_sgcarmart(pd.read_csv('datasets_sgcarmart.csv'))