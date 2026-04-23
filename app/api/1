from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..core.database import get_db
import redis
from kafka import KafkaProducer
from ..core.config import settings

router = APIRouter()

@router.get("/")
async def health_check(db: Session = Depends(get_db)):
    health_status = {
        "api": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "kafka": "unknown"
    }
    
    # Check database
    try:
        db.execute("SELECT 1")
        health_status["database"] = "healthy"
    except Exception as e:
        health_status["database"] = f"unhealthy: {str(e)}"
    
    # Check Redis
    try:
        r = redis.Redis.from_url(settings.REDIS_URL)
        r.ping()
        health_status["redis"] = "healthy"
    except Exception as e:
        health_status["redis"] = f"unhealthy: {str(e)}"
    
    # Check Kafka
    try:
        producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            request_timeout_ms=1000
        )
        health_status["kafka"] = "healthy"
        producer.close()
    except Exception as e:
        health_status["kafka"] = f"unhealthy: {str(e)}"
    
    return health_status
