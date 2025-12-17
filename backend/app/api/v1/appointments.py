from typing import List, Optional
from uuid import UUID
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi_pagination import Page, paginate

from app.core.database import get_db_session
from app.schemas.appointment import (
    Appointment, AppointmentCreate, AppointmentUpdate,
    AvailableSlot, DailySchedule, DoctorScheduleRequest
)
from app.services.appointment_service import AppointmentService
from app.api.deps import get_current_active_user, get_current_doctor

router = APIRouter(prefix="/appointments", tags=["appointments"])

@router.get("/", response_model=Page[Appointment])
def read_appointments(
    db: Session = Depends(get_db_session),
    skip: int = 0,
    limit: int = 100,
    patient_id: Optional[UUID] = Query(None),
    doctor_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Получить список записей с фильтрацией.
    """
    from app.models.appointment import Appointment as AppointmentModel
    
    query = db.query(AppointmentModel)
    
    # Фильтры
    if patient_id:
        query = query.filter(AppointmentModel.patient_id == patient_id)
    
    if doctor_id:
        query = query.filter(AppointmentModel.doctor_id == doctor_id)
    
    if status:
        query = query.filter(AppointmentModel.status == status)
    
    if start_date:
        query = query.filter(AppointmentModel.scheduled_start >= start_date)
    
    if end_date:
        query = query.filter(AppointmentModel.scheduled_start <= end_date)
    
    # Сортировка по времени
    query = query.order_by(AppointmentModel.scheduled_start.desc())
    
    appointments = query.offset(skip).limit(limit).all()
    return paginate(appointments)

@router.get("/available-slots/{doctor_id}")
def get_available_slots(
    doctor_id: UUID,
    target_date: date = Query(default_factory=date.today),
    duration_minutes: int = Query(30, ge=15, le=120),
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_active_user),
) -> List[AvailableSlot]:
    """
    Получить доступные слоты для записи у врача.
    """
    appointment_service = AppointmentService(db)
    slots = appointment_service.find_available_slots(
        str(doctor_id), target_date, duration_minutes
    )
    
    # Получаем информацию о враче
    from app.models.doctor import Doctor
    doctor = db.query(Doctor).get(doctor_id)
    
    return [
        AvailableSlot(
            start_time=slot,
            end_time=slot + timedelta(minutes=duration_minutes),
            doctor_id=doctor_id,
            doctor_name=f"{doctor.last_name} {doctor.first_name}" if doctor else "Неизвестный врач"
        )
        for slot in slots
    ]

@router.post("/", response_model=Appointment, status_code=status.HTTP_201_CREATED)
def create_appointment(
    appointment_in: AppointmentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Создать новую запись на прием.
    """
    appointment_service = AppointmentService(db)
    
    success, appointment, message = appointment_service.create_appointment(
        patient_id=str(appointment_in.patient_id),
        doctor_id=str(appointment_in.doctor_id),
        scheduled_start=appointment_in.scheduled_start,
        notes=appointment_in.notes,
        appointment_type=appointment_in.appointment_type
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Запускаем фоновую задачу для отправки подтверждения
    from app.tasks.notification_tasks import send_appointment_confirmation
    background_tasks.add_task(
        send_appointment_confirmation,
        appointment_id=str(appointment.id)
    )
    
    return appointment

@router.post("/check-availability")
def check_appointment_availability(
    doctor_id: UUID,
    start_time: datetime,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Проверить доступность врача в указанное время.
    """
    appointment_service = AppointmentService(db)
    
    # Если время окончания не указано, берем стандартную длительность
    if not end_time:
        from app.models.doctor import Doctor
        doctor = db.query(Doctor).get(doctor_id)
        duration = doctor.appointment_duration if doctor else timedelta(minutes=30)
        end_time = start_time + duration
    
    is_available = appointment_service.check_availability(
        str(doctor_id), start_time, end_time
    )
    
    return {
        "doctor_id": doctor_id,
        "start_time": start_time,
        "end_time": end_time,
        "is_available": is_available
    }

@router.put("/{appointment_id}", response_model=Appointment)
def update_appointment(
    appointment_id: UUID,
    appointment_in: AppointmentUpdate,
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Обновить запись на прием.
    """
    from app.models.appointment import Appointment as AppointmentModel
    
    appointment = db.query(AppointmentModel).get(appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена"
        )
    
    # Если меняем время, проверяем доступность
    if appointment_in.scheduled_start:
        appointment_service = AppointmentService(db)
        
        # Получаем длительность записи
        duration = appointment.scheduled_end - appointment.scheduled_start
        
        is_available = appointment_service.check_availability(
            str(appointment.doctor_id),
            appointment_in.scheduled_start,
            appointment_in.scheduled_start + duration,
            exclude_appointment_id=str(appointment_id)
        )
        
        if not is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Новое время занято"
            )
        
        appointment.scheduled_start = appointment_in.scheduled_start
        appointment.scheduled_end = appointment_in.scheduled_start + duration
    
    # Обновляем другие поля
    if appointment_in.status:
        appointment.status = appointment_in.status.value
    
    if appointment_in.reason:
        appointment.reason = appointment_in.reason
    
    if appointment_in.notes:
        appointment.notes = appointment_in.notes
    
    db.commit()
    db.refresh(appointment)
    
    return appointment

@router.post("/doctor-schedule", response_model=dict)
def get_doctor_schedule(
    schedule_request: DoctorScheduleRequest,
    db: Session = Depends(get_db_session),
    current_doctor: dict = Depends(get_current_doctor),
):
    """
    Получить расписание врача на период.
    """
    appointment_service = AppointmentService(db)
    
    schedule = appointment_service.get_doctor_schedule(
        str(schedule_request.doctor_id),
        schedule_request.start_date,
        schedule_request.end_date
    )
    
    return schedule

@router.post("/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: UUID,
    reason: Optional[str] = None,
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Отменить запись на прием.
    """
    from app.models.appointment import Appointment as AppointmentModel, AppointmentStatus
    
    appointment = db.query(AppointmentModel).get(appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена"
        )
    
    # Проверяем что запись можно отменить
    if appointment.status not in [
        AppointmentStatus.SCHEDULED.value,
        AppointmentStatus.CONFIRMED.value
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невозможно отменить запись с текущим статусом"
        )
    
    # Обновляем статус
    appointment.status = AppointmentStatus.CANCELLED.value
    if reason:
        appointment.notes = f"{appointment.notes or ''}\nОтменено: {reason}"
    
    db.commit()
    
    # Отправляем уведомление об отмене
    from app.tasks.notification_tasks import send_appointment_cancellation
    send_appointment_cancellation.delay(str(appointment_id))
    
    return {"message": "Запись успешно отменена"}

@router.get("/upcoming")
def get_upcoming_appointments(
    days_ahead: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_active_user),
) -> List[Appointment]:
    """
    Получить предстоящие записи.
    """
    from app.models.appointment import Appointment as AppointmentModel
    from datetime import datetime
    
    now = datetime.now()
    future_date = now + timedelta(days=days_ahead)
    
    appointments = db.query(AppointmentModel).filter(
        AppointmentModel.scheduled_start >= now,
        AppointmentModel.scheduled_start <= future_date,
        AppointmentModel.status.in_([
            AppointmentStatus.SCHEDULED.value,
            AppointmentStatus.CONFIRMED.value
        ])
    ).order_by(AppointmentModel.scheduled_start).all()
    
    return appointments