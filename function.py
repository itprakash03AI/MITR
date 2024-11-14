import streamlit as st
import pandas as pd
import numpy as np
import logging
import re
from datetime import datetime, timedelta

# Set up logging


def create_2023_dataset():
                                                                                            
    # Settings
    num_sap_accounts = 100
    cob_dates = ["2023-09-29"]
    trade_start_date = datetime(2023, 1, 1)
    trade_end_date = datetime(2023, 9, 30)

    # Generate unique Trade IDs for each day for each SAP Account
    trade_dates = pd.date_range(trade_start_date, trade_end_date)
    np.random.seed(42)

    # Create DataFrame for all combinations
    data = []

    for cob_date in cob_dates:
        for sap_account in [f"ACC-{i+1:04d}" for i in range(num_sap_accounts)]:
            for trade_date in trade_dates:
                num_trades_per_day = 1 # 1 to 3 trades per day
                for _ in range(num_trades_per_day):
                    trade_id = f"{sap_account}-{trade_date.strftime('%Y%m%d')}-{np.random.randint(1000, 9999)}"
                    
                    # Randomly set maturity to the next day or later
                    maturity_date = trade_date + timedelta(days=1)
                    
                    principal_amount = np.round(np.random.uniform(1, 10), 2) * 1e6
                    balance_amount = np.round(np.random.uniform(200000, 999000), 2)
                    interest_rate = np.round(np.random.uniform(3.5, 5.8), 2)
                    floating_rate = np.round(np.random.uniform(3.0, 6.0), 2)

                    data.append([
                        cob_date,
                        sap_account,
                        floating_rate,
                        interest_rate,
                        balance_amount,
                        trade_date,
                        maturity_date,
                        trade_id,
                        principal_amount
                    ])

    # Create DataFrame
    columns = [
        "Cob Date",
        "Sap Account",
        "Floating Rate",
        "Interest Rate",
        "Balance Amount",
        "Trade Date",
        "Maturity Date",
        "Trade ID",
        "Principal Amount"
    ]
    df_2023 = pd.DataFrame(data, columns=columns)
    return df_2023

def create_2024_dataset():
    num_sap_accounts = 100
    cob_dates = ["2024-09-30"]
    trade_start_date = datetime(2024, 1, 1)
    trade_end_date = datetime(2024, 9, 30)

    # Generate unique Trade IDs for each day for each SAP Account
    trade_dates = pd.date_range(trade_start_date, trade_end_date)
    np.random.seed(42)

    # Create DataFrame for all combinations
    data = []

    for cob_date in cob_dates:
        for sap_account in [f"ACC-{i+1:04d}" for i in range(num_sap_accounts)]:
            for trade_date in trade_dates:
                num_trades_per_day = 1 # 1 to 3 trades per day
                for _ in range(num_trades_per_day):
                    trade_id = f"{sap_account}-{trade_date.strftime('%Y%m%d')}-{np.random.randint(1000, 9999)}"
                    
                    # Randomly set maturity to the next day or later
                    maturity_date = trade_date + timedelta(days=1)
                    
                    principal_amount = np.round(np.random.uniform(1, 10), 2) * 1e6
                    balance_amount = np.round(np.random.uniform(200000, 999000), 2)
                    interest_rate = np.round(np.random.uniform(3.5, 5.8), 2)
                    floating_rate = np.round(np.random.uniform(3.0, 6.0), 2)

                    data.append([
                        cob_date,
                        sap_account,
                        floating_rate,
                        interest_rate,
                        balance_amount,
                        trade_date,
                        maturity_date,
                        trade_id,
                        principal_amount
                    ])

    # Create DataFrame
    columns = [
        "Cob Date",
        "Sap Account",
        "Floating Rate",
        "Interest Rate",
        "Balance Amount",
        "Trade Date",
        "Maturity Date",
        "Trade ID",
        "Principal Amount"
    ]
    df_2024 = pd.DataFrame(data, columns=columns)
    return df_2024

