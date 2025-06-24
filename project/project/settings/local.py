# ============================
# Local Environment Settings
# ============================
import logging

logger = logging.getLogger(__name__)
logger.info("I am in local settings")

from .base import *



# =============================================================
# Use for S3 bucket
# =============================================================
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
AWS_S3_CUSTOM_DOMAIN = config('AWS_S3_CUSTOM_DOMAIN', default=f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com')

# S3 Default Options
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
}
AWS_DEFAULT_ACL = None  # Important for newer AWS behavior

# --- STATIC FILES ---
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
# --- MEDIA FILES ---
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

# Correct Django 4.2+ storage configuration
STORAGES = {
    "default": {
        "BACKEND": "project.storage_backends.MediaStorage",
    },
    "staticfiles": {
        "BACKEND": "project.storage_backends.StaticStorage",
    },
}
# =============================================================


# =============================================================================
# Local Environment Settings
# =============================================================================
# STATIC_URL = "/static/"
# STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
#
# ## Media files (uploads)
# MEDIA_URL = "/media/"
# MEDIA_ROOT = os.path.join(BASE_DIR, "media")

## Use WhiteNoise to serve static files efficiently in production
# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
# ==============================================================================


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
            "NAME": config("DB_NAME", default="project-f-db"),
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
        # "LOCATION": "redis://alibi_redis:6379",
    }
}