# detect_anomalies_script.py

import pandas as pd
import joblib

# Load current data
current_data = pd.read_csv('network_data_silver.csv')

# Load the trained Isolation Forest model
model = joblib.load('isolation_forest_model.pkl')

if not current_data.empty:
    # Select relevant features for prediction
    features = current_data[['label', 'duration', 'protocol', 'source_port', 'direction', 'destination_port', 'state']]

    # Predict anomalies
    predictions = model.predict(features)

    # -1 indicates an anomaly
    anomalies = current_data[predictions == -1]

    # print(anomalies)

    # If anomalies are detected, save the anomalies to a file and exit with a non-zero status
    if not anomalies.empty:
        print(anomalies)
        # anomalies.to_csv('C:/airflow/dags/network_model/detected_anomalies.csv', index=False)
        print("Anomalies detected.")
        exit(1)
    else:
        print("No anomalies detected.")
        exit(0)
else:
    exit(0)
