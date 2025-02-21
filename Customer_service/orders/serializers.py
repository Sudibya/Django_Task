from rest_framework import serializers
from .models import ItemCopy, Order

class ItemCopySerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemCopy
        fields = '__all__'  # Include all fields, including 'id'

    def create(self, validated_data):
        # Get the ID passed in the validated data
        item_id = validated_data.get('id', None)
        
        if item_id:
            # If the ID is passed, create the item using the specified ID
            item_copy = ItemCopy(id=item_id, **validated_data)
            item_copy.save(force_insert=True)  # force_insert ensures it uses the passed ID
        else:
            # Otherwise, create the item normally
            item_copy = super().create(validated_data)

        return item_copy


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'  # Includes user_id, item_copy, and created_at
