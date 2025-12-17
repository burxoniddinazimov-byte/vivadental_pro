import logging
import sys
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler
import structlog
from pythonjsonlogger import jsonlogger

def setup_logging():
    """Настройка структурированного логирования"""
    
    # Удаляем стандартные обработчики
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Настройка формата для JSON логов
    class CustomJsonFormatter(jsonlogger.JsonFormatter):
        def add_fields(self, log_record, record, message_dict):
            super().add_fields(log_record, record, message_dict)
            
            # Добавляем стандартные поля
            log_record['timestamp'] = datetime.utcnow().isoformat()
            log_record['level'] = record.levelname
            log_record['logger'] = record.name
            
            # Добавляем дополнительные поля
            if hasattr(record, 'request_id'):
                log_record['request_id'] = record.request_id
            
            if hasattr(record, 'user_id'):
                log_record['user_id'] = record.user_id
            
            if hasattr(record, 'endpoint'):
                log_record['endpoint'] = record.endpoint
            
            # Удаляем лишние поля
            log_record.pop('message', None)
            log_record.pop('asctime', None)
    
    # Создаем обработчик для файла
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=10,
        encoding='utf-8'
    )
    
    file_handler.setFormatter(CustomJsonFormatter())
    
    # Создаем обработчик для консоли (для разработки)
    console_handler = logging.StreamHandler(sys.stdout)
    
    if settings.ENVIRONMENT == 'production':
        console_handler.setFormatter(CustomJsonFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
    
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Настраиваем логгер для конкретных библиотек
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    
    # Настройка structlog для дополнительного контекста
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger()

# Глобальный логгер
logger = setup_logging()

# Декоратор для логирования запросов
def log_request():
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            request_id = request.headers.get('X-Request-ID', 'N/A')
            user_id = getattr(request.state, 'user_id', 'anonymous')
            
            # Логируем начало запроса
            logger.info(
                "Request started",
                request_id=request_id,
                user_id=user_id,
                method=request.method,
                endpoint=request.url.path,
                client_ip=request.client.host,
                user_agent=request.headers.get('user-agent')
            )
            
            start_time = time.time()
            
            try:
                response = await func(request, *args, **kwargs)
                
                # Логируем успешное завершение
                duration = time.time() - start_time
                logger.info(
                    "Request completed",
                    request_id=request_id,
                    user_id=user_id,
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=response.status_code,
                    duration=duration
                )
                
                return response
                
            except Exception as e:
                # Логируем ошибку
                duration = time.time() - start_time
                logger.error(
                    "Request failed",
                    request_id=request_id,
                    user_id=user_id,
                    method=request.method,
                    endpoint=request.url.path,
                    error=str(e),
                    duration=duration,
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator

# Контекстный менеджер для логирования бизнес-событий
class BusinessEventLogger:
    def __init__(self, event_type: str, user_id: str = None):
        self.event_type = event_type
        self.user_id = user_id
        self.start_time = time.time()
        self.logger = logger.bind(event_type=event_type, user_id=user_id)
    
    def __enter__(self):
        self.logger.info(f"{self.event_type} started")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type:
            self.logger.error(
                f"{self.event_type} failed",
                duration=duration,
                error=str(exc_val)
            )
        else:
            self.logger.info(
                f"{self.event_type} completed",
                duration=duration
            )
    
    def log_step(self, step: str, data: dict = None):
        """Логирование шага внутри события"""
        self.logger.info(f"{self.event_type} step: {step}", step_data=data or {})