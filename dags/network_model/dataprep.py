# import required libraries
from google.cloud import bigquery
import pandas as pd
from sklearn.preprocessing import LabelEncoder
import ipaddress
import os
import pickle

#kalau coba pakai airflow, pakai ini buat crednya
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

# function to transform data with LabelEncoder
def transform_data_with_label_encoder(data, columns):
    label_encoders = {}
    le = LabelEncoder()
    for col in columns:
        data[col] = le.fit_transform(data[col])
        label_encoders[col] = le

    # Save the label encoders as a pickle file
    with open('label_encodings.pkl', 'wb') as f:
        pickle.dump(label_encoders, f)

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
    
# Function to convert port to integer, handling hexadecimal and other non-numeric values
def convert_port(port):
    try:
        # convert langsung ke integer
        return int(port)
    except ValueError:
        try:
            # kalau konversi gagal, cek apakah hexadecimal string
            if isinstance(port, str) and port.startswith("0x"):
                return int(port, 16)
        except ValueError:
            pass
        # Return None or a default value for non-numeric values
        return None

# main function
def main():
    # replace with your query to fetch data from BigQuery
    query = "SELECT * FROM `stately-node-363801.network.cleaned_data_silver`"
    
    # fetch data
    data = fetch_data_from_bigquery(query)
    
    # specify the columns to be transformed (encoder)
    columns_to_transform = ['protocol', 'direction', 'state', 'label']
    
    # transform data
    transformed_data = transform_data_with_label_encoder(data, columns_to_transform)

    # Apply IP to the DataFrame
    data['source_address'] = data['source_address'].apply(ip_to_int)
    data['destination_address'] = data['destination_address'].apply(ip_to_int)

    #transform data type
    data['destination_port'] = data['destination_port'].apply(convert_port)
    data['source_port'] = data['source_port'].apply(convert_port)

    #ensure there is no null values
    data.fillna(0)

    # save transformed data back to BigQuery
    save_data_to_bigquery(transformed_data, 'network', 'transformed_silver')

if __name__ == "__main__":
    main()
