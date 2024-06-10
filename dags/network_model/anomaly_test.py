# detect_anomalies_script.py
from google.cloud import bigquery
import pandas as pd
import joblib
import os

#kalau coba airflow, pakai ini
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/opt/airflow/dags/credential.json"

#kalau coba local, pakai ini
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "C:/airflow/dags/credential.json"

# initialize bigquery client
client = bigquery.Client()

# function to fetch data from BigQuery
def fetch_data_from_bigquery(query):
    query_job = client.query(query)
    result = query_job.result()
    data = result.to_dataframe()
    return data

# function to save data back to BigQuery
def save_data_to_bigquery(data, dataset_id, table_id):
    dataset_ref = client.dataset(dataset_id)
    table_ref = dataset_ref.table(table_id)
    job = client.load_table_from_dataframe(data, table_ref)
    job.result()  # Wait for the job to complete.
    print(f"Loaded {job.output_rows} rows into {dataset_id}:{table_id}.")

# # Load current data
query = "SELECT * FROM `stately-node-363801.network.transformed_silver`"
    
# fetch data
current_data = fetch_data_from_bigquery(query)
    
# Load the trained Isolation Forest model
model = joblib.load('isolation_forest_model.pkl')

if not current_data.empty:
    # Select relevant features for prediction
    features = current_data[['label', 'duration', 'protocol', 'source_port', 'direction', 'destination_port', 'state']]

    # Predict anomalies
    predictions = model.predict(features)

    # -1 indicates an anomaly
    anomalies = current_data[predictions == -1]

    #save anomaly_data with id
    anomaly_data = current_data.copy()
    anomaly_data['anomaly'] = predictions
    columns = ['primary_key','anomaly']
    anomaly_data = anomaly_data[columns]


    # If anomalies are detected, save the anomalies to a file and exit with a non-zero status
    if not anomalies.empty:
        # print(anomalies)
        #save as csv
        # anomalies.to_csv('C:/airflow/dags/network_model/detected_anomalies.csv', index=False)

        # #save as new gold table
        # # Load from cleaned data
        query2 = "SELECT * FROM `stately-node-363801.network.cleaned_data_silver`"
    
        # fetch data
        final_data = fetch_data_from_bigquery(query2)

        #merge data with anomaly result (gabungkan data awal yang sudah bersih, dengan hasil deteksi anomali)
        merged_data = final_data.merge(anomaly_data, on='primary_key', how='left')

        # merged_data.to_csv('C:/airflow/dags/network_model/final.csv', index=False)
        # save transformed data back to BigQuery
        save_data_to_bigquery(merged_data, 'network', 'anomaly_gold')

        print("Anomalies detected.")
        exit(1)
    else:
        print("No anomalies detected.")
        exit(0)
else:
    exit(0)
