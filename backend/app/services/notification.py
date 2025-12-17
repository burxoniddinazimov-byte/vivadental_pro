import asyncio
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from celery import Celery

from app.core.config import settings
from app.models.appointment import Appointment

# Настройка Celery
celery_app = Celery(
    'vivadental',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

@celery_app.task
def send_sms_reminder(phone: str, message: str):
    """Отправка SMS напоминания"""
    # Интеграция с SMS сервисом
    # Например, Twilio или smsc.ru
    print(f"SMS to {phone}: {message}")
    return True

@celery_app.task
def send_email_reminder(email: str, subject: str, message: str):
    """Отправка email напоминания"""
    # Интеграция с email сервисом
    print(f"Email to {email}: {subject} - {message}")
    return True

class NotificationService:
    def __init__(self, db: Session):
        self.db = db
    
    def schedule_appointment_reminders(self, appointment_id: str):
        """Планирование напоминаний о записи"""
        appointment = self.db.query(Appointment).get(appointment_id)
        if not appointment:
            return
        
        # За 24 часа
        send_time = appointment.scheduled_start - timedelta(hours=24)
        if appointment.patient.phone:
            send_sms_reminder.apply_async(
                args=[appointment.patient.phone, f"Напоминание о записи на {appointment.scheduled_start}"],
                eta=send_time
            )
        
        # За 2 часа
        send_time = appointment.scheduled_start - timedelta(hours=2)
        if appointment.patient.phone:
            send_sms_reminder.apply_async(
                args=[appointment.patient.phone, f"До вашей записи осталось 2 часа"],
                eta=send_time
            )