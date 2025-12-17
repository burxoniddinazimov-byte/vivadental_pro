from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID

class PatientBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    phone: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')  # E.164 формат
    email: Optional[EmailStr] = None
    birth_date: date
    gender: Optional[str] = None

class PatientCreate(PatientBase):
    password: str = Field(..., min_length=8)
    
    @validator('birth_date')
    def validate_birth_date(cls, v):
        if v > date.today():
            raise ValueError('Дата рождения не может быть в будущем')
        if v < date(1900, 1, 1):
            raise ValueError('Дата рождения слишком ранняя')
        return v

class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address_json: Optional[dict] = None
    allergies: Optional[List[str]] = None
    is_active: Optional[bool] = None

class Patient(PatientBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PatientWithStats(Patient):
    total_appointments: int = 0
    total_spent: float = 0.0
    last_visit: Optional[datetime] = None
    upcoming_appointments: int = 0