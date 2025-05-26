from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, ProductCategoryViewSet, UnitViewSet, GlobalSettingsViewSet

router = DefaultRouter()
router.register(r'product-category', ProductCategoryViewSet)
router.register(r'units', UnitViewSet)
router.register(r'products', ProductViewSet)
router.register(r'settings', GlobalSettingsViewSet, basename='settings')

urlpatterns = [
    path('', include(router.urls)),
]