import pandas as pd
import os
from datetime import datetime

def merge_car_datasets(df_sgcarmart, df_motorist, df_carro):
    #Standardize columns
    common_columns = list(set(df_sgcarmart.columns) & set(df_motorist.columns) & set(df_carro.columns))
    df_sgcarmart = df_sgcarmart[common_columns]
    df_motorist = df_motorist[common_columns]
    df_carro = df_carro[common_columns]

    #Merge all into one DataFrame
    combined_df = pd.concat([df_sgcarmart, df_motorist, df_carro], ignore_index=True)

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
    combined_df = combined_df[column_order]

    #Convert all to appropriate dtypes
    cat_cols = ["Brand","Make","Transmission","Fuel_Type","COE_Category","Website", "URL"]
    for c in cat_cols:
        combined_df[c] = combined_df[c].astype("string").str.strip()
    combined_df["COE_Renewed"] = (
        combined_df["COE_Renewed"]
        .astype("string").str.strip().str.upper()
        .map({"Y": True, "N": False})
    )

    #Save file as csv
    save_to_csv(combined_df, filename=None)

    return combined_df

def save_to_csv(df, filename=None):
    os.makedirs("./combined_datasets", exist_ok=True)
    if filename is None:
        filename = f"combined_car_datasets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join("combined_datasets", filename)
    df.to_csv(filepath, index=False)
    print(f"Saved file: {filename}")