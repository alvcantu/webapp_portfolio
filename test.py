import pandas as pd
import numpy as np

def convert_df_for_mysql(df):
    # Convert object types that should be ENUM to categorical with a specified set of categories
    categories = {
        'job': ['admin.', 'blue-collar', 'entrepreneur', 'housemaid', 'management', 'retired', 'self-employed', 'services', 'student', 'technician', 'unemployed', 'unknown'],
        'marital': ['divorced', 'married', 'single', 'unknown'],
        'default': ['no', 'yes', 'unknown'],
        'housing': ['no', 'yes', 'unknown'],
        'loan': ['no', 'yes', 'unknown'],
        'contact': ['cellular', 'telephone', 'unknown'],
        'month': ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'],
        'poutcome': ['failure', 'nonexistent', 'success', 'unknown'],
        'y': ['yes', 'no']
    }

    for col, cats in categories.items():
        df[col] = pd.Categorical(df[col], categories=cats, ordered=False)

    # Ensure 'balance' is float32 for MySQL FLOAT compatibility
    df['balance'] = df['balance'].astype('float32')

    # Convert duration, campaign, pdays, previous to int32 for MySQL INT compatibility
    for col in ['duration', 'campaign', 'pdays', 'previous']:
        df[col] = df[col].astype('int32')

    # Convert 'y' to 'subscribed_y' with boolean interpretation
    df['subscribed_y'] = df['y'].map({'yes': 1, 'no': 0}).astype('int8')  # TINYINT in MySQL
    del df['y']  # Remove the old 'y' column

    # Rename default to default_credit
    df = df.rename(columns={'default': 'default_credit'})

    # Add customer_id as a unique identifier
    df['customer_id'] = range(1, len(df) + 1)
    
    # Ensure all numeric columns are numeric to catch any potential issues
    numeric_columns = ['age', 'balance', 'duration', 'campaign', 'pdays', 'previous']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')  # Coerce to handle potential non-numeric values

    return df


# Read data from CSV files
df_nonadditional = pd.read_csv('/home/alvcantu/bank_marketing/bank-full.csv',sep=';')
df_additional = pd.read_csv('/home/alvcantu/bank_marketing/bank-additional-full.csv', sep=';')

# Drop columns that are not needed in df additional as they're only available in one csv
df_nonadditional = df_nonadditional.drop(['day'], axis=1)
df_additional = df_additional.drop(['day_of_week', 'emp.var.rate', 'cons.price.idx', 'cons.conf.idx', 'euribor3m', 'nr.employed'], axis=1)

# Union the two dataframes
union_df = pd.concat([df_nonadditional, df_additional], ignore_index=True)

# Remove duplicates on merged dataframe
df = union_df.drop_duplicates()

# Replace Nan Balance with 0
df['balance'] = df['balance'].fillna(0)
# Replace 'other' with 'unknown for poutomc column
df['poutcome'] = df['poutcome'].replace('other', 'unknown')

# Assuming you have your DataFrame named 'df'
df_ready = convert_df_for_mysql(df)
column_order = [
    'customer_id', 'age', 'job', 'marital', 'education', 'default_credit', 'balance', 'housing', 'loan', 'contact', 'month', 
    'duration', 'campaign', 'pdays', 'previous', 'poutcome', 'subscribed_y'
]
df_ready = df_ready[column_order]

print(df_ready.isnull().sum())  # This will show you if and where there are any NaN values
# print("Non aditional csv:")
# print(df_nonadditional['contact'].unique())
# print("Additional csv:")
# print(df_additional['contact'].unique())
# print("After union:")
# print(union_df['contact'].unique())
# print("After removing dups:")
# print(df['contact'].unique())
# print("After converting to mysql:")
# print(df_ready['contact'].unique())

