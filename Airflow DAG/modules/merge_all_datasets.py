import pandas as pd
import numpy as np
import os
from datetime import datetime

def merge_all_datasets(car_df, coe_df, pqp_df, stock_df):
    # Get main car_df data
    car_df["_tmp_posted_dt"] = pd.to_datetime(car_df["Posted_Date"], errors="coerce")
    car_df["_tmp_posted_year"] = car_df["_tmp_posted_dt"].dt.year
    car_df["_tmp_posted_month"] = car_df["_tmp_posted_dt"].dt.month

    # Add COE_Start_date to COE
    _reg_dt = pd.to_datetime(car_df["Registration_Date"], errors="coerce")
    _left_days = pd.to_numeric(car_df["COE_Left_Days"], errors="coerce")
    car_df = car_df.drop(columns=["COE_Expiry_Date"])
    _today = pd.to_datetime(car_df["Scrape_Date"], errors="coerce")
    car_df["COE_Expiry_Date"] = pd.to_datetime(_today) + pd.to_timedelta(_left_days, unit="D")
    _start_10y = car_df["COE_Expiry_Date"] - pd.DateOffset(years=10)
    car_df["COE_Start_Date"] = pd.concat([_reg_dt.rename("reg"), _start_10y.rename("start")], axis=1).max(axis=1)
    car_df["COE_Start_Date_Five_Year"] = car_df["COE_Start_Date"] + pd.DateOffset(years=5)
    car_df["_tmp_coe_start_dt"] = pd.to_datetime(car_df["COE_Start_Date"], errors="coerce")
    car_df["_tmp_coe_start_year"] = car_df["_tmp_coe_start_dt"].dt.year
    car_df["_tmp_coe_start_month"] = car_df["_tmp_coe_start_dt"].dt.month
    car_df["_tmp_coe_start_five_year_dt"] = pd.to_datetime(car_df["COE_Start_Date_Five_Year"], errors="coerce")
    car_df["_tmp_coe_start_five_year_year"] = car_df["_tmp_coe_start_five_year_dt"].dt.year
    car_df["_tmp_coe_start_five_year_month"] = car_df["_tmp_coe_start_five_year_dt"].dt.month

    # Add stock df data
    stock_df["Year"] = pd.to_numeric(stock_df["Year"], errors="coerce").astype("Int64")
    stock_df["Month"] = pd.to_numeric(stock_df["Month"], errors="coerce").astype("Int64")
    stock_df["Average_Close"] = pd.to_numeric(stock_df["Average_Close"], errors="coerce")
    merged_df = car_df.merge(
        stock_df,
        how="left",
        left_on=["_tmp_posted_year", "_tmp_posted_month"],
        right_on=["Year", "Month"],
        validate="m:1"
    )
    if "Average_Close" in merged_df.columns:
        merged_df["Average_Close"] = (
            pd.to_numeric(merged_df["Average_Close"], errors="coerce")
              .round()
              .astype("Int64")
        )
    merged_df = merged_df.rename(columns={'Average_Close': 'Stocks_Monthly_Avg'})
    drop_cols = [c for c in ["Year", "Month"] if c in merged_df.columns]
    if drop_cols:
        merged_df = merged_df.drop(columns=drop_cols)

    # Add COE df data
    coe_copy = coe_df.copy()
    coe_copy["Bidding_Date"] = pd.to_datetime(coe_copy["Bidding_Date"], errors="coerce")
    coe_copy["Vehicle_Class"] = (coe_copy["Vehicle_Class"].astype("string").str.strip().str[-1:].str.upper())
    for num_col in ["Quota", "Bids_Success", "Bids_Received", "Premium"]:
        if num_col in coe_copy.columns:
            coe_copy[num_col] = pd.to_numeric(coe_copy[num_col], errors="coerce")
    left = merged_df[["COE_Category", "Posted_Date"]].copy()
    left["Posted_Date"] = pd.to_datetime(left["Posted_Date"], errors="coerce")
    left["Vehicle_Class"] = left["COE_Category"].astype("string").str.strip()
    left["__rowid__"] = merged_df.index
    out_parts = []
    for cls in left["Vehicle_Class"].dropna().unique():
        L = left[left["Vehicle_Class"] == cls].sort_values("Posted_Date")
        R = coe_copy[coe_copy["Vehicle_Class"] == cls].sort_values("Bidding_Date")
        if R.empty:
            tmp = L.copy()
            tmp[["Bidding_Date", "Quota", "Bids_Success", "Bids_Received", "Premium"]] = pd.NA
        else:
            tmp = pd.merge_asof(
                L,
                R[["Bidding_Date", "Quota", "Bids_Success", "Bids_Received", "Premium"]],
                left_on="Posted_Date",
                right_on="Bidding_Date",
                direction="backward",
                allow_exact_matches=True
            )
        out_parts.append(tmp)
    matched = pd.concat(out_parts, axis=0).set_index("__rowid__").sort_index()
    merged_df["Quota_Current_COE"] = pd.to_numeric(matched["Quota"], errors="coerce").astype("Int64")
    merged_df["Bids_Success_Current_COE"] = pd.to_numeric(matched["Bids_Success"], errors="coerce").astype("Int64")
    merged_df["Bids_Received_Current_COE"] = pd.to_numeric(matched["Bids_Received"], errors="coerce").astype("Int64")
    merged_df["Premium_Current_COE"] = pd.to_numeric(matched["Premium"], errors="coerce").astype("Int64")

    # First PQP for 10 Year data
    pqp_copy = pqp_df.copy()
    pqp_copy = pqp_copy.drop(columns=["PQP_Price_Five_Year"])
    pqp_copy["Month"] = pd.to_datetime(pqp_copy["Month"], errors="coerce")
    pqp_copy["year"] = pqp_copy["Month"].dt.year
    pqp_copy["month_num"] = pqp_copy["Month"].dt.month
    pqp_copy["Vehicle_Class"] = (pqp_copy["Vehicle_Class"].astype("string").str.rstrip().str[-1:].str.upper())
    merged_df = merged_df.merge(
        pqp_copy,
        how="left",
        left_on=["COE_Category", "_tmp_coe_start_year", "_tmp_coe_start_month"],
        right_on=["Vehicle_Class", "year", "month_num"],
        validate="m:1"
    )
    drop_cols = [c for c in ["year", "Month", "month_num", "Vehicle_Class", 
                             "_tmp_coe_start_dt", "_tmp_coe_start_year", "_tmp_coe_start_month"] if c in merged_df.columns]
    if drop_cols:
        merged_df = merged_df.drop(columns=drop_cols)
    # Next PQP for 5 Year data
    pqp_copy = pqp_df.copy()
    pqp_copy = pqp_copy.drop(columns=["PQP_Price_Ten_Year"])
    pqp_copy["Month"] = pd.to_datetime(pqp_copy["Month"], errors="coerce")
    pqp_copy["year"] = pqp_copy["Month"].dt.year
    pqp_copy["month_num"] = pqp_copy["Month"].dt.month
    pqp_copy["Vehicle_Class"] = (pqp_copy["Vehicle_Class"].astype("string").str.rstrip().str[-1:].str.upper())
    merged_df = merged_df.merge(
        pqp_copy,
        how="left",
        left_on=["COE_Category", "_tmp_coe_start_five_year_year", "_tmp_coe_start_five_year_month"],
        right_on=["Vehicle_Class", "year", "month_num"],
        validate="m:1"
    )
    drop_cols = [c for c in ["year", "Month", "month_num", "Vehicle_Class", 
                             "_tmp_coe_start_five_year_dt", "_tmp_coe_start_five_year_year", "_tmp_coe_start_five_year_month"] if c in merged_df.columns]
    if drop_cols:
        merged_df = merged_df.drop(columns=drop_cols)
    # Add the Most_Recent_COE_Price and the Five_Year_COE boolean
    _reg = pd.to_datetime(merged_df["Registration_Date"], errors="coerce")
    _start = pd.to_datetime(merged_df["COE_Start_Date"], errors="coerce")
    coe = pd.to_numeric(merged_df["COE"], errors="coerce")
    pqp10 = pd.to_numeric(merged_df["PQP_Price_Ten_Year"], errors="coerce")
    pqp5 = pd.to_numeric(merged_df["PQP_Price_Five_Year"], errors="coerce")
    is_renewal = _reg != _start
    cannot_be_five_year_renewal = pqp5.isna()
    within10 = (coe - pqp10).abs() <= 10
    within5 = (coe - pqp5 ).abs() <= 10
    classic = (coe - (pqp10 / 10)).abs() <= 10
    merged_df["Five_Year_COE"] = pd.Series(pd.NA, index=merged_df.index, dtype="boolean")
    merged_df["Classic_Car"] = pd.Series(pd.NA, index=merged_df.index, dtype="boolean")
    merged_df.loc[~is_renewal, "Five_Year_COE"] = False
    merged_df.loc[~is_renewal, "Classic_Car"] = False
    merged_df.loc[is_renewal & classic, "Classic_Car"] = True
    merged_df.loc[is_renewal & ~classic, "Classic_Car"] = False
    merged_df.loc[is_renewal & classic, "Five_Year_COE"] = False
    merged_df.loc[is_renewal & ~classic & cannot_be_five_year_renewal, "Five_Year_COE"] = False
    merged_df.loc[is_renewal & ~classic & ~cannot_be_five_year_renewal & within5,  "Five_Year_COE"] = True
    merged_df.loc[is_renewal & ~classic & ~cannot_be_five_year_renewal & within10, "Five_Year_COE"] = False
    # Now if the "Five_Year_COE" is still blank, check whether its closer to PQP of 10 years or 5 years
    mask_na = merged_df["Five_Year_COE"].isna()
    diff5  = (coe - pqp5).abs()
    diff10 = (coe - pqp10).abs()
    merged_df.loc[mask_na & (diff5 < diff10), "Five_Year_COE"] = True
    merged_df.loc[mask_na & (diff10 <= diff5), "Five_Year_COE"] = False

    # Drop temporary original column
    # drop_cols = [c for c in ["_tmp_posted_dt", "_tmp_posted_year", "_tmp_posted_month", 
    #                          "PQP_Price_Ten_Year", "PQP_Price_Five_Year",
    #                          "COE_Start_Date", "COE_Start_Date_Five_Year"] if c in merged_df.columns]
    drop_cols = [c for c in ["_tmp_posted_dt", "_tmp_posted_year", "_tmp_posted_month"] if c in merged_df.columns]
    if drop_cols:
        merged_df = merged_df.drop(columns=drop_cols)

    # Filter out COE_Left that is negative or 0
    merged_df["COE_Left_Days"] = pd.to_numeric(merged_df["COE_Left_Days"], errors="coerce")
    merged_df = merged_df[merged_df["COE_Left_Days"] > 0]

    # Add COE cost per remaining months data
    months_left = pd.to_numeric(merged_df["COE_Left_Days"], errors="coerce").div(30.4375).apply(np.ceil).clip(lower=1).astype("Int64")
    merged_df["Previous_COE_Per_Month_Remaining"] = pd.to_numeric(merged_df["COE"], errors="coerce").div(months_left).round().astype("Int64")
    merged_df["Current_COE_Per_Month_Remaining"] = pd.to_numeric(merged_df["Premium_Current_COE"], errors="coerce").div(months_left).round().astype("Int64")
    
    # Some small cleanups
    merged_df = merged_df.rename(columns={"COE":"Previous_COE"})
    merged_df["Horse_Power_kW"] = pd.to_numeric(merged_df["Horse_Power_kW"], errors="coerce").round(0).astype("Int64")

    # Sort Column Order
    column_order = [
        "URL",
        "Brand",
        "Make",
        "Price",
        "Registration_Date",
        "Sold",
        "Number_of_Previous_Owners",
        "Mileage_km",
        "Previous_COE",
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
        "Stocks_Monthly_Avg",
        "Quota_Current_COE",
        "Bids_Success_Current_COE",
        "Bids_Received_Current_COE",
        "Premium_Current_COE",
        "Previous_COE_Per_Month_Remaining",
        "Current_COE_Per_Month_Remaining",
        "Five_Year_COE",
        "Classic_Car",
        "Website"
    ]
    merged_df = merged_df[column_order]

    save_to_csv(merged_df, filename=None)
    return merged_df

def save_to_csv(df, filename=None):
    os.makedirs("./final_datasets", exist_ok=True)
    if filename is None:
        filename = f"final_dashboard_datasets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join("final_datasets", filename)
    df.to_csv(filepath, index=False)
    print(f"Saved file: {filename}")