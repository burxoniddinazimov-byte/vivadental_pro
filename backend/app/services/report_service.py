from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, extract
import pandas as pd
from io import BytesIO

from app.models.finance import Invoice, Payment, PaymentStatus
from app.models.patient import Patient
from app.models.doctor import Doctor

class ReportService:
    """Сервис финансовой аналитики и отчетов (исправляю медленные запросы из vivag3.0)"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_financial_overview(
        self,
        start_date: date,
        end_date: date,
        group_by: str = "day"  # day, week, month, doctor, service
    ) -> Dict[str, Any]:
        """
        Общий финансовый обзор за период.
        """
        # Основные метрики
        metrics = self.db.query(
            func.count(Invoice.id).label('invoice_count'),
            func.sum(Invoice.total_amount).label('total_revenue'),
            func.sum(Invoice.paid_amount).label('collected_revenue'),
            func.sum(Invoice.balance_due).label('outstanding_debt'),
            func.sum(case([(Invoice.status == PaymentStatus.PAID, Invoice.total_amount)], else_=0)).label('paid_amount'),
            func.sum(case([(Invoice.status == PaymentStatus.OVERDUE, Invoice.balance_due)], else_=0)).label('overdue_debt'),
            func.avg(Invoice.total_amount).label('avg_invoice_amount')
        ).filter(
            Invoice.issue_date >= start_date,
            Invoice.issue_date <= end_date
        ).first()
        
        # Группировка по времени
        if group_by == "day":
            time_data = self._get_daily_financial_data(start_date, end_date)
        elif group_by == "month":
            time_data = self._get_monthly_financial_data(start_date, end_date)
        
        # Группировка по врачам
        doctor_stats = self.db.query(
            Doctor,
            func.count(Invoice.id).label('invoice_count'),
            func.sum(Invoice.total_amount).label('revenue')
        ).join(
            Invoice, Doctor.id == Invoice.appointment.has(doctor_id=Doctor.id)
        ).filter(
            Invoice.issue_date >= start_date,
            Invoice.issue_date <= end_date
        ).group_by(Doctor.id).order_by(
            func.sum(Invoice.total_amount).desc()
        ).limit(10).all()
        
        # Группировка по услугам
        service_stats = self._get_service_statistics(start_date, end_date)
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "metrics": {
                "invoice_count": metrics.invoice_count or 0,
                "total_revenue": float(metrics.total_revenue or 0),
                "collected_revenue": float(metrics.collected_revenue or 0),
                "outstanding_debt": float(metrics.outstanding_debt or 0),
                "paid_amount": float(metrics.paid_amount or 0),
                "overdue_debt": float(metrics.overdue_debt or 0),
                "avg_invoice_amount": float(metrics.avg_invoice_amount or 0),
                "collection_rate": (
                    (metrics.collected_revenue or 0) / (metrics.total_revenue or 1) * 100
                )
            },
            "time_series": time_data,
            "top_doctors": [
                {
                    "id": doctor.id,
                    "name": f"{doctor.last_name} {doctor.first_name}",
                    "specialization": doctor.specialization,
                    "invoice_count": count,
                    "revenue": float(revenue or 0)
                }
                for doctor, count, revenue in doctor_stats
            ],
            "top_services": service_stats
        }
    
    def _get_daily_financial_data(self, start_date: date, end_date: date) -> List[Dict]:
        """Финансовые данные по дням"""
        data = self.db.query(
            func.date(Invoice.issue_date).label('date'),
            func.count(Invoice.id).label('invoice_count'),
            func.sum(Invoice.total_amount).label('revenue'),
            func.sum(Invoice.paid_amount).label('collected')
        ).filter(
            Invoice.issue_date >= start_date,
            Invoice.issue_date <= end_date
        ).group_by(
            func.date(Invoice.issue_date)
        ).order_by('date').all()
        
        return [
            {
                "date": row.date.isoformat(),
                "invoice_count": row.invoice_count or 0,
                "revenue": float(row.revenue or 0),
                "collected": float(row.collected or 0)
            }
            for row in data
        ]
    
    def _get_service_statistics(self, start_date: date, end_date: date) -> List[Dict]:
        """Статистика по услугам"""
        from app.models.finance import InvoiceItem, Service
        
        stats = self.db.query(
            Service.name,
            Service.category,
            func.count(InvoiceItem.id).label('count'),
            func.sum(InvoiceItem.quantity).label('total_quantity'),
            func.sum(InvoiceItem.total).label('total_revenue'),
            func.avg(InvoiceItem.unit_price).label('avg_price')
        ).join(
            InvoiceItem, Service.id == InvoiceItem.service_id
        ).join(
            Invoice, InvoiceItem.invoice_id == Invoice.id
        ).filter(
            Invoice.issue_date >= start_date,
            Invoice.issue_date <= end_date
        ).group_by(
            Service.id, Service.name, Service.category
        ).order_by(
            func.sum(InvoiceItem.total).desc()
        ).limit(20).all()
        
        return [
            {
                "service": row.name,
                "category": row.category,
                "count": row.count or 0,
                "total_quantity": float(row.total_quantity or 0),
                "total_revenue": float(row.total_revenue or 0),
                "avg_price": float(row.avg_price or 0)
            }
            for row in stats
        ]
    
    def generate_aging_report(self) -> Dict[str, Any]:
        """
        Отчет по давности долгов (Aging Report).
        """
        today = date.today()
        
        # Группируем счета по давности просрочки
        aging_data = self.db.query(
            case([
                (Invoice.due_date >= today, "current"),
                (and_(Invoice.due_date < today, Invoice.due_date >= today - timedelta(days=30)), "1-30"),
                (and_(Invoice.due_date < today - timedelta(days=30), 
                      Invoice.due_date >= today - timedelta(days=60)), "31-60"),
                (and_(Invoice.due_date < today - timedelta(days=60), 
                      Invoice.due_date >= today - timedelta(days=90)), "61-90"),
                (Invoice.due_date < today - timedelta(days=90), "90+")
            ]).label('age_group'),
            func.count(Invoice.id).label('invoice_count'),
            func.sum(Invoice.balance_due).label('total_amount'),
            func.avg(Invoice.days_overdue).label('avg_days_overdue')
        ).filter(
            Invoice.status.in_([PaymentStatus.PENDING.value, PaymentStatus.PARTIALLY_PAID.value, 
                              PaymentStatus.OVERDUE.value]),
            Invoice.balance_due > 0
        ).group_by('age_group').all()
        
        # Детали по каждому пациенту с долгами
        debtor_details = self.db.query(
            Patient,
            func.sum(Invoice.balance_due).label('total_debt'),
            func.count(Invoice.id).label('invoice_count'),
            func.max(Invoice.due_date).label('oldest_due_date')
        ).join(
            Invoice, Patient.id == Invoice.patient_id
        ).filter(
            Invoice.balance_due > 0
        ).group_by(Patient.id).order_by(
            func.sum(Invoice.balance_due).desc()
        ).limit(50).all()
        
        return {
            "report_date": today.isoformat(),
            "aging_summary": [
                {
                    "age_group": row.age_group,
                    "invoice_count": row.invoice_count or 0,
                    "total_amount": float(row.total_amount or 0),
                    "avg_days_overdue": row.avg_days_overdue or 0
                }
                for row in aging_data
            ],
            "top_debtors": [
                {
                    "patient_id": patient.id,
                    "name": f"{patient.last_name} {patient.first_name}",
                    "phone": patient.phone,
                    "total_debt": float(total_debt or 0),
                    "invoice_count": invoice_count or 0,
                    "oldest_due_date": oldest_due_date.isoformat() if oldest_due_date else None
                }
                for patient, total_debt, invoice_count, oldest_due_date in debtor_details
            ]
        }
    
    def export_to_excel(
        self,
        start_date: date,
        end_date: date,
        report_type: str = "financial"
    ) -> BytesIO:
        """
        Экспорт отчета в Excel (исправляю проблемы с памятью из vivag3.0).
        """
        # Используем пагинацию для больших объемов данных
        if report_type == "financial":
            data = self._get_financial_export_data(start_date, end_date)
        elif report_type == "aging":
            data = self._get_aging_export_data()
        elif report_type == "services":
            data = self._get_services_export_data(start_date, end_date)
        
        # Создаем Excel файл с помощью pandas
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, sheet_data in data.items():
                df = pd.DataFrame(sheet_data)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        output.seek(0)
        return output
    
    def _get_financial_export_data(self, start_date: date, end_date: date) -> Dict[str, List]:
        """Данные для финансового отчета"""
        invoices = self.db.query(
            Invoice.invoice_number,
            Invoice.issue_date,
            Patient.last_name,
            Patient.first_name,
            Invoice.subtotal,
            Invoice.discount_amount,
            Invoice.tax_amount,
            Invoice.total_amount,
            Invoice.paid_amount,
            Invoice.balance_due,
            Invoice.status,
            Invoice.payment_method
        ).join(
            Patient, Invoice.patient_id == Patient.id
        ).filter(
            Invoice.issue_date >= start_date,
            Invoice.issue_date <= end_date
        ).order_by(Invoice.issue_date.desc()).limit(10000).all()
        
        return {
            "Invoices": [
                {
                    "Номер счета": inv.invoice_number,
                    "Дата": inv.issue_date.isoformat(),
                    "Пациент": f"{inv.last_name} {inv.first_name}",
                    "Сумма": float(inv.subtotal),
                    "Скидка": float(inv.discount_amount),
                    "Налог": float(inv.tax_amount),
                    "Итого": float(inv.total_amount),
                    "Оплачено": float(inv.paid_amount),
                    "Долг": float(inv.balance_due),
                    "Статус": inv.status.value if hasattr(inv.status, 'value') else inv.status,
                    "Способ оплаты": inv.payment_method.value if inv.payment_method else None
                }
                for inv in invoices
            ]
        }