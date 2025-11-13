import os, re
from datetime import datetime
import numpy as np
import pandas as pd

def ETL_motorist(df,brands_list):
    #Standardise Headers
    df = df.rename(columns={"url": "URL",
                            "Ownership":"Number_of_Previous_Owners", 
                            "price":"Price", 
                            "Registration Date":"Registration_Date",
                            "Road Tax Payable":"Road_Tax_Payable",
                            "COE Expiry Date":"COE_Expiry_Date",
                            "Fuel Type":"Fuel_Type",
                            "Engine Capacity":"Engine_Capacity_cc",
                            "Power":"Horse_Power_kW",
                            "Mileage":"Mileage_km",
                            "scrape_date":"Scrape_Date",
                            "Status":"Sold",
                            "Posted Date":"Posted_Date",})
    #Standardise Transmission, Sold, Fuel_Type inputs
    df['Sold'] = ~df['Sold'].eq('Available')
    df['Transmission'] = df['Transmission'].replace({
        'Auto': 'Automatic',
        'Manual': 'Manual'
    })
    df['Fuel_Type'] = df['Fuel_Type'].replace('Petrol-Electric', 'Hybrid')
    df['Fuel_Type'] = df['Fuel_Type'].replace('Petrol-Electric (Plug-In)', 'Hybrid')

    #Extract just kW and remove bhp, convert to numeric (use to_numeric instead of astype(float) to avoid error if there are invalid values) 
    df['Horse_Power_kW'] = pd.to_numeric(
        df['Horse_Power_kW'].str.extract(r'([\d\.]+)\s*kW')[0],
        errors='coerce'
    )

    #Remove columns that carro and sgcarmart do not have
    df = df.drop(columns=["Veh. Scheme", "Paper Value", "Primary Colour", 
                          "PARF Expiry Date", "Manufacturing Year",
                          "Road Tax Expiry Date", "Min. PARF",
                          "listing_id","ARF"])

    cleaned_brands_list = [
        re.sub(r'\s+', '',
            re.sub(r'[\.\-]', '', str(b).upper().replace('\u00A0', ''))  
            ).strip()
        for b in brands_list
    ]

    df['title_cleaned'] = (
        df['title'].astype(str)
        .str.upper()
        .str.replace('\u00A0', '', regex=False)
        .str.replace(r'[\.\-]', '', regex=True)
        .str.replace(r'\s+', '', regex=True)
        .str.strip()
    )

    df['Brand'] = pd.NA
    for brand_clean, brand_orig in zip(cleaned_brands_list, brands_list):
        mask = df['title_cleaned'].str.startswith(brand_clean, na=False)
        df.loc[mask, 'Brand'] = brand_orig

    #Fallback: if Brand still missing, take first word
    df['Brand'] = df['Brand'].fillna(df['title'].str.split().str[0].str.upper())

    #Extract Make (remove brand from front)
    df['Make'] = df.apply(
        lambda row: row['title'][len(row['Brand']):].strip() if pd.notnull(row['Brand']) else row['title'],
        axis=1
    )

    #Declare so pandas does not get confused with Makes that are just numbers 
    df['Make'] = df['Make'].astype(str)

    #Remove rows of vans and trucks
    df = df[~df['Make'].str.contains(r'\b(?:TRUCK|TRUCKS|VAN|BUS)\b', case=False, regex=True)]

    #Remove truck brands 
    truck_brands = {"HINO", "HIGER", "ISUZU", "KYC", "MAN", "SOKON","FARIZON","SRM","SHINERAY","DFSK","FOTON","GOLDEN DRAGON","LEX BUILD"}
    remove_trucks = df['Brand'].str.upper().apply(lambda x: any(tb in x for tb in truck_brands))
    df = df[~remove_trucks]

    #Remove "COE Till" and "New 10-yr COE"
    df['Make'] = df['Make'].str.replace(r'\s*\(COE TILL .*?\)', '', regex=True).str.strip()
    df['Make'] = df['Make'].str.replace(r'\s*\(COE till .*?\)', '', regex=True).str.strip()
    df['Make'] = df['Make'].str.replace(r'\s*\((NEW 10-YR COE)\)', '', regex=True).str.strip()
    df['Make'] = df['Make'].str.replace(r'\s*\((New 10-yr COE)\)', '', regex=True).str.strip()

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
    df['Road_Tax_Payable'] = clean_numeric_motorist(df['Road_Tax_Payable'])
    df['Mileage_km'] = clean_numeric_motorist(df['Mileage_km'], r'([\d,]+)')
    df['Engine_Capacity_cc'] = clean_numeric_motorist(df['Engine_Capacity_cc'], r'(\d+)')
    df['Engine_Capacity_cc'] = df['Engine_Capacity_cc'].fillna(0) #any missing values become 0 
    df['Engine_Capacity_cc'] = df['Engine_Capacity_cc'].apply( #if human errors of using decimal instead of comma
        lambda x: int(x * 1000) if pd.notnull(x) and 0.5 <= x < 10 else int(x)
    )
    df['OMV'] = df['OMV'].fillna(0) #any missing values become 0 

    #Replace "more than 5" with 6, and convert to numeric 
    df['Number_of_Previous_Owners'] = df['Number_of_Previous_Owners'].apply(
        lambda x: 6 if x == "More than 5" else pd.to_numeric(x, errors='coerce')
    )
    #If 0, replace with 1 
    df['Number_of_Previous_Owners'] = df['Number_of_Previous_Owners'].replace(0, 1)

    #Convert all dates to datetime
    df['Registration_Date'] = pd.to_datetime(df['Registration_Date'], format='%d/%m/%Y', errors='coerce')

    #If any two-digit years were interpreted into the future, push them back 100 years
    today = pd.Timestamp.today().normalize()
    mask = df['Registration_Date'].dt.year > today.year
    df.loc[mask, 'Registration_Date'] = df.loc[mask, 'Registration_Date'] - pd.DateOffset(years=100)    
    df['COE_Expiry_Date'] = df['COE_Expiry_Date'].str[:10] #Remove "remaining COE left" as it is only from day of web scrapping
    df['COE_Expiry_Date'] = pd.to_datetime(df['COE_Expiry_Date'], format='%d/%m/%Y', errors='coerce')
    df['Scrape_Date'] = pd.to_datetime(df['Scrape_Date'], errors='coerce')
    df['Posted_Date'] = pd.to_datetime(df['Posted_Date'], errors='coerce')

    #New feature: COE left
    df = df.dropna(subset=['COE_Expiry_Date'])
    df['COE_Left_Days'] = (df['COE_Expiry_Date'] - today).dt.days.astype('Int64')

    #New feature: Age of Vehicle
    today = pd.to_datetime(datetime.now().date())
    df['Vehicle_Age_Years'] = (
        ((today - df['Registration_Date']).dt.days / 365.25)
        .round()
        .astype('Int64')
    )
    today = pd.Timestamp.today().normalize() #Strip away hours/minutes
    df['Vehicle_Age_Days'] = (today - df['Registration_Date']).dt.days #Days too to differentiate between less than 1 year old cars

    #New Feature: COE Category 
    df = coe_category_motorist(df)

    #New Feature: Number of COE cycles 
    age_years_exact = (today - df['Registration_Date']).dt.days / 365.25
    cycles = np.floor(age_years_exact / 10).astype("Int64") + 1
    cycles = cycles.where(age_years_exact.notna(), pd.NA)

    df['COE_Cycles'] = pd.Series(cycles, index=df.index).astype('Int64')

    #New Feature: Binary indicator about whether the car has COE renewed
    df['COE_Renewed'] = df['COE_Cycles'].apply(lambda x: 'Y' if (pd.notna(x) and x > 1) else 'N')

    #New Feature: Website scrapped
    df['Website'] = "Motorist.sg"

    df = df.drop(columns=['title_cleaned'])
    # pd.set_option('display.max_columns', None)   # show all columns
    # print(df.head())


   #Only want the date, not the time
    # df['Registration_Date'] = df['Registration_Date'].dt.normalize()
    # df['Scrape_Date'] = (pd.to_datetime(df['Scrape_Date'], errors='coerce')).dt.normalize()
    # df['COE_Expiry_Date'] = df['COE_Expiry_Date'].dt.normalize()
    # df['Posted_Date'] = df['Posted_Date'].dt.normalize()

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

    #Save to Excel
    #df.to_excel("cleaned_motorist_data.xlsx", index=False)
    # df.to_csv("cleaned_motorist_data.csv", index=False, encoding="utf-8-sig")
    save_to_csv(df, filename=None)

    return df

def coe_category_motorist(df):
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

#Remove units and convert to numeric
def clean_numeric_motorist(series, regex=r'([\d,\.]+)'):
    return pd.to_numeric(
        series.astype(str)
              .str.extract(regex)[0]
              .str.replace(',', '', regex=False),
        errors='coerce'
    )
    # #New Feature: COE_5_Years (binary indicator about whether the car is in the 5-year COE category)
    # year_diff = (df['COE_Expiry_Date'].dt.year - df['Registration_Date'].dt.year) 
    # df['COE_5_Years'] = np.where((year_diff >= 5) & (year_diff <= 7), 1, 0)

def save_to_csv(df, filename=None):
    os.makedirs("./cleaned_datasets", exist_ok=True)
    if filename is None:
        filename = f"motorist_cleaned_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join("cleaned_datasets", filename)
    df.to_csv(filepath, index=False)
    print(f"Saved file: {filename}")
# brands_list = pd.read_csv('datasets_sgcarmart.csv')['brand'].dropna().str.strip().unique().tolist()
# ETL_motorist(pd.read_csv('datasets_motorist.csv'), brands_list)