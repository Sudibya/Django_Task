from rest_framework import serializers
from .models import CustomUser, Item
from django.core.exceptions import ValidationError
import os

# 🚀 Serializer for CustomUser Model
class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = '__all__'  # Includes all fields (username, email)


# 🚀 Serializer for Item Model with validation
class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = '__all__'  # Includes all fields (name, image, likes)

    def validate_name(self, value):
        """Ensure that an item with the same name does not exist."""
        if Item.objects.filter(name=value).exists():
            raise ValidationError("An item with this name already exists.")
        return value

    def validate_image(self, value):
        """Validate that the uploaded image is a JPG."""
        ext = os.path.splitext(value.name)[1].lower()  # Get file extension
        if ext not in ['.jpg', '.jpeg']:  # Only allow JPG files
            raise ValidationError("Only JPG images are allowed.")
        return value
