import os, re
import pandas as pd
from airflow.exceptions import AirflowSkipException
from airflow.decorators import dag, task
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.providers.google.cloud.hooks.bigquery import BigQueryHook
from datetime import datetime, timedelta
from apis.carro_scrape import get_carro_data
from apis.sgcarmart_scrape import get_sgcarmart_data
from apis.motorist_new_listings import get_updated_motorist_data
from apis.motorist_webscraping import get_motorist_data
from apis.annual_car_population_api import get_annual_car_population
from apis.coe_api import get_coe_dataset
from apis.stock_api import get_stock_data
from modules.sgcarmart_ETL import ETL_sgcarmart
from modules.carro_ETL import ETL_carro
from modules.motorist_ETL import ETL_motorist
from modules.get_coe_forecast import get_coe_forecast
from modules.merge_car_datasets import merge_car_datasets
from modules.merge_all_datasets import merge_all_datasets
from modules.sold_checker import run_sold_check
from modules.fill_blanks_assumption import fill_blanks_in_df

PROJECT_ID = "car-resale-capstone"
BQ_DATASET = "car_resale_bigquery"
GCS_BUCKET_NAME = "car-resale-bucket"
GCP_CONN_ID = "google_cloud_default"
BQ_LOCATION = "asia-southeast1"

DATA_DIR = "datasets"
TEMP_DIR = "temporary"

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2025, 1, 1),
    'retries': 3, 
    'retry_delay': timedelta(minutes=5),  
    'email': ['Jevan.Koh@u.nus.edu', 'xiangjunooi@u.nus.edu', 'charlenetan2003@gmail.com', 'ernsee2208@gmail.com', 'xanelletanls@gmail.com', 'peckernwen@gmail.com'],
    'email_on_failure': True, 
    'email_on_retry': False, 
}

# =========================
# GCS HELPERS
# =========================
def _gcs_hook():
    return GCSHook(gcp_conn_id=GCP_CONN_ID)

def _upload_to_gcs(df: pd.DataFrame, name: str, subdir: str = DATA_DIR):
    os.makedirs(subdir, exist_ok=True)
    local_path = f"{subdir}/{name}.csv"
    gcs_path   = f"{subdir}/{name}.csv"
    df.to_csv(local_path, index=False)
    try:
        _gcs_hook().upload(bucket_name=GCS_BUCKET_NAME, object_name=gcs_path, filename=local_path)
        print(f"Uploaded {name}.csv → gs://{GCS_BUCKET_NAME}/{gcs_path}")
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)
            print(f"Deleted local file: {local_path}")
        if os.path.isdir(subdir) and not os.listdir(subdir):
            os.rmdir(subdir)
            print(f"Deleted empty folder: {subdir}")

def _download_from_gcs(name: str, subdir: str = DATA_DIR) -> pd.DataFrame:
    gcs_path   = f"{subdir}/{name}.csv"
    local_path = f"{subdir}/{name}.csv"
    os.makedirs(subdir, exist_ok=True)
    hook = _gcs_hook()
    try:
        hook.download(bucket_name=GCS_BUCKET_NAME, object_name=gcs_path, filename=local_path)
        print(f"Downloaded {gcs_path} → {local_path}")
        df = pd.read_csv(local_path)
        print(f"Loaded {len(df)} rows from {name}.csv")
        return df
    except Exception as e:
        print(f"No existing {gcs_path} found in GCS — returning empty DataFrame. ({e})")
        return pd.DataFrame()
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)
            print(f"Deleted local file: {local_path}")
        if os.path.isdir(subdir) and not os.listdir(subdir):
            os.rmdir(subdir)
            print(f"Deleted empty folder: {subdir}")

def _gcs_to_bq_task(task_id: str, source_objects, table_name: str, write_disposition: str = "WRITE_TRUNCATE",
                    autodetect: bool = True, skip_leading_rows: int = 1):
    return GCSToBigQueryOperator(
        task_id=task_id,
        bucket=GCS_BUCKET_NAME,
        source_objects=source_objects if isinstance(source_objects, list) else [source_objects],
        destination_project_dataset_table=f"{PROJECT_ID}.{BQ_DATASET}.{table_name}",
        source_format="CSV",
        autodetect=autodetect,
        write_disposition=write_disposition,
        skip_leading_rows=skip_leading_rows,
        allow_quoted_newlines=True,
        gcp_conn_id=GCP_CONN_ID,
        location=BQ_LOCATION
    )

