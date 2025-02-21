from confluent_kafka import Consumer, KafkaException, KafkaError
import json
import logging
import signal
import sys
import os
import django

# 🔹 Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customer_service.settings')
django.setup()

from orders.models import ItemCopy  # Import ItemCopy model
from orders.serializers import ItemCopySerializer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flag to indicate when to exit
running = True

def shutdown_signal_handler(signum, frame):
    global running
    logger.info("Shutdown signal received. Exiting consumer loop...")
    running = False

# Register the signal handlers for graceful shutdown
signal.signal(signal.SIGINT, shutdown_signal_handler)
signal.signal(signal.SIGTERM, shutdown_signal_handler)

# Initialize Kafka Consumer
consumer = Consumer({
    'bootstrap.servers': 'kafka:9092',  # Kafka broker address
    'group.id': 'customer_service_group',  # Consumer group ID
    'auto.offset.reset': 'earliest',  # Start reading from the earliest message
    'enable.auto.commit': True  # Ensure auto-commit is enabled
})

logger.info("Starting Kafka consumer...")

# Subscribe to topic
consumer.subscribe(['items_topic'])
logger.info("Successfully subscribed to topic: items_topic")

# Consume messages until a shutdown signal is received
while running:
    try:
        msg = consumer.poll(timeout=1.0)  # Poll for new messages with a timeout of 1 second
        
        if msg is None:  # No message available within the timeout
            logger.info("No new messages, polling again...")
            continue

        if msg.error():  # Handle any errors
            if msg.error().code() == KafkaError._PARTITION_EOF:
                logger.info(f"End of partition reached {msg.partition()} at offset {msg.offset()}")
            else:
                logger.error(f"Consumer error: {msg.error()}")
                raise KafkaException(msg.error())
        else:
            # Decode and process the message
            item_data = msg.value().decode('utf-8')
            logger.info(f"Received item data: {item_data}")

            # Ensure the message is valid JSON
            try:
                item_data_json = json.loads(item_data)  # Convert to JSON
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON decode error: {e}")
                continue

            # Action from the Kafka message
            action = item_data_json.get('action', None)
            
            if action == 'create' or action == 'update':
                # Create or update the item as per previous logic
                item_id = item_data_json.get('item', {}).get('id', None)
                
                if item_id:
                    # Try to get the existing item from the database by ID
                    try:
                        item_copy = ItemCopy.objects.get(id=item_id)
                        logger.info(f"✅ Found item to {action}: {item_copy.name}")
                        
                        # Use the serializer to create or update the item
                        serializer = ItemCopySerializer(item_copy, data=item_data_json.get('item', {}), partial=True)
                        if serializer.is_valid():
                            # Save item (either create or update)
                            item_copy = serializer.save()
                            logger.info(f"✅ Item {action}d: {item_copy.name}")
                        else:
                            logger.error("❌ Invalid data for update: %s", serializer.errors)
                    except ItemCopy.DoesNotExist:
                        if action == 'create':
                            logger.warning(f"❌ Item with ID {item_id} does not exist. Creating a new item.")
                            serializer = ItemCopySerializer(data=item_data_json.get('item', {}))
                            if serializer.is_valid():
                                item_copy = serializer.save()
                                logger.info(f"✅ Item created: {item_copy.name}")
                            else:
                                logger.error("❌ Invalid data for creation: %s", serializer.errors)
                        else:
                            logger.warning(f"❌ Item with ID {item_id} does not exist and cannot be updated.")
                else:
                    logger.error("❌ Item ID is missing in the message.")

            elif action == 'delete':
                # Handle delete action
                item_id = item_data_json.get('item', {}).get('id', None)
                if item_id:
                    try:
                        item_copy = ItemCopy.objects.get(id=item_id)
                        logger.info(f"✅ Found item to delete: {item_copy.name}")
                        item_copy.delete()  # Delete the item
                        logger.info(f"✅ Item deleted: {item_copy.name}")
                    except ItemCopy.DoesNotExist:
                        logger.error(f"❌ Item with ID {item_id} does not exist. Cannot delete.")
                else:
                    logger.error("❌ Item ID is missing for delete operation.")
            else:
                logger.error(f"❌ Unknown action: {action}")

    except Exception as e:
        logger.error(f"Error processing message: {e}")

# Closing the consumer when exiting
consumer.close()
logger.info("Kafka Consumer has stopped.")
sys.exit(0)
