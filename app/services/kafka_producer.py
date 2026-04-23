"""
Kafka Producer for Log Ingestion
Generates 10,000 logs per minute for testing
"""
from kafka import KafkaProducer
import json
import time
import random
from datetime import datetime
from typing import Dict, Any
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LogProducer:
    def __init__(self, bootstrap_servers: str = "localhost:9092", topic: str = "logiq-logs"):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=3,
            enable_idempotence=True
        )
        self.topic = topic
        self.running = False
        
        self.log_templates = [
            {"level": "ERROR", "message": "Database connection failed: timeout after {timeout}s", "source": "database"},
            {"level": "WARNING", "message": "High memory usage detected: {percent}%", "source": "monitoring"},
            {"level": "INFO", "message": "User {user_id} logged in successfully", "source": "auth"},
            {"level": "DEBUG", "message": "Processing request {request_id} took {duration}ms", "source": "api"},
            {"level": "CRITICAL", "message": "Service {service_name} is down!", "source": "orchestrator"},
            {"level": "ERROR", "message": "Payment processing failed for order {order_id}", "source": "payment"},
            {"level": "INFO", "message": "Backup completed: {size}MB in {duration}s", "source": "backup"},
            {"level": "WARNING", "message": "Rate limit exceeded for API key {api_key}", "source": "gateway"},
        ]
        
    def generate_log(self) -> Dict[str, Any]:
        """Generate a single log entry"""
        template = random.choice(self.log_templates)
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": template["level"],
            "source": template["source"],
            "message": template["message"].format(
                timeout=random.randint(5, 60),
                percent=random.randint(70, 99),
                user_id=f"user_{random.randint(1, 1000)}",
                request_id=f"req_{random.randint(1000, 9999)}",
                duration=random.randint(10, 500),
                service_name=random.choice(["payment", "auth", "inventory", "shipping"]),
                order_id=f"ORD-{random.randint(10000, 99999)}",
                size=random.randint(10, 1000),
                api_key=f"key_{random.randint(1, 100)}"
            ),
            "metadata": {
                "host": f"server-{random.randint(1, 10)}",
                "environment": random.choice(["prod", "staging", "dev"]),
                "trace_id": f"trace_{random.randint(1000, 9999)}"
            }
        }
        return log_entry
    
    def produce_logs(self, logs_per_minute: int = 10000):
        """Produce logs at specified rate"""
        delay = 60.0 / logs_per_minute
        self.running = True
        count = 0
        
        logger.info(f"Starting log production: {logs_per_minute} logs/min (delay={delay:.4f}s)")
        
        while self.running:
            log_entry = self.generate_log()
            
            try:
                future = self.producer.send(self.topic, log_entry)
                record_metadata = future.get(timeout=10)
                count += 1
                
                if count % 1000 == 0:
                    logger.info(f"Produced {count} logs")
                    
            except Exception as e:
                logger.error(f"Failed to send log: {e}")
                
            time.sleep(delay)
    
    def produce_batch(self, batch_size: int = 1000):
        """Produce a batch of logs at once"""
        logs = [self.generate_log() for _ in range(batch_size)]
        
        for log in logs:
            self.producer.send(self.topic, log)
        
        self.producer.flush()
        logger.info(f"Produced batch of {batch_size} logs")
        
    def stop(self):
        self.running = False
        self.producer.close()
        logger.info("Producer stopped")

if __name__ == "__main__":
    producer = LogProducer()
    try:
        producer.produce_logs(logs_per_minute=1000)
    except KeyboardInterrupt:
        producer.stop()
