from rest_framework import serializers
from .models import ItemCopy, Order

class ItemCopySerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemCopy
        fields = '__all__'  # Includes name and image

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'  # Includes user_id, item_copy, and created_at
