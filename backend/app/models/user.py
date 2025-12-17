from sqlalchemy import Column, String, Boolean, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from datetime import datetime

from .base import Base

class UserRole(enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    DOCTOR = "doctor"
    RECEPTION = "reception"
    FINANCE = "finance"
    PATIENT = "patient"

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=False)
    avatar_url = Column(String(500))
    
    role = Column(Enum(UserRole), default=UserRole.PATIENT, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Дополнительные данные
    specialization = Column(String(200))  # Для врачей
    department = Column(String(100))
    notes = Column(String(500))
    
    # Связи
    doctor_profile = relationship("Doctor", back_populates="user", uselist=False)
    
    # Таймстампы
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime)
    
    # Индексы
    __table_args__ = (
        Index('ix_users_email', 'email'),
        Index('ix_users_role', 'role'),
        Index('ix_users_created', 'created_at'),
    )
    
    # Методы
    def has_permission(self, permission: str) -> bool:
        """Проверка разрешений пользователя"""
        permissions = {
            UserRole.SUPER_ADMIN: ['*'],
            UserRole.ADMIN: [
                'patients.*',
                'appointments.*',
                'finance.*',
                'reports.*',
                'settings.*'
            ],
            UserRole.DOCTOR: [
                'patients.read',
                'appointments.read',
                'appointments.create',
                'appointments.update',
                'finance.read'
            ],
            UserRole.RECEPTION: [
                'patients.*',
                'appointments.*',
                'finance.create',
                'finance.read'
            ],
            UserRole.FINANCE: [
                'patients.read',
                'appointments.read',
                'finance.*'
            ],
            UserRole.PATIENT: [
                'patients.self',
                'appointments.self',
                'finance.self'
            ]
        }
        
        user_perms = permissions.get(self.role, [])
        
        if '*' in user_perms:
            return True
        
        for perm in user_perms:
            if perm.endswith('*'):
                prefix = perm[:-1]
                if permission.startswith(prefix):
                    return True
            elif perm == permission:
                return True
        
        return False