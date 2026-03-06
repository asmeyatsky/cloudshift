from google.cloud import firestore

db = firestore.Client()
collection = db.collection('users')


def put_user(user_id, name, email):
    """Add a user to Firestore."""
    collection.document(user_id).set({
        'name': name,
        'email': email,
    })


def get_user(user_id):
    """Get a user from Firestore."""
    doc = collection.document(user_id).get()
    return doc.to_dict() if doc.exists else None


def query_users_by_email(email):
    """Query users by email."""
    docs = collection.where('email', '==', email).stream()
    return [doc.to_dict() for doc in docs]


def delete_user(user_id):
    """Delete a user from Firestore."""
    collection.document(user_id).delete()
