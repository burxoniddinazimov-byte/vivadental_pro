from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from fastapi import HTTPException, status
from datetime import date, datetime, timedelta

from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate
from app.core.security import get_password_hash

class CRUDPatient:
    def get(self, db: Session, patient_id: UUID) -> Optional[Patient]:
        """Получение пациента по ID (безопасно, исправляю SQL-инъекции из VIVAD)"""
        return db.query(Patient).filter(Patient.id == patient_id).first()
    
    def get_by_phone(self, db: Session, phone: str) -> Optional[Patient]:
        """Получение пациента по телефону"""
        return db.query(Patient).filter(Patient.phone == phone).first()
    
    def get_multi(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        search: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Patient]:
        """Получение списка пациентов с фильтрацией и поиском"""
        query = db.query(Patient)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Patient.first_name.ilike(search_term),
                    Patient.last_name.ilike(search_term),
                    Patient.phone.ilike(search_term),
                    Patient.email.ilike(search_term)
                )
            )
        
        if is_active is not None:
            query = query.filter(Patient.is_active == is_active)
        
        return query.offset(skip).limit(limit).all()
    
    def create(self, db: Session, obj_in: PatientCreate) -> Patient:
        """Создание пациента (с транзакцией)"""
        # Проверяем дубликаты
        if self.get_by_phone(db, obj_in.phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пациент с таким телефоном уже существует"
            )
        
        db_obj = Patient(
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            middle_name=obj_in.middle_name,
            phone=obj_in.phone,
            email=obj_in.email,
            birth_date=obj_in.birth_date,
            gender=obj_in.gender
        )
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(
        self, 
        db: Session, 
        db_obj: Patient, 
        obj_in: PatientUpdate
    ) -> Patient:
        """Обновление пациента"""
        update_data = obj_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def deactivate(self, db: Session, patient_id: UUID) -> Patient:
        """Деактивация пациента (мягкое удаление)"""
        patient = self.get(db, patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пациент не найден"
            )
        
        patient.is_active = False
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return patient
    
    def get_stats(self, db: Session, patient_id: UUID) -> Dict[str, Any]:
        """Получение статистики по пациенту"""
        from app.models.appointment import Appointment
        from app.models.finance import FinancialRecord
        
        patient = self.get(db, patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пациент не найден"
            )
        
        # Статистика посещений
        total_appointments = db.query(func.count(Appointment.id)).filter(
            Appointment.patient_id == patient_id
        ).scalar() or 0
        
        # Последний визит
        last_visit = db.query(Appointment).filter(
            Appointment.patient_id == patient_id,
            Appointment.status == 'completed'
        ).order_by(Appointment.scheduled_start.desc()).first()
        
        # Предстоящие записи
        upcoming_appointments = db.query(func.count(Appointment.id)).filter(
            Appointment.patient_id == patient_id,
            Appointment.scheduled_start > datetime.now(),
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).scalar() or 0
        
        # Финансовая статистика
        financial_stats = db.query(
            func.sum(FinancialRecord.total_amount).label('total_spent'),
            func.sum(FinancialRecord.paid_amount).label('total_paid'),
            func.sum(FinancialRecord.balance).label('total_debt')
        ).filter(
            FinancialRecord.patient_id == patient_id
        ).first()
        
        return {
            "patient": patient,
            "total_appointments": total_appointments,
            "last_visit": last_visit.scheduled_start if last_visit else None,
            "upcoming_appointments": upcoming_appointments,
            "total_spent": float(financial_stats.total_spent or 0),
            "total_paid": float(financial_stats.total_paid or 0),
            "total_debt": float(financial_stats.total_debt or 0),
        }

patient = CRUDPatient()