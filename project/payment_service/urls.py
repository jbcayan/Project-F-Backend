# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'subscription-plans', views.SubscriptionPlanViewSet, basename='subscriptionplan')
router.register(r'payment-history', views.PaymentHistoryViewSet, basename='paymenthistory')

urlpatterns = [
    path('', include(router.urls)),
    path('purchase/', views.purchase, name='purchase'),
    path('subscribe/', views.subscribe, name='subscribe'),
    path('univapay/charge/', views.univapay_charge, name='univapay_charge'),
    path('univapay/subscription/', views.univapay_subscription, name='univapay_subscription'),
    path('univapay/webhook/', views.univapay_webhook, name='univapay_webhook'),
]