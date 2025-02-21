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

            # Use the ItemCopySerializer to validate and create the ItemCopy instance
            serializer = ItemCopySerializer(data=item_data_json.get('item', {}))
            
            if serializer.is_valid():
                # Save directly to the database
                item_copy = serializer.save()  # This saves the instance directly
                logger.info(f"✅ Item successfully saved: {item_copy.name}")
            else:
                logger.error("❌ Invalid item data: %s", serializer.errors)

    except Exception as e:
        logger.error(f"Error processing message: {e}")

# Closing the consumer when exiting
consumer.close()
logger.info("Kafka Consumer has stopped.")
sys.exit(0)