def standardize_column_names(df):
    # Standardize column names by stripping whitespace and converting to title case
    df.columns = [col.strip().title() for col in df.columns]
    return df


def prompt_response_run(df_summary, df_detailed):

    # Task 1
    df_summary['Cob Date'] = pd.to_datetime(df_summary['Cob Date'])

    df_summary_2023 = df_summary[df_summary['Cob Date'].dt.year == 2023]
    df_summary_2024 = df_summary[df_summary['Cob Date'].dt.year == 2024]

    df_summary_2023_grp = df_summary_2023.groupby('Sap Account')['Balance Amount'].sum().reset_index()
    df_summary_2024_grp = df_summary_2024.groupby('Sap Account')['Balance Amount'].sum().reset_index()

    df_summary_yoy = pd.merge(df_summary_2023_grp, df_summary_2024_grp, on='Sap Account', suffixes=('_2023', '_2024'))

    df_summary_yoy['Balance_chg'] = df_summary_yoy['Balance Amount_2024'] - df_summary_yoy['Balance Amount_2023']

    # top 3 SAP accounts with largest increase in balance
    top3_increase = df_summary_yoy.nlargest(3, 'Balance_chg')['Sap Account'].tolist()

    # top 3 SAP accounts with largest decrease in balance
    top3_decrease = df_summary_yoy.nsmallest(3, 'Balance_chg')['Sap Account'].tolist()


    # Task 2
    df_detailed['Cob Date'] = pd.to_datetime(df_detailed['Cob Date'])
    df_detailed['Trade Date'] = pd.to_datetime(df_detailed['Trade Date'])
    df_detailed['Maturity Date'] = pd.to_datetime(df_detailed['Maturity Date'])

    df_detailed_sep_2023 = df_detailed[(df_detailed['Cob Date'].dt.month == 9) & (df_detailed['Cob Date'].dt.year == 2023)]
    df_detailed_sep_2024 = df_detailed[(df_detailed['Cob Date'].dt.month == 9) & (df_detailed['Cob Date'].dt.year == 2024)]

    avg_data_2023 = df_detailed_sep_2023.groupby(['Sap Account']).agg(
        {'Balance Amount': 'mean', 'Floating Rate': 'mean', 'Interest Rate': 'mean', 'Principal Amount': 'mean'}).reset_index()
    avg_data_2024 = df_detailed_sep_2024.groupby(['Sap Account']).agg(
        {'Balance Amount': 'mean', 'Floating Rate': 'mean', 'Interest Rate': 'mean', 'Principal Amount': 'mean'}).reset_index()

    avg_data = pd.merge(avg_data_2023, avg_data_2024, on='Sap Account', suffixes=('_2023', '_2024'))


    # Task 3
    avg_data['Balance_chg'] = avg_data['Balance Amount_2024'] - avg_data['Balance Amount_2023']
    avg_data['Principal_chg'] = avg_data['Principal Amount_2024'] - avg_data['Principal Amount_2023']
    avg_data['FloatingRate_chg'] = avg_data['Floating Rate_2024'] - avg_data['Floating Rate_2023']
    avg_data['Interest_chg'] = avg_data['Interest Rate_2024'] - avg_data['Interest Rate_2023']


    # Task 4
    top3_floating_increase = avg_data.nlargest(3, 'FloatingRate_chg')['Sap Account'].tolist()
    top3_floating_decrease = avg_data.nsmallest(3, 'FloatingRate_chg')['Sap Account'].tolist()
    top3_int_increase = avg_data.nlargest(3, 'Interest_chg')['Sap Account'].tolist()
    top3_int_decrease = avg_data.nsmallest(3, 'Interest_chg')['Sap Account'].tolist()

    return top3_increase, top3_decrease, avg_data, top3_floating_increase, top3_floating_decrease, top3_int_increase, top3_int_decrease
