# Generated by Django 5.2.1 on 2025-06-24 06:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment_service', '0002_subscriptionplan_uid'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersubscription',
            name='checkout_session_id',
            field=models.CharField(blank=True, help_text='Last known Stripe Checkout Session ID', max_length=255, null=True),
        ),
    ]
