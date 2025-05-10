from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CounterpartyViewSet, CounterpartyStatusViewSet

router = DefaultRouter()
router.register(r'counterparties', CounterpartyViewSet)
router.register(r'counterparty-statuses', CounterpartyStatusViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
