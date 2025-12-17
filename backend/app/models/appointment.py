from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, INTERVAL
import uuid
import enum
from .base import Base, TimestampMixin

class AppointmentStatus(enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

class Appointment(Base, TimestampMixin):
    __tablename__ = "appointments"
    
    # Основные поля
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    
    # Время (исправляю ошибку с таймзонами из VIVAD)
    scheduled_start = Column(DateTime(timezone=True), nullable=False, index=True)
    scheduled_end = Column(DateTime(timezone=True), nullable=False)
    actual_start = Column(DateTime(timezone=True))
    actual_end = Column(DateTime(timezone=True))
    
    # Статус и тип
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED, index=True)
    appointment_type = Column(String(50))  # consultation, treatment, cleaning, etc.
    
    # Описание
    reason = Column(Text)
    diagnosis = Column(Text)
    treatment_plan = Column(Text)
    notes = Column(Text)
    
    # Связи
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    services = relationship("AppointmentService", back_populates="appointment",
                           cascade="all, delete-orphan")
    
    # Оптимизации для поиска свободных окон
    __table_args__ = (
        Index('ix_appointments_doctor_time', 'doctor_id', 'scheduled_start'),
        Index('ix_appointments_status_time', 'status', 'scheduled_start'),
    )
    
    # Методы для бизнес-логики
    def is_available(self):
        return self.status in [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]
    
    def duration(self):
        if self.actual_start and self.actual_end:
            return self.actual_end - self.actual_start
        return self.scheduled_end - self.scheduled_start