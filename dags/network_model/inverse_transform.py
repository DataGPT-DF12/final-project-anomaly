# import required libraries
from google.cloud import bigquery
import pandas as pd
from sklearn.preprocessing import LabelEncoder
import ipaddress
import os
import pickle

#kalau coba pakai airflow, pakai ini buat crednya
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/opt/airflow/dags/credential.json"

#kalau coba local, pakai ini
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "C:/airflow/dags/credential.json"

# initialize bigquery client
client = bigquery.Client()

# function to fetch data from BigQuery
def fetch_data_from_bigquery(query):
    query_job = client.query(query)
    result = query_job.result()
    data = result.to_dataframe()
    return data

# function to transform data back to its first value with inverse transform LabelEncoder
def inverse_transform_columns(data, columns_to_inverse, pickle_path):
    # Load the label encoders from the pickle file
    with open(pickle_path, 'rb') as f:
        label_encoders = pickle.load(f)

    # Perform the inverse transform only on selected columns
    for col in columns_to_inverse:
        if col in data.columns and col in label_encoders:
            le = label_encoders[col]
            data[col] = le.inverse_transform(data[col].astype(int))

    return data

# function to save data back to BigQuery
def save_data_to_bigquery(data, dataset_id, table_id):
    dataset_ref = client.dataset(dataset_id)
    table_ref = dataset_ref.table(table_id)
    job = client.load_table_from_dataframe(data, table_ref)
    job.result()  # Wait for the job to complete.
    print(f"Loaded {job.output_rows} rows into {dataset_id}:{table_id}.")

#function to convert IP
def ip_to_int(ip):
    try:
        # Convert IP to integer safely
        return int(ipaddress.ip_address(ip))
    except ValueError:
        # Handle invalid IP addresses
        return None
    except OverflowError:
        # Handle overflow errors
        return None
    

# main function
def main():
    # replace with your query to fetch data from BigQuery
    query = "SELECT * FROM `stately-node-363801.network.test` LIMIT 10"
    
    # fetch data
    data = fetch_data_from_bigquery(query)
    
    # specify the columns to be transformed (encoder)
    columns = ['protocol', 'direction', 'state', 'label']

    #specify encoding file path
    path = "C:/airflow/dags/network_model/label_encodings.pkl"

    # transform data
    transformed_data = inverse_transform_columns(data, columns, path)

    # Apply IP to the DataFrame
    # data['source_address'] = data['source_address'].apply(ip_to_int)
    # data['destination_address'] = data['destination_address'].apply(ip_to_int)

    # save transformed data back to BigQuery
    save_data_to_bigquery(transformed_data, 'network', 'test_inverse')

if __name__ == "__main__":
    main()
