# payment_service/stripe_client.py

import stripe
from decouple import config
from dotenv import load_dotenv
import os

# Load .env manually to fix shell/admin context
load_dotenv()

def init_stripe():
    stripe.api_key = config("STRIPE_SECRET_KEY")
    return stripe

def get_stripe_keys():
    return {
        "secret": config("STRIPE_SECRET_KEY"),
        "public": config("STRIPE_PUBLIC_KEY"),
    }
