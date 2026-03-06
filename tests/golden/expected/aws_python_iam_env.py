import os
from google.cloud import storage
from google.auth import default

GCP_PROJECT = os.environ.get('GCP_PROJECT')
GCP_REGION = os.environ.get('GCP_REGION', 'us-central1')

credentials, project = default()

client = storage.Client(credentials=credentials, project=GCP_PROJECT)
