import json
from google.cloud import storage, firestore

storage_client = storage.Client()
db = firestore.Client()
collection = db.collection('events')


def handler(request):
    """Cloud Function handler for processing GCS events."""
    event = request.get_json()
    bucket_name = event['bucket']
    file_name = event['name']

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    data = json.loads(blob.download_as_bytes())

    collection.document(data['id']).set({
        'source': f"gs://{bucket_name}/{file_name}",
        'payload': json.dumps(data),
    })

    return json.dumps({'processed': 1}), 200
