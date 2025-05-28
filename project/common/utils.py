""" Common utility functions for the project."""""
import re

# Media File Prefixes
def get_user_media_path_prefix(instance, filename):
    return f"users/{instance.uid}/{filename}"