@dag(
    dag_id='car_resale_dag',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False,
    tags=['car-resale-capstone']
)

def my_dag():
    @task
    def start_DAG():
        print("Starting DAG!")

    @task
    def extract_coe():
        coe_df, pqp_df = get_coe_dataset()
        _upload_to_gcs(coe_df, "coe")
        _upload_to_gcs(pqp_df, "pqp")
    
    @task
    def extract_car_population():
        df = get_annual_car_population()
        _upload_to_gcs(df, "carpopulation")
    
    @task
    def extract_stock():
        df = get_stock_data()
        _upload_to_gcs(df, "stock")

    @task
    def extract_motorist():
        prev_df = _download_from_gcs("motorist")
        if prev_df.empty:
            df = get_motorist_data()
            if df.empty:
                raise AirflowSkipException("Motorist: no data collected (full scrape).")
            print(f"Motorist full scrape: {len(df)} rows.")
        else:
            df = get_updated_motorist_data(prev_df)
            if df.empty:
                raise AirflowSkipException("Motorist: no data collected (incremental).")
            print(f"Motorist incremental: now {len(df)} rows total after merge.")
        _upload_to_gcs(df, "motorist")

    @task
    def extract_sgcarmart():
        prev_df = _download_from_gcs("sgcarmart")
        df = get_sgcarmart_data(prev_df)
        if df.empty:
            raise AirflowSkipException("Sgcarmart: no data collected.")
        _upload_to_gcs(df, "sgcarmart")

    @task
    def extract_carro():
        prev_df = _download_from_gcs("carro")
        df = get_carro_data(prev_df)
        if df.empty:
            raise AirflowSkipException("Carro: no data collected.")
        _upload_to_gcs(df, "carro")
    
    @task
    def extract_initial_data_from_gcs():
        filenames = ["motorist", "sgcarmart", "carro", "coe", "pqp", "carpopulation", "stock"]
        for name in filenames:
            df = _download_from_gcs(name)
            print(f"{name} data shape: {df.shape}")
        return "Extract from GCS completed."
    
    @task
    def clean_sgcarmart():
        prev_df = _download_from_gcs("sgcarmart", subdir="datasets")
        cleaned_df = ETL_sgcarmart(prev_df)
        _upload_to_gcs(cleaned_df, "sgcarmart_clean", subdir="cleaned_datasets")
        brands_list = cleaned_df['Brand'].dropna().unique().tolist()
        return brands_list

    @task
    def clean_motorist(brands_list):
        prev_df = _download_from_gcs("motorist", subdir="datasets")
        cleaned_df = ETL_motorist(prev_df, brands_list)
        _upload_to_gcs(cleaned_df, "motorist_clean", subdir="cleaned_datasets")
    
    @task
    def clean_carro(brands_list):
        prev_df = _download_from_gcs("carro", subdir="datasets")
        cleaned_df = ETL_carro(prev_df, brands_list)
        _upload_to_gcs(cleaned_df, "carro_clean", subdir="cleaned_datasets")
    
    @task
    def coe_forecast():
        prev_df = _download_from_gcs("coe", subdir="datasets")
        final_df = get_coe_forecast(prev_df)
        _upload_to_gcs(final_df, "final_coe_data", subdir="final_datasets")
    
    @task
    def merge_car_data():
        sgcarmart_df = _download_from_gcs("sgcarmart_clean", subdir="cleaned_datasets")
        carro_df = _download_from_gcs("carro_clean", subdir="cleaned_datasets")
        motorist_df = _download_from_gcs("motorist_clean", subdir="cleaned_datasets")
        combined_cars_df = merge_car_datasets(sgcarmart_df, motorist_df, carro_df)
        _upload_to_gcs(combined_cars_df, "combined_car_data", subdir="combined_datasets")

    @task
    def merge_all_data():
        car_df = _download_from_gcs("combined_car_data", subdir="combined_datasets")
        coe_df = _download_from_gcs("coe", subdir="datasets")
        pqp_df = _download_from_gcs("pqp", subdir="datasets")
        stock_df = _download_from_gcs("stock", subdir="datasets")
        combined_all_df = merge_all_datasets(car_df, coe_df, pqp_df, stock_df)
        _upload_to_gcs(combined_all_df, "final_dashboard_data", subdir="final_datasets")

    @task
    def run_sold_checker():
        unclean_df = _download_from_gcs("final_dashboard_data", subdir="final_datasets")
        sgcarmart_df = _download_from_gcs("sgcarmart", subdir="datasets")
        motorist_df = _download_from_gcs("motorist", subdir="datasets")
        carro_df = _download_from_gcs("carro", subdir="datasets")
        clean_df, updated_sgcarmart_df, updated_motorist_df, updated_carro_df = run_sold_check(unclean_df, sgcarmart_df, motorist_df, carro_df)
        _upload_to_gcs(clean_df, "final_dashboard_data", subdir="final_datasets")
        _upload_to_gcs(updated_sgcarmart_df, "sgcarmart", subdir="datasets")
        _upload_to_gcs(updated_motorist_df, "motorist", subdir="datasets")
        _upload_to_gcs(updated_carro_df, "carro", subdir="datasets")

    @task
    def all_data_with_blanks_filled():
        df_with_blanks = _download_from_gcs("final_dashboard_data", subdir="final_datasets")
        df_with_blanks_filled = fill_blanks_in_df(df_with_blanks)
        _upload_to_gcs(df_with_blanks_filled, "final_ml_data", subdir="final_datasets")
    
    # Initializing DAG
    start_DAG_task = start_DAG()

    # Extracting datasets using APIs & Webscraping and pushing them to Google Cloud
    run_motorist_task = extract_motorist()
    run_sgcarmart_task = extract_sgcarmart()
    run_carro_task = extract_carro()
    run_coe_task = extract_coe()
    run_car_population_task = extract_car_population()
    run_stock_task = extract_stock()

    # Check all data is correct
    initial_data_checker_task = extract_initial_data_from_gcs()

    # Clean all datasets
    clean_sgcarmart_task = clean_sgcarmart()
    clean_motorist_task = clean_motorist(clean_sgcarmart_task)
    clean_carro_task = clean_carro(clean_sgcarmart_task)

    # Forecast COE data
    forecast_coe_task = coe_forecast()

    # Merge car datasets
    merge_car_task = merge_car_data()

    # Merge all datasets
    merge_all_task = merge_all_data()

    # Run sold checker on final data
    run_sold_checker_task = run_sold_checker()

    # Upload dashboard dataset to BigQuery
    bq_dashboard_data_upload_task = _gcs_to_bq_task(task_id="bq_upload_final_dashboard_data",
                                                    source_objects="final_datasets/final_dashboard_data.csv",
                                                    table_name="final_dashboard_data")
    
    # Upload Final COE dataset to BigQuery
    bq_coe_data_upload_task = _gcs_to_bq_task(task_id="bq_upload_final_coe_data",
                                                    source_objects="final_datasets/final_coe_data.csv",
                                                    table_name="final_coe_data")

    # Fill up blank cells with assumptions
    fill_blanks_for_ml_task = all_data_with_blanks_filled()

    # Upload ML dataset to BigQuery
    bq_final_ml_upload_task = _gcs_to_bq_task(task_id="bq_upload_final_ml_data",
                                              source_objects="final_datasets/final_ml_data.csv",
                                              table_name="final_ml_data")

    start_DAG_task >> [run_coe_task, run_car_population_task, run_stock_task,
                       run_motorist_task, run_sgcarmart_task, run_carro_task] \
                       >> initial_data_checker_task \
                       >> [clean_motorist_task, clean_sgcarmart_task, 
                           clean_carro_task, forecast_coe_task] \
                       >> merge_car_task \
                       >> merge_all_task \
                       >> run_sold_checker_task \
                       >> [bq_dashboard_data_upload_task, bq_coe_data_upload_task] \
                       >> fill_blanks_for_ml_task \
                       >> bq_final_ml_upload_task

dag = my_dag()