import stripe
from decouple import config
from dotenv import load_dotenv

load_dotenv()

def init_stripe():
    live_mode = config("STRIPE_LIVE_MODE", default="false").lower() == "true"
    stripe.api_key = (
        config("STRIPE_LIVE_SECRET_KEY") if live_mode else config("STRIPE_TEST_SECRET_KEY")
    )
    return stripe

def get_stripe_keys():
    live_mode = config("STRIPE_LIVE_MODE", default="false").lower() == "true"
    return {
        "secret": config("STRIPE_LIVE_SECRET_KEY") if live_mode else config("STRIPE_TEST_SECRET_KEY"),
        "public": config("STRIPE_LIVE_PUBLIC_KEY") if live_mode else config("STRIPE_TEST_PUBLIC_KEY"),
    }
