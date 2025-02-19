import random
from rest_framework import viewsets
from .models import CustomUser, Item
from .serializers import CustomUserSerializer, ItemSerializer

# 🚀 ViewSet for CustomUser with random ordering
class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()  # ✅ Explicitly define queryset
    serializer_class = CustomUserSerializer

    def get_queryset(self):
        """Return users in random order"""
        return CustomUser.objects.order_by("?")[:1]  # Fetch users randomly

# 🚀 ViewSet for handling Item CRUD operations
class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
