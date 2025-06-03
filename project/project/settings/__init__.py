from decouple import config

env = config("DJANGO_ENV", default="local").lower()

if env == "local":
    from .local import *
elif env == "development":
    from .development import *
elif env == "production":
    from .production import *
else:
    raise Exception("Invalid DJANGO_ENV value. Must be 'local', 'development', or 'production'.")
