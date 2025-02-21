import time
import json
import logging
from confluent_kafka import Producer, KafkaException
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import CustomUser, Item
from .serializers import CustomUserSerializer, ItemSerializer

logger = logging.getLogger(__name__)

def get_kafka_producer(retries=5, delay=5):
    """
    Lazily create a confluent_kafka Producer with retries.
    """
    conf = {
        'bootstrap.servers': 'kafka:9092'  # Ensure Kafka is reachable
    }
    for attempt in range(1, retries + 1):
        try:
            producer = Producer(conf)
            logger.info("✅ Kafka producer created successfully on attempt %d", attempt)
            return producer
        except KafkaException as e:
            logger.error("❌ Attempt %d: Kafka producer error: %s", attempt, e)
            time.sleep(delay)
    raise Exception("❌ Could not connect to Kafka broker after {} attempts".format(retries))


# ✅ Callback function for Kafka message delivery
def delivery_report(err, msg):
    if err is not None:
        logger.error("❌ Kafka delivery failed: %s", err)
    else:
        logger.info("✅ Kafka message delivered to %s [%s]", msg.topic(), msg.partition())


# 🚀 ViewSet for CustomUser with random ordering
class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

    def get_queryset(self):
        """Return users in random order"""
        return CustomUser.objects.order_by("?")[:1]


# 🚀 ViewSet for handling Item CRUD operations using confluent_kafka for event publishing
class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer

    def _send_kafka_event(self, action, item_data):
        """
        Send an event to Kafka topic asynchronously with a callback.
        """
        event_data = {'action': action, 'item': item_data}
        try:
            producer = get_kafka_producer()
            producer.produce(
                topic='items_topic',
                key=b"key.user.event",  # 🔹 Key should be in bytes
                value=json.dumps(event_data).encode('utf-8'),  # 🔹 Value should be in bytes
                callback=delivery_report  # 🔹 Callback for error handling
            )
            producer.flush()   # 🔹 Non-blocking alternative to flush()
            logger.info("✅ Kafka event sent: %s", event_data)
        except Exception as e:
            logger.error("❌ Error sending Kafka event: %s", e)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        self._send_kafka_event('create', serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        # Find item by name (case-sensitive or case-insensitive)
        item_name = request.data.get('name')

        try:
            # Find the item based on the name
            item = Item.objects.get(name=item_name)
        except Item.DoesNotExist:
            return Response({"detail": "Item not found"}, status=status.HTTP_404_NOT_FOUND)

        # Update the item using the serializer
        serializer = self.get_serializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()

        # Send Kafka event for update
        self._send_kafka_event('update', serializer.data)

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        # Find item by name (case-sensitive or case-insensitive)
        item_name = request.data.get('name')

        try:
            # Find the item based on the name
            item = Item.objects.get(name=item_name)
        except Item.DoesNotExist:
            logger.error("%s", Item.DoesNotExist)
            return Response({"detail": "Item not found"}, status=status.HTTP_404_NOT_FOUND)

        item_data = self.get_serializer(item).data
        self.perform_destroy(item)

        # Send Kafka event for delete
        self._send_kafka_event('delete', item_data)

        return Response(status=status.HTTP_204_NO_CONTENT)
