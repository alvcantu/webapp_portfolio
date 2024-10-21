import pandas as pd
import numpy as np
import mysql.connector
from mysql.connector import Error
from sklearn.preprocessing import LabelEncoder
from lazypredict.Supervised import LazyClassifier

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
features = df.drop(columns=['subscribed_y', 'duration'])
target = df['subscribed_y']

# Encode categorical variables
le = LabelEncoder()
for column in features.select_dtypes(include=['category', 'object']):
    features[column] = le.fit_transform(features[column])

# Set train and test data
X_train, X_test, y_train, y_test = train_test_split(features, target, test_size=0.2, random_state=42)

# Determine what model to use with laxy classifier
# Initialize LazyClassifier
clf = LazyClassifier(verbose=0, ignore_warnings=True, custom_metric=None)
# Fit on the train set
models, predictions = clf.fit(X_train, X_test, y_train, y_test)
# This will take some time to run as it tests many different models
print(models)