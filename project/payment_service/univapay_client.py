import uuid
import requests
from django.conf import settings
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

UNIVAPAY_SECRET_KEY = os.getenv('UNIVAPAY_APP_SECRET', '')
UNIVAPAY_JWT_TOKEN = os.getenv('UNIVAPAY_APP_TOKEN', '')
UNIVAPAY_WEBHOOK_AUTH = os.getenv('UNIVAPAY_WEBHOOK_AUTH', '')


class UnivapayError(Exception):
    def __init__(self, status, body):
        self.status = status
        self.body = body
        super().__init__(f"Univapay API error: {status} - {body}")


class UnivapayClient:
    def __init__(self):
        self.base_url = "https://api.univapay.com"
        self.secret_key = UNIVAPAY_SECRET_KEY
        self.jwt_token = UNIVAPAY_JWT_TOKEN

        print("secret key:", self.secret_key)
        print("jwt token:", self.jwt_token)

        if not all([self.secret_key, self.jwt_token]):
            raise ValueError("Univapay credentials not configured properly")

        self.auth_header = f"Bearer {self.secret_key}.{self.jwt_token}"
        self.headers = {
            'Authorization': self.auth_header,
            'Content-Type': 'application/json',
        }

    @staticmethod
    def new_idempotency_key():
        return str(uuid.uuid4())

    def _request(self, method, endpoint, data=None, idempotency_key=None):
        url = f"{self.base_url}{endpoint}"
        headers = self.headers.copy()

        if idempotency_key:
            headers['Idempotency-Key'] = idempotency_key

        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=data)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, json=data)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            if response.status_code >= 400:
                raise UnivapayError(response.status_code, response.text)

            return response.json()
        except requests.exceptions.RequestException as e:
            raise UnivapayError(500, str(e))

    def create_charge(self, transaction_token_id, amount, currency, capture=True,
                      metadata=None, three_ds_mode=None, redirect_endpoint=None, idempotency_key=None):
        endpoint = "/charges"
        data = {
            "transaction_token_id": transaction_token_id,
            "amount": amount,
            "currency": currency,
            "capture": capture,
        }

        if metadata:
            data["metadata"] = metadata

        if three_ds_mode:
            data["three_ds"] = {"mode": three_ds_mode}

        if redirect_endpoint:
            data["redirect"] = {"endpoint": redirect_endpoint}

        return self._request('POST', endpoint, data, idempotency_key)

    def get_charge(self, charge_id):
        endpoint = f"/charges/{charge_id}"
        return self._request('GET', endpoint)

    def create_subscription(self, transaction_token_id, amount, currency, period,
                            metadata=None, three_ds_mode=None, redirect_endpoint=None, idempotency_key=None):
        endpoint = "/subscriptions"
        data = {
            "transaction_token_id": transaction_token_id,
            "amount": amount,
            "currency": currency,
            "period": period,
        }

        if metadata:
            data["metadata"] = metadata

        if three_ds_mode:
            data["three_ds"] = {"mode": three_ds_mode}

        if redirect_endpoint:
            data["redirect"] = {"endpoint": redirect_endpoint}

        return self._request('POST', endpoint, data, idempotency_key)

    def get_subscription(self, subscription_id):
        endpoint = f"/subscriptions/{subscription_id}"
        return self._request('GET', endpoint)

    def cancel_subscription(self, subscription_id):
        endpoint = f"/subscriptions/{subscription_id}/cancel"
        return self._request('POST', endpoint)
