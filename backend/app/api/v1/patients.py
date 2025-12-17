from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from fastapi_pagination import Page, add_pagination, paginate

from app.core.database import get_db_session
from app.crud.patient import patient as patient_crud
from app.schemas.patient import Patient, PatientCreate, PatientUpdate, PatientWithStats
from app.api.deps import get_current_active_user

router = APIRouter(prefix="/patients", tags=["patients"])

@router.get("/", response_model=Page[Patient])
def read_patients(
    db: Session = Depends(get_db_session),
    skip: int = 0,
    limit: int = 100,
    search: str = Query(None, description="Поиск по имени, фамилии, телефону или email"),
    is_active: bool = Query(True, description="Только активные пациенты"),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Получить список пациентов с пагинацией и поиском.
    """
    patients = patient_crud.get_multi(
        db, skip=skip, limit=limit, search=search, is_active=is_active
    )
    return paginate(patients)

@router.get("/{patient_id}", response_model=PatientWithStats)
def read_patient(
    patient_id: UUID,
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Получить пациента по ID со статистикой.
    """
    stats = patient_crud.get_stats(db, patient_id=patient_id)
    if not stats["patient"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пациент не найден"
        )
    return stats

@router.post("/", response_model=Patient, status_code=status.HTTP_201_CREATED)
def create_patient(
    patient_in: PatientCreate,
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Создать нового пациента.
    """
    patient = patient_crud.get_by_phone(db, phone=patient_in.phone)
    if patient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пациент с таким телефоном уже существует"
        )
    return patient_crud.create(db=db, obj_in=patient_in)

@router.put("/{patient_id}", response_model=Patient)
def update_patient(
    patient_id: UUID,
    patient_in: PatientUpdate,
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Обновить данные пациента.
    """
    patient = patient_crud.get(db, patient_id=patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пациент не найден"
        )
    return patient_crud.update(db=db, db_obj=patient, obj_in=patient_in)

@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: UUID,
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Деактивировать пациента (мягкое удаление).
    """
    patient = patient_crud.get(db, patient_id=patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пациент не найден"
        )
    patient_crud.deactivate(db, patient_id=patient_id)
    return None

# Подключаем пагинацию
add_pagination(router)