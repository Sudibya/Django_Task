from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ItemCopyViewSet, OrderViewSet

router = DefaultRouter()
router.register(r'items_copy', ItemCopyViewSet)  # /api/items/
router.register(r'orders', OrderViewSet)  # /api/orders/

urlpatterns = [
    path('', include(router.urls)),
]
