import os
from airflow import DAG
from airflow.providers.google.cloud.operators.gcs import GCSFileTransformOperator, GCSListObjectsOperator
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.operators.python import PythonOperator
from airflow.operators.email import EmailOperator
from airflow.utils.dates import days_ago
from datetime import datetime
import subprocess

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 6, 4),
    'retries': 1,
}

# Define the DAG
dag = DAG(
    'anomaly_detect_pipeline',
    default_args=default_args,
    description='A DAG to upload or overwrite CSV data in GCS',
    schedule_interval='@once',
)

# Define bucket, file details and DBT
GCS_BUCKET = 'testing_bucket_df12' #bucket name
GCS_FILE_PATH = 'network_data/test_dataset.csv' # Path to the GCS and file name when its done uploaded
LOCAL_FILE_PATH = '/opt/airflow/dags/network_model/test_dataset.csv'  # Path to the local file to be uploaded
DBT_PROJECT_PATH = '/opt/airflow/dags/dbt/network' #path of dbt project in airflow

def check_file_exists(**kwargs):
    """
    Check if a file exists in GCS.
    """
    ti = kwargs['ti']
    bucket_name = kwargs['bucket_name']
    file_path = kwargs['file_path']
    
    # Use the GCSListObjectsOperator to list files in the bucket
    list_files = GCSListObjectsOperator(
        task_id='list_files',
        bucket=bucket_name,
        prefix=file_path,
        #google_cloud_storage_conn_id='google_cloud_default'
    )
    
    files = list_files.execute(context=kwargs)
    
    if files:
        # File exists
        ti.xcom_push(key='file_exists', value=True)
    else:
        # File does not exist
        ti.xcom_push(key='file_exists', value=False)

def upload_or_overwrite(**kwargs):
    """
    Upload or overwrite the file in GCS based on its existence.
    """
    ti = kwargs['ti']
    file_exists = ti.xcom_pull(task_ids='check_file_exists', key='file_exists')
    
    if file_exists:
        # Overwrite existing file
        os.system(f'gsutil cp -a public-read {LOCAL_FILE_PATH} gs://{GCS_BUCKET}/{GCS_FILE_PATH}')
    else:
        # Upload the file
        os.system(f'gsutil cp {LOCAL_FILE_PATH} gs://{GCS_BUCKET}/{GCS_FILE_PATH}')


def run_dbt():
    try:
        # Run dbt commands using subprocess
        subprocess.run(["dbt", "run","--select", "cleaned_data_silver"], check=True, cwd=DBT_PROJECT_PATH)
    except subprocess.CalledProcessError as e:
        # Log any errors if the dbt command fails
        print(f"dbt command failed with error: {e}")


def run_transform_script():
    result = subprocess.run(['python', '/opt/airflow/dags/network_model/dataprep.py'], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)
    if result.returncode != 0:
        raise Exception("Script failed: " + result.stderr)


#function to trigger the anomaly_test.py script to detect anomaly using ML model
def run_detect_anomalies_script(**kwargs):
    # Run the anomaly detection script
    result = subprocess.run(['python', '/opt/airflow/dags/network_model/anomaly_test.py'], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)
    
    # Check the return code to see if anomalies were detected
    if result.returncode == 1:
        # Set XCom to indicate anomalies were detected
        kwargs['ti'].xcom_push(key='anomalies_detected', value=True)
    else:
        kwargs['ti'].xcom_push(key='anomalies_detected', value=False)


#if anomaly detected, send email
def send_alert(**kwargs):
    # Check XCom for anomalies_detected flag
    anomalies_detected = kwargs['ti'].xcom_pull(task_ids='detect_and_alert', key='anomalies_detected')
    if anomalies_detected:

        #coba send email
        email_operator = EmailOperator(
            task_id='send_email',
            to='brightlyyun@gmail.com',
            subject='Airflow Email Notification',
            html_content='<p>Anomalies detected. Please check on your network security system.</p>',
            dag=dag,
        )
        email_operator.execute(context=kwargs)


# Task to check if the file exists in GCS
check_file_exists = PythonOperator(
    task_id='check_file_exists',
    python_callable=check_file_exists,
    op_kwargs={'bucket_name': GCS_BUCKET, 'file_path': GCS_FILE_PATH},
    provide_context=True,
    dag=dag,
)

# Task to upload or overwrite the file in GCS
upload_or_overwrite = PythonOperator(
    task_id='upload_or_overwrite',
    python_callable=upload_or_overwrite,
    provide_context=True,
    dag=dag,
)

# Task for bigquery load (Define the BigQuery load tasks)
load_to_bigquery = GCSToBigQueryOperator(
    task_id='load_to_bigquery',
    bucket='testing_bucket_df12',
    source_objects=[GCS_FILE_PATH],
    destination_project_dataset_table='stately-node-363801.network.network_raw_bronze',
    source_format='CSV',
    skip_leading_rows=1,
    write_disposition='WRITE_TRUNCATE',
    dag=dag,
)

# Task for dbt (Define the dbt run task)
dbt_run = PythonOperator(
    task_id='dbt_run',
    python_callable=run_dbt,
    dag=dag,
)


#task for transform with Python file (label encoder)
transform_task = PythonOperator(
    task_id='run_transform_script',
    python_callable=run_transform_script,
    provide_context=True,
    dag=dag,
)

#detect by running python file to find anomaly using ML model
detect_and_alert = PythonOperator(
    task_id='detect_and_alert',
    python_callable=run_detect_anomalies_script,
    provide_context=True,
    dag=dag,
)

alert_task = PythonOperator(
    task_id='send_alert',
    python_callable=send_alert,
    provide_context=True,
    dag=dag,
)


# Set the task dependencies
check_file_exists >> upload_or_overwrite >> load_to_bigquery >> dbt_run >> transform_task
transform_task >> detect_and_alert >> alert_task
