# ============================
# Local Environment Settings
# ============================
import logging

logger = logging.getLogger(__name__)
logger.info("I am in production settings")

from .base import *


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Use WhiteNoise to serve static files efficiently in production
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files (uploads)
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
DATABASE_TYPE = config("DATABASE_TYPE", default="sqlite")
if DATABASE_TYPE == "sqlite":
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:  # Assuming PostgreSQL as the other option
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="throwin"),
            "USER": config("DB_USER", default="postgres"),
            "PASSWORD": config("DB_PASSWORD", default="postgres"),
            "HOST": config("DB_HOST", default="127.0.0.1"),
            "PORT": config("DB_PORT", default="5432")
        },
        "OPTIONS": {
            "sslmode": "require",  # Add this line if SSL is required
        },
    }


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://localhost:6379",
        # "LOCATION": "redis://redis_cache:6379",
    }
}