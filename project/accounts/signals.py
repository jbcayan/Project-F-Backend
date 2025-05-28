import logging

logger = logging.getLogger(__name__)

def post_save_create_profile_receiver(sender, instance, created, **kwargs):
    # Import here to prevent circular import
    from accounts.models import UserProfile

    if created:
        UserProfile.objects.create(user=instance)
        logger.info(f"UserProfile created for new user: {instance.email}")
    else:
        try:
            profile = UserProfile.objects.get(user=instance)
            profile.save()
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(user=instance)
            logger.info(f"UserProfile created for existing user: {instance.email}")
