#retrieve data of newly registered vehicles from data.gov.sg
import requests
import pandas as pd

def get_annual_car_population():
    dataset_id = "d_20d3fc7f08caa581c5586df51a8993c5"
    base_url = "https://data.gov.sg/api/action/datastore_search"
    records = []
    offset = 0
    limit = 1000

    while True:
        url = f"{base_url}?resource_id={dataset_id}&limit={limit}&offset={offset}"
        response = requests.get(url)
        batch = response.json()['result']['records']
        if not batch:
            break
        records.extend(batch)
        offset += limit

    df_newly_registered_vehicles = pd.DataFrame(records)
    return df_newly_registered_vehicles

# df_newly_registered_vehicles = get_annual_car_population()
# print(df_newly_registered_vehicles.head())