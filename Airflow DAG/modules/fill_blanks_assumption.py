import pandas as pd
import numpy as np
from datetime import datetime
import os

COLUMN_ORDER = [
    "URL","Brand","Make","Price","Registration_Date","Sold","Number_of_Previous_Owners",
    "Mileage_km","Previous_COE","OMV","Road_Tax_Payable","COE_Expiry_Date","Transmission",
    "Fuel_Type","Engine_Capacity_cc","Horse_Power_kW","Scrape_Date","Posted_Date",
    "Vehicle_Age_Years","Vehicle_Age_Days","COE_Left_Days","COE_Category","COE_Cycles",
    "COE_Renewed","Stocks_Monthly_Avg","Quota_Current_COE","Bids_Success_Current_COE",
    "Bids_Received_Current_COE","Premium_Current_COE","Previous_COE_Per_Month_Remaining",
    "Current_COE_Per_Month_Remaining","Five_Year_COE","Classic_Car","Website"
]

DATE_COLS = [
    "Registration_Date", "Scrape_Date", "Posted_Date", "COE_Expiry_Date"
]

NUMERIC_COLS = [
    "Price","Mileage_km","Previous_COE","OMV","Road_Tax_Payable","Engine_Capacity_cc",
    "Horse_Power_kW","Vehicle_Age_Years","Vehicle_Age_Days","COE_Left_Days","COE_Cycles",
    "Stocks_Monthly_Avg","Quota_Current_COE","Bids_Success_Current_COE",
    "Bids_Received_Current_COE","Premium_Current_COE","Previous_COE_Per_Month_Remaining",
    "Current_COE_Per_Month_Remaining","Number_of_Previous_Owners"
]

BOOL_COLS = [
    "Sold","COE_Renewed","Five_Year_COE","Classic_Car"
]

CATEGORICAL_COLS = [
    "Fuel_Type","Transmission","COE_Category","Website","Brand","Make"
]

def _to_datetime(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce")

def _to_numeric(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")

def _to_bool_from_strings(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s
    m = s.astype(str).str.strip().str.lower()
    truthy = {"true","1","yes","y","t"}
    falsy  = {"false","0","no","n","f"}
    out = pd.Series(index=s.index, dtype="boolean")
    out[m.isin(truthy)] = True
    out[m.isin(falsy)]  = False
    return out.astype("boolean")

def coerce_schema(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    for c in DATE_COLS:
        if c in x.columns:
            x[c] = _to_datetime(x[c])
    for c in NUMERIC_COLS:
        if c in x.columns:
            x[c] = _to_numeric(x[c])
    for c in BOOL_COLS:
        if c in x.columns:
            x[c] = _to_bool_from_strings(x[c]).astype("bool")
    for c in CATEGORICAL_COLS:
        if c in x.columns:
            x[c] = x[c].astype("string").str.strip()
    return x

def fill_blanks_in_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fill in missing values for ML models
    """
    combined_df = coerce_schema(df)

    # Missing mileage: take average mileage for that registration year (assume similar age cars have similar mileage)
    if {"Mileage_km","Registration_Date"}.issubset(combined_df.columns):
        year = combined_df["Registration_Date"].dt.year
        combined_df["Mileage_km"] = combined_df["Mileage_km"].fillna(
            combined_df.groupby(year)["Mileage_km"].transform("mean")
        )
        # If a year has no mileage data at all, fall back to global mean
        combined_df["Mileage_km"] = combined_df["Mileage_km"].fillna(combined_df["Mileage_km"].mean())

    # Road Tax: take average road tax for that brand (assume similar car brands pay similar road tax)
    if {"Road_Tax_Payable","Brand"}.issubset(combined_df.columns):
        combined_df["Road_Tax_Payable"] = combined_df["Road_Tax_Payable"].fillna(
            combined_df.groupby("Brand")["Road_Tax_Payable"].transform("mean")
        )
        # Classic cars: flat 280
        if {"Classic_Car","Road_Tax_Payable"}.issubset(combined_df.columns):
            classic_mask = combined_df["Classic_Car"].astype("boolean")
            combined_df.loc[classic_mask, "Road_Tax_Payable"] = 280.0
        # If a brand has no road tax data at all, fall back to global mean
        combined_df["Road_Tax_Payable"] = combined_df["Road_Tax_Payable"].fillna(combined_df["Road_Tax_Payable"].mean())

    # if "Engine_Capacity_cc" in combined_df.columns:
    #     vc = combined_df["Engine_Capacity_cc"].value_counts(dropna=False)
    #     rare_caps = vc[vc == 1].index

    # For horsepower, we have to separate electric vehicles first as they do not depend on engine size
    if {"Horse_Power_kW","Fuel_Type"}.issubset(combined_df.columns):
        is_ev = combined_df["Fuel_Type"].astype("string").eq("Electric")
        ev = combined_df.loc[is_ev].copy()

        # Immediately take average horse power of brand, then global median as fallback
        if not ev.empty:
            ev["Horse_Power_kW"] = ev["Horse_Power_kW"].fillna(
                ev.groupby("Brand")["Horse_Power_kW"].transform("median")
            ).fillna(ev["Horse_Power_kW"].median())

        # For non-electric cars, horsepower typically scales with engine capacity
        non_ev = combined_df.loc[~is_ev].copy()

        if not non_ev.empty:
            # Fill missing values with average horsepower of other rows with exact engine capacity
            if "Engine_Capacity_cc" in non_ev.columns:
                non_ev["Horse_Power_kW"] = non_ev["Horse_Power_kW"].fillna(
                    non_ev.groupby("Engine_Capacity_cc")["Horse_Power_kW"].transform("median")
                )

                # If no exact engine capacity match found, we use bins
                bins = pd.cut(
                    non_ev["Engine_Capacity_cc"],
                    [0, 999, 1299, 1599, 1999, 2499, 2999, 1e9],
                    include_lowest=True
                )
                non_ev["Horse_Power_kW"] = non_ev["Horse_Power_kW"].fillna(
                    non_ev.groupby(bins, observed=True)["Horse_Power_kW"].transform("median")  # use median to account for extreme ends that can fault mean
                )

            # Fallback: by brand, then global means
            non_ev["Horse_Power_kW"] = non_ev["Horse_Power_kW"].fillna(
                non_ev.groupby("Brand")["Horse_Power_kW"].transform("median")
            ).fillna(non_ev["Horse_Power_kW"].median())

        combined_df.loc[non_ev.index, "Horse_Power_kW"] = non_ev["Horse_Power_kW"]
        combined_df.loc[ev.index,  "Horse_Power_kW"] = ev["Horse_Power_kW"]

    # Convert the 4 calculated columns to int
    int_cols = ["Mileage_km", "Road_Tax_Payable", "Horse_Power_kW"]
    for c in int_cols:
        if c in combined_df.columns:
            combined_df[c] = pd.to_numeric(combined_df[c], errors="coerce").round(0).astype("Int64")

    # Keep only your defined order
    keep_cols = [c for c in COLUMN_ORDER if c in combined_df.columns]
    combined_df = combined_df[keep_cols]
    save_to_csv(combined_df, filename=None)

    return combined_df

def save_to_csv(df, filename=None):
    os.makedirs("./final_datasets", exist_ok=True)
    if filename is None:
        filename = f"final_ml_datasets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join("final_datasets", filename)
    df.to_csv(filepath, index=False)
    print(f"Saved file: {filename}")