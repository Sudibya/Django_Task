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

# Redis connection
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)  # Update Redis host and port as necessary

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
        for item_id in top_items:
            try:
                item = Item.objects.get(id=item_id.decode('utf-8'))  # Decode item_id from Redis byte format
                item_data = ItemSerializer(item).data
                top_item_data.append(item_data)
            except Item.DoesNotExist:
                logger.error(f"Item with ID {item_id.decode('utf-8')} does not exist in the database.")
        
        # Store the top 3 items in Redis
        redis_client.set('top_3_items', json.dumps(top_item_data))
        logger.info(f"Updated top 3 items in Redis: {top_item_data}")

    def like_item(self, request, item_id):
        """
        Like an item, increment the like count, and update the top 3 items in Redis.
        """
        # Increment the like count
        self._update_like_count(item_id)
        
        # Return the response
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
        """
        cached_items = self._get_cached_top_items()

        if cached_items:
            # Return top 3 items from Redis immediately
            response_data = {"cached_data": cached_items}
        else:
            # If not found in Redis, fall back to DB query and cache it
            response_data = {"cached_data": "No cached data available"}

        # Wait 10 seconds before returning data from the DB
        time.sleep(10)
        
        # Fetch data from the DB (for fallback if Redis was empty or for fresh data)
        all_items = Item.objects.all()
        all_items_data = ItemSerializer(all_items, many=True).data
        response_data["database_data"] = all_items_data

        return Response(response_data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        self._send_kafka_event('create', serializer.data)
        self._update_like_count(item.id)  # Update like count when item is created
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Update an existing item and send a Kafka event"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()  # Get the item from the database
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()  # Save the updated item
        self._send_kafka_event('update', serializer.data)  # Send Kafka event
        self._update_like_count(item.id)  # Update like count when item is updated
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Delete an existing item and send a Kafka event"""
        instance = self.get_object()  # Get the item from the database
        item_data = self.get_serializer(instance).data  # Get the data to send to Kafka
        self.perform_destroy(instance)  # Actually delete the item
        self._send_kafka_event('delete', item_data)  # Send Kafka event
        self._update_like_count(instance.id)  # Update like count when item is deleted
        return Response(status=status.HTTP_204_NO_CONTENT)
