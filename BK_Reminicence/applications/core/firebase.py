import os
import firebase_admin
from firebase_admin import credentials, firestore
from django.conf import settings

def get_firestore_client():
    """
    Inicializa Firebase Admin una sola vez y devuelve el cliente Firestore.
    """
    if not firebase_admin._apps:
        key_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_FILE")
        if not key_path:
            key_path = os.path.join(settings.BASE_DIR, "secret", "firebase_service_account.json")

        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)

    return firestore.client()