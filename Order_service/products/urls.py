from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomUserViewSet, ItemViewSet

# 🚀 Create router & register our ViewSets
router = DefaultRouter()
router.register(r'users', CustomUserViewSet)  # /api/users/
router.register(r'items', ItemViewSet)  # /api/items/

# Include the router URLs
urlpatterns = [
    path('', include(router.urls)),  # Adds all endpoints automatically

    # Added for likes 
    path('items/<int:item_id>/like/', ItemViewSet.as_view({'post': 'like_item'}), name='item-like'),
]
