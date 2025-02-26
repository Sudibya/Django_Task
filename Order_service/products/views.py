import redis
import time
import json
import logging
from confluent_kafka import Producer, KafkaException
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import CustomUser, Item
from .serializers import CustomUserSerializer, ItemSerializer

logger = logging.getLogger(__name__)

# Redis connection (since Redis is installed inside this container, use localhost)
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

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

# Callback function for Kafka message delivery
def delivery_report(err, msg):
    if err is not None:
        logger.error("❌ Kafka delivery failed: %s", err)
    else:
        logger.info("✅ Kafka message delivered to %s [%s]", msg.topic(), msg.partition())

# ViewSet for CustomUser with random ordering
class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

    def get_queryset(self):
        """Return users in random order"""
        return CustomUser.objects.order_by("?")[:1]

# ViewSet for handling Item CRUD operations using confluent_kafka for event publishing
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
                key=b"key.user.event",  # Key should be in bytes
                value=json.dumps(event_data).encode('utf-8'),  # Value should be in bytes
                callback=delivery_report  # Callback for error handling
            )
            producer.flush()
            logger.info("✅ Kafka event sent: %s", event_data)
        except Exception as e:
            logger.error("❌ Error sending Kafka event: %s", e)
            # You can choose to propagate the error or simply log it.

    def _update_like_count(self, item_id):
        """
        Increment the like count for an item in Redis and update the top 3 items.
        """
        # Increment the like count in Redis
        redis_client.zincrby('item_likes', 1, item_id)
        
        # Retrieve the top 3 items with the most likes from Redis
        top_items = redis_client.zrevrange('item_likes', 0, 2)
        
        # Get the item data from the database for the top 3 items
        top_item_data = []
        for redis_item_id in top_items:
            try:
                item = Item.objects.get(id=redis_item_id.decode('utf-8'))
                item_data = ItemSerializer(item).data
                top_item_data.append(item_data)
            except Item.DoesNotExist:
                logger.error(f"Item with ID {redis_item_id.decode('utf-8')} does not exist in the database.")
        
        # Store the top 3 items in Redis
        redis_client.set('top_3_items', json.dumps(top_item_data))
        logger.info(f"Updated top 3 items in Redis: {top_item_data}")

    def like_item(self, request, item_id):
        """
        Like an item, increment the like count, and update the top 3 items in Redis.
        """
        # Validate that the item exists
        try:
            Item.objects.get(id=item_id)
        except Item.DoesNotExist:
            return Response({"error": f"Item {item_id} not found."}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            self._update_like_count(item_id)
        except Exception as e:
            logger.error(f"Error updating like count: {e}")
            return Response({"error": "Error updating like count."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({"message": f"Item {item_id} liked successfully!"}, status=status.HTTP_200_OK)

    def _get_cached_top_items(self):
        """
        Get the top 3 items from Redis.
        """
        cached_top_items = redis_client.get('top_3_items')
        if cached_top_items:
            logger.info("✅ Found top 3 items in cache.")
            return json.loads(cached_top_items)
        return None

    def retrieve(self, request, *args, **kwargs):
        """
        Override retrieve to return top 3 items from Redis first, then from DB after 10 seconds.
        Note: This blocking call (time.sleep(10)) will delay the response.
        """
        cached_items = self._get_cached_top_items()
        response_data = {"cached_data": cached_items or "No cached data available"}

        # Simulate delay (blocking call)
        time.sleep(10)
        
        # Fetch fresh data from the database
        all_items = Item.objects.all()
        all_items_data = ItemSerializer(all_items, many=True).data
        response_data["database_data"] = all_items_data

        return Response(response_data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            item = serializer.save()
        except Exception as e:
            logger.error("Error saving item: %s", e)
            return Response({"error": "Error saving item."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        try:
            self._send_kafka_event('create', serializer.data)
        except Exception as e:
            logger.error("Error sending Kafka event during creation: %s", e)
            # Optionally, handle this error or continue
        
        try:
            self._update_like_count(item.id)  # Update like count when item is created
        except Exception as e:
            logger.error("Error updating like count during creation: %s", e)
            # Optionally, handle this error or continue
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        try:
            item = serializer.save()
        except Exception as e:
            logger.error("Error updating item: %s", e)
            return Response({"error": "Error updating item."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        try:
            self._send_kafka_event('update', serializer.data)
        except Exception as e:
            logger.error("Error sending Kafka event during update: %s", e)
        try:
            self._update_like_count(item.id)  # Update like count when item is updated
        except Exception as e:
            logger.error("Error updating like count during update: %s", e)
        
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        item_data = self.get_serializer(instance).data
        self.perform_destroy(instance)
        try:
            self._send_kafka_event('delete', item_data)
        except Exception as e:
            logger.error("Error sending Kafka event during deletion: %s", e)
        try:
            self._update_like_count(instance.id)  # Update like count when item is deleted
        except Exception as e:
            logger.error("Error updating like count during deletion: %s", e)
        return Response(status=status.HTTP_204_NO_CONTENT)
