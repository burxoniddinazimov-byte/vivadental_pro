from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

from app.core.config import settings
from app.models.appointment import Appointment
from app.models.patient import Patient

# Настройка Celery
celery_app = Celery(
    'vivadental_tasks',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Создаем сессию БД для задач
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@celery_app.task
def send_appointment_confirmation(appointment_id: str):
    """Отправка подтверждения записи"""
    db = SessionLocal()
    try:
        appointment = db.query(Appointment).get(appointment_id)
        if not appointment:
            return
        
        patient = appointment.patient
        if not patient:
            return
        
        # Отправка SMS
        if patient.phone:
            send_sms(
                phone=patient.phone,
                message=f"Запись подтверждена на {appointment.scheduled_start.strftime('%d.%m.%Y %H:%M')}"
            )
        
        # Отправка email
        if patient.email:
            send_email(
                to_email=patient.email,
                subject="Подтверждение записи",
                body=f"""
                Уважаемый(ая) {patient.first_name} {patient.last_name}!
                
                Ваша запись на прием подтверждена.
                
                Дата: {appointment.scheduled_start.strftime('%d.%m.%Y')}
                Время: {appointment.scheduled_start.strftime('%H:%M')}
                Врач: {appointment.doctor.last_name} {appointment.doctor.first_name}
                
                Просим прибыть за 10 минут до назначенного времени.
                """
            )
            
    finally:
        db.close()

@celery_app.task
def send_appointment_reminder(appointment_id: str, reminder_type: str):
    """Отправка напоминания о записи"""
    db = SessionLocal()
    try:
        appointment = db.query(Appointment).get(appointment_id)
        if not appointment or appointment.status != 'scheduled':
            return
        
        patient = appointment.patient
        if not patient:
            return
        
        if reminder_type == '24h':
            message = f"Напоминание: завтра в {appointment.scheduled_start.strftime('%H:%M')} прием у врача"
        else:  # '2h'
            message = f"Через 2 часа прием у врача в {appointment.scheduled_start.strftime('%H:%M')}"
        
        if patient.phone:
            send_sms(patient.phone, message)
            
    finally:
        db.close()

def send_sms(phone: str, message: str):
    """Отправка SMS (интеграция с SMS-шлюзом)"""
    # Пример для smsc.ru
    try:
        response = requests.post(
            "https://smsc.ru/sys/send.php",
            params={
                'login': settings.SMSC_LOGIN,
                'psw': settings.SMSC_PASSWORD,
                'phones': phone,
                'mes': message,
                'charset': 'utf-8',
                'fmt': 3  # JSON ответ
            }
        )
        return response.json()
    except Exception:
        # Логируем ошибку
        pass

def send_email(to_email: str, subject: str, body: str):
    """Отправка email"""
    if not all([settings.SMTP_HOST, settings.SMTP_PORT, 
                settings.SMTP_USER, settings.SMTP_PASSWORD]):
        return
    
    try:
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            
    except Exception:
        # Логируем ошибку
        pass