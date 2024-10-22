
8/home/alvcantu/bank_marketing/ml_model_bank_marketing.pyä(import pandas as pd
import numpy as np
import mysql.connector
from mysql.connector import Error
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from bayes_opt import BayesianOptimization


# Connect to MySQL database
def get_db_connection():
    mydb = mysql.connector.connect(
        host="alvcantu.mysql.pythonanywhere-services.com",
        user="alvcantu",
        password="h63Efp09-d",
        database="alvcantu$default"
    )
    cursor = mydb.cursor()
    return mydb, cursor


sql_query_extract = '''
SELECT * FROM BM_FactCustomers;
'''

# Fetch data
mydb, cursor = get_db_connection()
cursor.execute(sql_query_extract)
data = cursor.fetchall()
columns = [i[0] for i in cursor.description]  # Get column names

# Convert to DataFrame
df = pd.DataFrame(data, columns=columns)

# Convert ENUM and other categorical data to category type for better memory usage and performance
for col in df.columns:
    if df[col].dtype == 'object':  # This will catch both ENUM and VARCHAR
        df[col] = df[col].astype('category')

# Assuming 'duration' should not be used in the model as per following documentation:
# Duration: last contact duration, in seconds (numeric). Important
# note: this attribute highly affects the output target (e.g., if
# duration=0 then y='no'). Yet, the duration is not known before a call
# is performed. Also, after the end of the call y is obviously known.
# Thus, this input should only be included for benchmark purposes and
# should be discarded if the intention is to have a realistic
# predictive model.
features = df.drop(columns=['subscribed_y', 'duration','customer_id'])
target = df['subscribed_y']


def encode_categorical_columns(df, encoding_type='label'):
    """
    Encodes categorical columns in the dataframe either using LabelEncoder or One-Hot Encoding.

    Parameters:
    df (pd.DataFrame): The dataframe containing the features.
    encoding_type (str): The type of encoding to apply ('label' for LabelEncoder, 'onehot' for One-Hot Encoding).

    Returns:
    pd.DataFrame: The dataframe with encoded categorical columns.
    """
    # Make a copy of the dataframe to avoid modifying the original
    df_encoded = df.copy()
    
    # Get the list of categorical columns
    categorical_columns = df_encoded.select_dtypes(include=['category', 'object']).columns
    
    # Loop through each categorical column and encode it
    if encoding_type == 'label':
        # Label Encoding (converts categories to integers)
        le = LabelEncoder()
        for column in categorical_columns:
            df_encoded[column] = le.fit_transform(df_encoded[column])
    
    elif encoding_type == 'onehot':
        # One-Hot Encoding (converts categories to binary columns)
        df_encoded = pd.get_dummies(df_encoded, columns=categorical_columns)
    
    else:
        raise ValueError("Invalid encoding_type. Choose 'label' or 'onehot'.")
    
    return df_encoded

# Encode categorical variables
le = LabelEncoder()
for column in features.select_dtypes(include=['category', 'object']):
    features[column] = le.fit_transform(features[column])

# Set train and test data
X_train, X_test, y_train, y_test = train_test_split(features, target, test_size=0.2, random_state=42)

# Define the Bayesian optimization function
def xgb_bayes_opt(max_depth, learning_rate, n_estimators, gamma, min_child_weight, subsample, colsample_bytree, reg_alpha, reg_lambda):
    xgb_class = xgb.XGBClassifier(objective='binary:logistic', max_depth=int(max_depth), learning_rate=learning_rate, n_estimators=int(n_estimators), gamma=gamma, min_child_weight=min_child_weight, subsample=subsample, colsample_bytree=colsample_bytree, reg_alpha=reg_alpha, reg_lambda=reg_lambda, n_jobs=-1)
    xgb_class.fit(X_train, y_train)
    y_pred = xgb_class.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    return -accuracy  # Note the minus sign to convert to minimization problem

# Define the bounds for the hyperparameters
bounds = {
    'max_depth': (3, 10),
    'learning_rate': (0.01, 1),
    'n_estimators': (50, 200),
    'gamma': (0, 1),
    'min_child_weight': (1, 10),
    'subsample': (0.5, 1),
    'colsample_bytree': (0.5, 1),
    'reg_alpha': (0, 1),
    'reg_lambda': (0, 1)
}

# Initialize the Bayesian optimizer
optimizer = BayesianOptimization(f=xgb_bayes_opt, pbounds=bounds, random_state=42)

# Perform the optimization
optimizer.maximize(init_points=5, n_iter=40)

# Print the optimized hyperparameters
print(optimizer.max)

# Train the XGBoost classifier with the optimized hyperparameters
xgb_class = xgb.XGBClassifier(objective='binary:logistic', **optimizer.max['params'])
xgb_class.fit(X_train, y_train)

# Make predictions
y_pred = xgb_class.predict(X_test)

# Evaluate the model
accuracy = accuracy_score(y_test, y_pred)

# Save accuracy
with open('accuracy_ml_model_classification_bank_marketing.txt', 'w') as f:
    f.write(str(accuracy))

# Save the model
xgb_class.save_model('ml_model_classification_bank_marketing.json')` `√√ƒ
ƒƒ 
ƒ› ›ˇ
ˇç	 ç	é	é	ÒÒÙ
Ù¶ ¶ß
ßÕ# Õ#œ#
œ#æ& 
æ&«& 0«&Õ&*$bb1bb65a-1944-472b-ac01-78f71e1aad670
Õ&Œ& 2Œ&Ÿ& *$3054d509-892c-46b4-922c-1c0fb4716fd00Ÿ&‚&‚&˙&2˙&µ' *$3054d509-892c-46b4-922c-1c0fb4716fd00
µ'∂' 
∂'›' 
›'ı' 
ı'ä( "(7819dda098421ea5c0fedc4efd2807baf5d803b2*/home/alvcantu2?file:///home/alvcantu/bank_marketing/ml_model_bank_marketing.py:file:///home/alvcantu