import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.email import EmailOperator
from airflow.utils.dates import days_ago

# Define the function to detect anomalies
def detect_anomalies(**kwargs):
    # Load the trained Isolation Forest model
    model = joblib.load('/path/to/isolation_forest_model.pkl')

    # Load current data
    current_data = pd.read_csv('/path/to/current_performance_data.csv')

    # Select relevant features for prediction
    features = current_data[['cpu_usage', 'memory_usage', 'response_time']]

    # Predict anomalies
    predictions = model.predict(features)

    # -1 indicates an anomaly
    anomalies = current_data[predictions == -1]

    # If anomalies are detected, set XCom to indicate anomalies were detected
    if not anomalies.empty:
        kwargs['ti'].xcom_push(key='anomalies_detected', value=1)
        anomaly_details = anomalies.to_string()
    else:
        kwargs['ti'].xcom_push(key='anomalies_detected', value=0)
        anomaly_details = "No anomalies detected."

    return anomaly_details

# Define the DAG
default_args = {
    'owner': 'airflow',
    'start_date': days_ago(1),
    'retries': 1,
    'email_on_failure': False,
    'email_on_retry': False,
}

dag = DAG(
    'anomaly_detection_and_alerting',
    default_args=default_args,
    description='Run anomaly detection and send alerts if anomalies are detected',
    schedule_interval='@hourly',
)

# Define the task to detect anomalies
detect_and_alert_task = PythonOperator(
    task_id='detect_anomalies',
    python_callable=detect_anomalies,
    provide_context=True,
    dag=dag,
)

# Define the function to send an alert
def send_alert(**kwargs):
    # Retrieve the anomaly detection result from XCom
    anomalies_detected = kwargs['ti'].xcom_pull(task_ids='detect_anomalies', key='anomalies_detected')
    anomaly_details = kwargs['ti'].xcom_pull(task_ids='detect_anomalies')
    
    if anomalies_detected == 1:
        email_subject = 'Anomaly Detected in IT Infrastructure'
    else:
        email_subject = 'No Anomaly Detected in IT Infrastructure'
        
    # Send email
    email_operator = EmailOperator(
        task_id='send_email',
        to='alert@example.com',
        subject=email_subject,
        html_content=f"<p>{anomaly_details}</p>",
        dag=dag
    )
    email_operator.execute(context=kwargs)

# Define the task to send an alert
alert_task = PythonOperator(
    task_id='send_alert',
    python_callable=send_alert,
    provide_context=True,
    dag=dag,
)

# Set task dependencies
detect_and_alert_task >> alert_task

