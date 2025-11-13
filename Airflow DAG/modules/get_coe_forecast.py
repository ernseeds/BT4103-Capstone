import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
import os
from scipy.stats import norm
from datetime import timedelta, datetime

def get_coe_forecast(df_coe):
    df_coe_a = df_coe[df_coe['Vehicle_Class'] == 'Category A'].reset_index(drop=True)
    df_coe_b = df_coe[df_coe['Vehicle_Class'] == 'Category B'].reset_index(drop=True)

    model_a = ARIMA(endog=df_coe_a['Premium'], order=(2,1,3)).fit()
    model_b = ARIMA(endog=df_coe_b['Premium'], order=(1,1,2)).fit()

    # model_a
    model_a.get_forecast(steps=10).conf_int(alpha=0.05)

    model_a = ARIMA(endog=df_coe_a['Premium'], order=(2,1,3)).fit()
    model_b = ARIMA(endog=df_coe_b['Premium'], order=(1,1,2)).fit()

    def get_bidding_wednesday(month_date, bidding_no):
        """
        Returns the Wednesday closing date for a given bidding number (1 or 2) in a month.
        """
        # Ensure month_date is the first day of the month
        first_day = month_date.replace(day=1)
        
        # Weekday: Monday=0, Sunday=6
        first_monday = first_day + pd.offsets.Week(weekday=0)
        
        if bidding_no == 1:
            closing_wed = first_monday + timedelta(days=2)
        elif bidding_no == 2:
            third_monday = first_monday + timedelta(weeks=2)
            closing_wed = third_monday + timedelta(days=2)
        else:
            raise ValueError("bidding_no should be 1 or 2")
        
        return closing_wed

    def generate_future_bidding_wednesdays(start_date, n_biddings):
        """
        Generate n_biddings future bidding Wednesdays starting from start_date.

        Returns a DataFrame with columns: 'Bidding_No', 'Closing_Wednesday'
        """
        future_dates = []

        # Ensure start_date is a Timestamp
        current_date = pd.Timestamp(start_date)

        # Find the first Wednesday on or after start_date
        weekday = current_date.weekday()  # Monday=0
        days_to_wed = (2 - weekday) % 7  # Wednesday is 2
        next_wed = current_date + timedelta(days=days_to_wed)

        for i in range(n_biddings):
            future_dates.append({
                'Bidding_No': i + 1,
                'Closing_Wednesday': next_wed
            })
            # Next bidding Wednesday is 2 weeks later
            next_wed += timedelta(weeks=2)

        return pd.DataFrame(future_dates)

    steps = 240

    # --- Category A ---
    # Last known bidding date
    last_bidding_a = pd.to_datetime(df_coe_a['Bidding_Date'].values[-1])
    print(last_bidding_a)
    # Generate future bidding Wednesdays starting from the day after last known bidding
    df_future_a = generate_future_bidding_wednesdays(last_bidding_a + pd.Timedelta(days=1), n_biddings=steps)

    # Forecast using ARIMA
    forecast_a = model_a.get_forecast(steps=steps)
    pred_mean_a = forecast_a.predicted_mean
    conf_int_a = forecast_a.conf_int(alpha=0.05)

    # Merge forecasts with future dates
    df_forecast_a = pd.DataFrame({
        'Premium_Forecast': pred_mean_a.round().astype(int).values,
        'CI_Lower': conf_int_a.iloc[:,0].round().astype(int).values,
        'CI_Upper': conf_int_a.iloc[:,1].round().astype(int).values,
        'Bidding_Date': df_future_a['Closing_Wednesday'].dt.date.values,
        'Vehicle_Class': 'Category A'
    })

    # --- Category B ---
    last_bidding_b = pd.to_datetime(df_coe_b['Bidding_Date'].values[-1])
    steps_b = 240  # your forecast horizon for category B

    df_future_b = generate_future_bidding_wednesdays(last_bidding_b + pd.Timedelta(days=1), n_biddings=steps_b)

    forecast_b = model_b.get_forecast(steps=steps_b)
    pred_mean_b = forecast_b.predicted_mean
    conf_int_b = forecast_b.conf_int(alpha=0.05)

    df_forecast_b = pd.DataFrame({
        'Premium_Forecast': pred_mean_b.round().astype(int).values,
        'CI_Lower': conf_int_b.iloc[:,0].round().astype(int).values,
        'CI_Upper': conf_int_b.iloc[:,1].round().astype(int).values,
        'Bidding_Date': df_future_b['Closing_Wednesday'].dt.date.values,
        'Vehicle_Class': 'Category B'
    })

    # Category A
    df_a_full = pd.concat([df_coe_a, df_forecast_a], ignore_index=True, sort=False)

    # Category B
    df_b_full = pd.concat([df_coe_b, df_forecast_b], ignore_index=True, sort=False)

    # Combine both categories if needed
    df_full = pd.concat([df_a_full, df_b_full], ignore_index=True, sort=False)

    # Print a csv
    save_to_csv(df_full, filename=None)
    
    return df_full

def save_to_csv(df, filename=None):
    os.makedirs("./final_datasets", exist_ok=True)
    if filename is None:
        filename = f"final_coe_datasets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join("final_datasets", filename)
    df.to_csv(filepath, index=False)
    print(f"Saved file: {filename}")

# df_full[df_full['Vehicle_Class'] =='Category A']
# print(df_full)
# df_full.to_csv('COE_prices.csv', index=False)