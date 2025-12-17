from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, or_
from collections import defaultdict

from app.core.database import get_db_session
from app.api.deps import get_current_active_user
from app.models.appointment import Appointment, AppointmentStatus
from app.models.patient import Patient
from app.models.finance import FinancialRecord, PaymentStatus

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/stats")
def get_dashboard_stats(
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Получить статистику для дашборда.
    """
    # Статистика записей
    appointment_stats = db.query(
        func.count(Appointment.id).label('total'),
        func.sum(case([(Appointment.status == 'completed', 1)], else_=0)).label('completed'),
        func.sum(case([(Appointment.status == 'cancelled', 1)], else_=0)).label('cancelled'),
        func.sum(case([(Appointment.status == 'no_show', 1)], else_=0)).label('no_show'),
    ).filter(
        Appointment.scheduled_start >= start_date,
        Appointment.scheduled_start <= end_date
    ).first()
    
    # Статистика пациентов
    patient_stats = db.query(
        func.count(Patient.id).label('total'),
        func.sum(case([(Patient.is_active == True, 1)], else_=0)).label('active'),
        func.count(distinct(
            case([(Appointment.patient_id.isnot(None), Appointment.patient_id)])
        )).label('with_appointments')
    ).first()
    
    # Финансовая статистика
    finance_stats = db.query(
        func.sum(FinancialRecord.total_amount).label('revenue'),
        func.sum(FinancialRecord.paid_amount).label('collected'),
        func.sum(
            case([
                (FinancialRecord.status == 'paid', FinancialRecord.total_amount)
            ], else_=0)
        ).label('paid'),
        func.sum(
            case([
                (FinancialRecord.status == 'pending', 
                 FinancialRecord.total_amount - FinancialRecord.paid_amount)
            ], else_=0)
        ).label('debt')
    ).filter(
        FinancialRecord.invoice_date >= start_date,
        FinancialRecord.invoice_date <= end_date
    ).first()
    
    # Статистика по дням (для графика)
    daily_stats_query = db.query(
        func.date(Appointment.scheduled_start).label('date'),
        func.count(Appointment.id).label('appointments'),
        func.sum(case([(Appointment.status == 'completed', 1)], else_=0)).label('completed')
    ).filter(
        Appointment.scheduled_start >= start_date,
        Appointment.scheduled_start <= end_date
    ).group_by(
        func.date(Appointment.scheduled_start)
    ).order_by('date')
    
    daily_stats = [
        {
            'date': stat.date.isoformat(),
            'appointments': stat.appointments,
            'completed': stat.completed or 0
        }
        for stat in daily_stats_query.all()
    ]
    
    # Топ врачей
    from app.models.doctor import Doctor
    top_doctors = db.query(
        Doctor,
        func.count(Appointment.id).label('appointment_count')
    ).join(
        Appointment, Doctor.id == Appointment.doctor_id
    ).filter(
        Appointment.scheduled_start >= start_date,
        Appointment.scheduled_start <= end_date
    ).group_by(Doctor.id).order_by(
        func.count(Appointment.id).desc()
    ).limit(5).all()
    
    return {
        'period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        },
        'appointments': {
            'total': appointment_stats.total or 0,
            'completed': appointment_stats.completed or 0,
            'cancelled': appointment_stats.cancelled or 0,
            'no_show': appointment_stats.no_show or 0,
            'completion_rate': (
                (appointment_stats.completed or 0) / (appointment_stats.total or 1) * 100
            ) if appointment_stats.total else 0
        },
        'patients': {
            'total': patient_stats.total or 0,
            'active': patient_stats.active or 0,
            'with_appointments': patient_stats.with_appointments or 0,
            'new_patients': get_new_patients_count(db, start_date, end_date)
        },
        'finance': {
            'revenue': float(finance_stats.revenue or 0),
            'collected': float(finance_stats.collected or 0),
            'paid': float(finance_stats.paid or 0),
            'debt': float(finance_stats.debt or 0),
            'collection_rate': (
                (finance_stats.collected or 0) / (finance_stats.revenue or 1) * 100
            ) if finance_stats.revenue else 0
        },
        'daily_stats': daily_stats,
        'top_doctors': [
            {
                'id': doctor.id,
                'name': f"{doctor.last_name} {doctor.first_name}",
                'specialization': doctor.specialization,
                'appointment_count': count
            }
            for doctor, count in top_doctors
        ]
    }

def get_new_patients_count(db: Session, start_date: date, end_date: date) -> int:
    """Получить количество новых пациентов за период"""
    return db.query(Patient).filter(
        Patient.created_at >= start_date,
        Patient.created_at <= end_date
    ).count()