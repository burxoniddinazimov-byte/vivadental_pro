import redis
from redis.lock import Lock
from typing import Optional
import pickle
import json
from datetime import timedelta

from app.core.config import settings

# Создаем подключение к Redis
redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=False,  # Для pickle объектов
    socket_timeout=5,
    socket_connect_timeout=5,
    retry_on_timeout=True
)

class RedisService:
    """Сервис для работы с Redis (кэш, блокировки, очереди)"""
    
    @staticmethod
    def get_lock(key: str, timeout: int = 10) -> Lock:
        """Получение блокировки для предотвращения race condition"""
        return redis_client.lock(
            f"lock:{key}",
            timeout=timeout,
            blocking_timeout=timeout
        )
    
    @staticmethod
    def cache_get(key: str) -> Optional[Any]:
        """Получение данных из кэша"""
        try:
            data = redis_client.get(f"cache:{key}")
            if data:
                return pickle.loads(data)
        except Exception:
            pass
        return None
    
    @staticmethod
    def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
        """Сохранение данных в кэш"""
        try:
            redis_client.setex(
                f"cache:{key}",
                ttl,
                pickle.dumps(value)
            )
            return True
        except Exception:
            return False
    
    @staticmethod
    def invalidate_pattern(pattern: str) -> None:
        """Инвалидация кэша по паттерну"""
        keys = redis_client.keys(f"cache:{pattern}")
        if keys:
            redis_client.delete(*keys)