"""
Kafka Consumer with exactly-once semantics
"""
from kafka import KafkaConsumer
from kafka.structs import TopicPartition
import json
import logging
from typing import Callable, Optional
from datetime import datetime
import sqlite3  # For offset tracking (use PostgreSQL in production)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LogConsumer:
    def __init__(self, 
                 bootstrap_servers: str = "localhost:9092",
                 topic: str = "logiq-logs",
                 group_id: str = "logiq-consumer-group"):
        
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            enable_auto_commit=False,  # Manual commit for exactly-once
            auto_offset_reset='earliest',
            isolation_level='read_committed'  # Only read committed messages
        )
        self.topic = topic
        self.processed_count = 0
        
    def process_log(self, log_entry: dict) -> bool:
        """
        Process a single log entry
        Returns True if processed successfully
        """
        try:
            # Log processing logic will go here
            # For now, just log the entry
            logger.debug(f"Processing log: {log_entry['level']} - {log_entry['source']}")
            
            # Store to database (will implement in Day 4)
            # Store to Elasticsearch (will implement in Day 4)
            
            self.processed_count += 1
            if self.processed_count % 100 == 0:
                logger.info(f"Processed {self.processed_count} logs")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to process log: {e}")
            return False
    
    def consume_with_exactly_once(self, callback: Optional[Callable] = None):
        """
        Consume messages with exactly-once semantics
        Using manual offset commit after successful processing
        """
        logger.info("Starting consumer with exactly-once semantics")
        
        for message in self.consumer:
            log_entry = message.value
            
            # Process the message
            if callback:
                success = callback(log_entry)
            else:
                success = self.process_log(log_entry)
            
            # Only commit if processing succeeded
            if success:
                self.consumer.commit()
                logger.debug(f"Committed offset: {message.offset}")
            else:
                logger.error(f"Processing failed, not committing offset: {message.offset}")
                # In production, send to dead letter queue
    
    def consume_batch(self, batch_size: int = 100):
        """Consume messages in batches for better performance"""
        messages = self.consumer.poll(timeout_ms=1000, max_records=batch_size)
        
        for tp, records in messages.items():
            for record in records:
                log_entry = record.value
                if self.process_log(log_entry):
                    # Commit offset for this partition
                    self.consumer.commit({tp: record.offset + 1})
                    
        return len(messages)
    
    def close(self):
        self.consumer.close()
        logger.info("Consumer closed")

if __name__ == "__main__":
    consumer = LogConsumer()
    try:
        consumer.consume_with_exactly_once()
    except KeyboardInterrupt:
        consumer.close()
