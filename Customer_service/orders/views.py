from rest_framework import viewsets
from rest_framework.response import Response
from .models import ItemCopy, Order
from .serializers import ItemCopySerializer, OrderSerializer

class ItemCopyViewSet(viewsets.ModelViewSet):
    queryset = ItemCopy.objects.all()
    serializer_class = ItemCopySerializer

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def create(self, request, *args, **kwargs):
        """
        Handle order creation and publish event to Kafka.
        """
        response = super().create(request, *args, **kwargs)

        # 🔥 Publish to Kafka (Example)
        # kafka_producer.send('order_events', response.data)

        return response
