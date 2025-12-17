from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date, time
from uuid import UUID
import enum

from app.models.appointment import AppointmentStatus

class AppointmentBase(BaseModel):
    patient_id: UUID
    doctor_id: UUID
    scheduled_start: datetime
    appointment_type: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None

class AppointmentCreate(AppointmentBase):
    @validator('scheduled_start')
    def validate_scheduled_start(cls, v):
        if v < datetime.now():
            raise ValueError('Время записи не может быть в прошлом')
        
        # Проверяем что это рабочее время (не ночь)
        if v.hour < 8 or v.hour > 20:
            raise ValueError('Запись возможна только с 8:00 до 20:00')
        
        # Проверяем что это не выходной
        if v.weekday() >= 5:  # Суббота или воскресенье
            # Можно сделать исключения через конфиг
            pass
        
        # Округляем до 15 минут
        minute = v.minute
        if minute % 15 != 0:
            rounded_minute = (minute // 15) * 15
            v = v.replace(minute=rounded_minute, second=0, microsecond=0)
        
        return v

class AppointmentUpdate(BaseModel):
    scheduled_start: Optional[datetime] = None
    status: Optional[AppointmentStatus] = None
    reason: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None

class Appointment(AppointmentBase):
    id: UUID
    scheduled_end: datetime
    status: AppointmentStatus
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AvailableSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    doctor_id: UUID
    doctor_name: str

class DailySchedule(BaseModel):
    date: date
    appointments: List[Appointment]
    available_slots: List[AvailableSlot]

class DoctorScheduleRequest(BaseModel):
    doctor_id: UUID
    start_date: date
    end_date: date = Field(default_factory=date.today)
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('Дата окончания должна быть позже даты начала')
        if (v - values['start_date']).days > 30:
            raise ValueError('Максимальный период - 30 дней')
        return v