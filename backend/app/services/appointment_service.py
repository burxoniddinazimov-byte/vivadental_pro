from datetime import datetime, timedelta, date, time
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, not_, func
from sqlalchemy.exc import IntegrityError
import pytz
from redis.lock import Lock

from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor import Doctor
from app.core.redis_client import redis_client

class AppointmentService:
    """Сервис управления записями (решаю проблему дублирования записей из Vivad2.0)"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_availability(
        self,
        doctor_id: str,
        start_time: datetime,
        end_time: datetime,
        exclude_appointment_id: Optional[str] = None
    ) -> bool:
        """
        Проверка доступности врача в указанное время.
        Исправляю race condition из VIVAD с помощью Redis Lock.
        """
        # Получаем блокировку для этого врача и времени
        lock_key = f"appointment_lock:{doctor_id}:{start_time.timestamp()}"
        
        try:
            # Пытаемся получить блокировку (таймаут 5 секунд)
            with redis_client.lock(lock_key, timeout=5, blocking_timeout=5):
                # Проверяем рабочее время врача
                doctor = self.db.query(Doctor).get(doctor_id)
                if not doctor or not doctor.is_active:
                    return False
                
                # Проверяем рабочий день
                day_of_week = start_time.strftime('%A').lower()
                if not doctor.is_available_on_day(day_of_week):
                    return False
                
                # Проверяем рабочее время
                work_start_str, work_end_str = doctor.get_work_hours(day_of_week)
                if not work_start_str or not work_end_str:
                    return False
                
                work_start = datetime.combine(start_time.date(), 
                                            time.fromisoformat(work_start_str))
                work_end = datetime.combine(start_time.date(), 
                                          time.fromisoformat(work_end_str))
                
                if start_time < work_start or end_time > work_end:
                    return False
                
                # Проверяем перерыв
                schedule = doctor.work_schedule.get(day_of_week)
                if schedule.get("break"):
                    break_start_str, break_end_str = schedule["break"].split("-")
                    break_start = datetime.combine(start_time.date(), 
                                                 time.fromisoformat(break_start_str))
                    break_end = datetime.combine(start_time.date(), 
                                               time.fromisoformat(break_end_str))
                    
                    if (start_time < break_end and end_time > break_start):
                        return False
                
                # Проверяем существующие записи (исправляю ошибку логики из vivag3.0)
                query = self.db.query(Appointment).filter(
                    Appointment.doctor_id == doctor_id,
                    Appointment.status.in_([
                        AppointmentStatus.SCHEDULED.value,
                        AppointmentStatus.CONFIRMED.value
                    ]),
                    # Проверяем пересечение временных интервалов
                    and_(
                        Appointment.scheduled_start < end_time,
                        Appointment.scheduled_end > start_time
                    )
                )
                
                if exclude_appointment_id:
                    query = query.filter(Appointment.id != exclude_appointment_id)
                
                conflicting_appointments = query.count()
                
                return conflicting_appointments == 0
                
        except Exception as e:
            # Если не удалось получить блокировку, считаем что время занято
            print(f"Error checking availability: {e}")
            return False
    
    def find_available_slots(
        self,
        doctor_id: str,
        target_date: date,
        duration_minutes: int = 30
    ) -> List[datetime]:
        """
        Поиск всех доступных слотов у врача на указанную дату.
        Исправляю ошибку неправильного расчета слотов из Vivad2.0.
        """
        doctor = self.db.query(Doctor).get(doctor_id)
        if not doctor or not doctor.is_active:
            return []
        
        # Получаем расписание врача на этот день
        day_of_week = target_date.strftime('%A').lower()
        schedule = doctor.work_schedule.get(day_of_week)
        
        if not schedule or not schedule.get("start") or not schedule.get("end"):
            return []
        
        # Парсим рабочее время
        work_start = datetime.combine(target_date, 
                                    time.fromisoformat(schedule["start"]))
        work_end = datetime.combine(target_date, 
                                  time.fromisoformat(schedule["end"]))
        
        # Парсим время перерыва
        break_start = None
        break_end = None
        if schedule.get("break"):
            break_start_str, break_end_str = schedule["break"].split("-")
            break_start = datetime.combine(target_date, 
                                         time.fromisoformat(break_start_str))
            break_end = datetime.combine(target_date, 
                                       time.fromisoformat(break_end_str))
        
        # Получаем существующие записи
        existing_appointments = self.db.query(Appointment).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.scheduled_start >= work_start,
            Appointment.scheduled_start <= work_end,
            Appointment.status.in_([
                AppointmentStatus.SCHEDULED.value,
                AppointmentStatus.CONFIRMED.value
            ])
        ).order_by(Appointment.scheduled_start).all()
        
        # Генерируем слоты
        slots = []
        current_time = work_start
        slot_duration = timedelta(minutes=duration_minutes)
        
        while current_time + slot_duration <= work_end:
            slot_end = current_time + slot_duration
            
            # Пропускаем перерыв
            if break_start and break_end:
                if current_time < break_end and slot_end > break_start:
                    current_time = break_end
                    continue
            
            # Проверяем конфликты с существующими записями
            has_conflict = False
            for appointment in existing_appointments:
                if (current_time < appointment.scheduled_end and 
                    slot_end > appointment.scheduled_start):
                    has_conflict = True
                    # Перескакиваем на время после этой записи
                    current_time = appointment.scheduled_end
                    break
            
            if not has_conflict:
                slots.append(current_time)
                current_time += slot_duration
            else:
                # Продолжаем с текущего времени (уже обновлено в цикле)
                continue
        
        return slots
    
    def create_appointment(
        self,
        patient_id: str,
        doctor_id: str,
        scheduled_start: datetime,
        notes: Optional[str] = None,
        appointment_type: Optional[str] = None
    ) -> Tuple[bool, Appointment, str]:
        """
        Создание записи с проверкой доступности и транзакцией.
        Решаю проблему потери данных при конфликтах из VIVAD.
        """
        # Рассчитываем время окончания
        doctor = self.db.query(Doctor).get(doctor_id)
        if not doctor:
            return False, None, "Врач не найден"
        
        duration = doctor.appointment_duration or timedelta(minutes=30)
        scheduled_end = scheduled_start + duration
        
        # Проверяем доступность с блокировкой
        if not self.check_availability(doctor_id, scheduled_start, scheduled_end):
            return False, None, "Время занято или врач недоступен"
        
        try:
            # Создаем запись в транзакции
            appointment = Appointment(
                patient_id=patient_id,
                doctor_id=doctor_id,
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end,
                notes=notes,
                appointment_type=appointment_type,
                status=AppointmentStatus.SCHEDULED.value
            )
            
            self.db.add(appointment)
            self.db.commit()
            self.db.refresh(appointment)
            
            # Планируем напоминания
            self._schedule_reminders(appointment)
            
            return True, appointment, "Запись создана успешно"
            
        except IntegrityError as e:
            self.db.rollback()
            return False, None, f"Ошибка создания записи: {str(e)}"
    
    def _schedule_reminders(self, appointment: Appointment):
        """Планирование напоминаний о записи"""
        from app.tasks.notification_tasks import send_appointment_reminder
        
        # Напоминание за 24 часа
        reminder_time = appointment.scheduled_start - timedelta(hours=24)
        if reminder_time > datetime.now():
            send_appointment_reminder.apply_async(
                args=[appointment.id, '24h'],
                eta=reminder_time
            )
        
        # Напоминание за 2 часа
        reminder_time = appointment.scheduled_start - timedelta(hours=2)
        if reminder_time > datetime.now():
            send_appointment_reminder.apply_async(
                args=[appointment.id, '2h'],
                eta=reminder_time
            )
    
    def update_appointment_status(
        self,
        appointment_id: str,
        status: AppointmentStatus,
        notes: Optional[str] = None
    ) -> bool:
        """Обновление статуса записи"""
        appointment = self.db.query(Appointment).get(appointment_id)
        if not appointment:
            return False
        
        appointment.status = status.value
        if notes:
            appointment.notes = notes
        
        # Если запись завершена, обновляем время фактического окончания
        if status == AppointmentStatus.COMPLETED:
            appointment.actual_end = datetime.now()
        
        self.db.commit()
        return True
    
    def get_doctor_schedule(
        self,
        doctor_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Получение расписания врача на период.
        Исправляю ошибку производительности из vivag3.0.
        """
        appointments = self.db.query(Appointment).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.scheduled_start >= start_date,
            Appointment.scheduled_start <= end_date
        ).order_by(Appointment.scheduled_start).all()
        
        # Группируем по дням для удобства отображения
        schedule_by_day = {}
        current_date = start_date
        
        while current_date <= end_date:
            day_appointments = [
                appt for appt in appointments 
                if appt.scheduled_start.date() == current_date
            ]
            schedule_by_day[current_date.isoformat()] = day_appointments
            current_date += timedelta(days=1)
        
        return {
            "doctor_id": doctor_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "schedule": schedule_by_day
        }