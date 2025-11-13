import requests
import pandas as pd
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

def get_coe_dataset():
    base_url = "https://data.gov.sg/api/action/datastore_search"
    dataset_id = "d_69b3380ad7e51aff3a7dcc84eba52b8a"
    records = []
    offset = 0
    limit = 1000

    while True:
        url = f"{base_url}?resource_id={dataset_id}&limit={limit}&offset={offset}"
        response = requests.get(url)
        batch = response.json()['result']['records']
        if not batch:  # stop when API returns empty
            break
        records.extend(batch)
        offset += limit

    raw_df = pd.DataFrame(records)
    df1 = _make_coe(raw_df)
    df2 = _make_pqp(raw_df)
    return df1, df2

# ----------------------------
# Helpers for COE close date
# ----------------------------
def first_monday(year: int, month: int) -> date:
    d = date(year, month, 1)
    return d + timedelta(days=(0 - d.weekday()) % 7)

def third_monday(year: int, month: int) -> date:
    return first_monday(year, month) + timedelta(days=14)

def coe_bidding_end_simple(year: int, month: int, bidding_no: int) -> datetime:
    mon = first_monday(year, month) if bidding_no == 1 else third_monday(year, month)
    end_d = mon + timedelta(days=2)
    return datetime.combine(end_d, time(16, 0))

# ----------------------------
# COE df
# ----------------------------
def _make_coe(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    # Normalize
    df[['year','month_num']] = df['month'].str.split('-', expand=True).astype(int)
    df['bidding_no'] = pd.to_numeric(df['bidding_no'], errors='coerce').astype(int)
    for col in ['quota', 'bids_success', 'bids_received', 'premium']:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype('string')
                .str.replace(r'[^\d\.\-]', '', regex=True)
            )
            df[col] = pd.to_numeric(df[col], errors='coerce')
    # Close date/time
    df['bidding_end']  = df.apply(lambda r: coe_bidding_end_simple(int(r['year']), int(r['month_num']), int(r['bidding_no'])), axis=1)
    df['bidding_date'] = pd.to_datetime(df['bidding_end']).dt.date
    # Select/order
    cols = ['bidding_date', 'vehicle_class', 'quota', 'bids_success', 'bids_received', 'premium']
    have = [c for c in cols if c in df.columns]
    df_coe = df.loc[:, have].reset_index(drop=True)
    df_coe = df_coe.rename(columns={
        'bidding_date': 'Bidding_Date',
        'vehicle_class': 'Vehicle_Class',
        'quota': 'Quota',
        'bids_success': 'Bids_Success',
        'bids_received': 'Bids_Received',
        'premium': 'Premium'
    })
    return df_coe

# ----------------------------
# PQP df
# ----------------------------
def _make_pqp(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    df['month_key'] = df['month']
    df['premium'] = pd.to_numeric(df['premium'], errors='coerce')
    # PQP for A–D only
    df = df[~df['vehicle_class'].str.upper().eq('CATEGORY E')].copy()
    monthly = (
        df.groupby(['vehicle_class', 'month_key'], as_index=False)
          .agg(premium_sum=('premium','sum'), premium_cnt=('premium','count'))
          .sort_values(['vehicle_class','month_key'])
    )
    # 1) Monthly avg rounded to nearest dollar (half-up) using integer math:
    monthly['monthly_avg_rounded'] = (
        (monthly['premium_sum']*2 + monthly['premium_cnt']) // (2*monthly['premium_cnt'])
    ).astype('Int64')
    # 2) PQP = half-up of mean of previous 3 rounded monthly avgs
    def pqp_from_rounded_window(s: pd.Series):
        s_prev = s.shift(1)  # use previous 3 months
        # half-up divide by 3: (a+b+c + 1) // 3
        return s_prev.rolling(3, min_periods=3).apply(
            lambda w: (int(w.iloc[-3]) + int(w.iloc[-2]) + int(w.iloc[-1]) + 1) // 3,
            raw=False
        ).astype('Int64')
    monthly['pqp_price_ten_year'] = (
        monthly.groupby('vehicle_class', group_keys=False)['monthly_avg_rounded']
               .apply(pqp_from_rounded_window)
    )
    # 5-year = floor(ten-year/2)
    monthly['pqp_price_five_year'] = monthly['pqp_price_ten_year'].floordiv(2).astype('Int64')
    # Final shape
    out = monthly[['month_key','vehicle_class','pqp_price_ten_year','pqp_price_five_year']].copy()
    out['month'] = pd.to_datetime(out['month_key'], format='%Y-%m')  # first day of month
    out = out.drop(columns=['month_key']).sort_values(['month','vehicle_class']).reset_index(drop=True)
    # Fill missing monthly rows per Vehicle_Class (ffill)
    def fill_months(g: pd.DataFrame) -> pd.DataFrame:
        g = g.sort_values('month')
        full_idx = pd.date_range(g['month'].min(), g['month'].max(), freq='MS')
        g = (g.set_index('month')
               .reindex(full_idx)
               .ffill()
               .rename_axis('month')
               .reset_index())
        # ensure the class label persists after reindex
        g['vehicle_class'] = g['vehicle_class'].astype('string')
        return g
    out = (out.groupby('vehicle_class', group_keys=True, as_index=False)
           .apply(fill_months)
           .reset_index(drop=True))
    # Restore integer dtypes after ffill (which may cast to float)
    for c in ['pqp_price_ten_year', 'pqp_price_five_year']:
        out[c] = pd.to_numeric(out[c], errors='coerce').astype('Int64')
    # Select/order
    cols = ['month', 'vehicle_class', 'pqp_price_ten_year', 'pqp_price_five_year']
    have = [c for c in cols if c in out.columns]
    df_pqp = out.loc[:, have].reset_index(drop=True)
    df_pqp = df_pqp.rename(columns={
        'month': 'Month',
        'vehicle_class': 'Vehicle_Class',
        'pqp_price_ten_year': 'PQP_Price_Ten_Year',
        'pqp_price_five_year': 'PQP_Price_Five_Year'
    })
    return df_pqp

# df_coe, df_pqp = get_coe_dataset()
# df_coe.to_csv("df_coe.csv", index=False)
# df_pqp.to_csv("df_pqp.csv", index=False)
# print(df_coe)
# print(df_pqp)