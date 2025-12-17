from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import hashlib
import hmac
import requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.finance import Invoice, Payment, PaymentMethod, PaymentStatus
from app.core.redis_client import RedisService

class PaymentService:
    """Сервис обработки платежей (решаю проблемы интеграции из vivag3.0)"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_payment_link(
        self,
        invoice_id: str,
        amount: Optional[Decimal] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создание ссылки для онлайн оплаты.
        Поддерживает СБП, банковские карты.
        """
        invoice = self.db.query(Invoice).get(invoice_id)
        if not invoice:
            raise ValueError("Счет не найден")
        
        if invoice.status == PaymentStatus.PAID:
            raise ValueError("Счет уже оплачен")
        
        # Сумма для оплаты
        payment_amount = amount or invoice.balance_due
        
        if payment_amount <= 0:
            raise ValueError("Нет суммы для оплаты")
        
        # Генерируем ID платежа
        payment_id = f"pay_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{invoice.invoice_number[-6:]}"
        
        # Пример для ЮKassa (можно заменить на другую систему)
        payload = {
            "amount": {
                "value": str(payment_amount),
                "currency": "RUB"
            },
            "payment_method_data": {
                "type": "bank_card"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": success_url or f"{settings.FRONTEND_URL}/payment/success",
            },
            "description": description or f"Оплата счета {invoice.invoice_number}",
            "metadata": {
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "patient_id": str(invoice.patient_id)
            },
            "capture": True
        }
        
        # Отправляем запрос к платежному шлюзу
        response = self._make_yookassa_request(payment_id, payload)
        
        # Сохраняем временные данные платежа в Redis
        payment_data = {
            "invoice_id": str(invoice.id),
            "amount": float(payment_amount),
            "payment_id": payment_id,
            "yookassa_id": response.get("id"),
            "status": "pending",
            "confirmation_url": response.get("confirmation", {}).get("confirmation_url")
        }
        
        RedisService.cache_set(f"payment:{payment_id}", payment_data, ttl=3600)
        
        return {
            "payment_id": payment_id,
            "amount": payment_amount,
            "confirmation_url": response.get("confirmation", {}).get("confirmation_url"),
            "invoice_number": invoice.invoice_number
        }
    
    def process_webhook(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Обработка вебхука от платежной системы.
        """
        # Проверяем подпись (безопасность)
        if not self._verify_webhook_signature(payload):
            return False, "Invalid signature"
        
        event = payload.get("event")
        payment_data = payload.get("object", {})
        
        if event == "payment.succeeded":
            return self._handle_successful_payment(payment_data)
        elif event == "payment.canceled":
            return self._handle_cancelled_payment(payment_data)
        elif event == "payment.waiting_for_capture":
            return self._handle_pending_payment(payment_data)
        
        return False, f"Unhandled event: {event}"
    
    def _handle_successful_payment(self, payment_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Обработка успешного платежа"""
        metadata = payment_data.get("metadata", {})
        invoice_id = metadata.get("invoice_id")
        
        if not invoice_id:
            return False, "No invoice ID in metadata"
        
        # Начинаем транзакцию (исправляю потерю данных из vivag3.0)
        try:
            invoice = self.db.query(Invoice).get(invoice_id)
            if not invoice:
                return False, "Invoice not found"
            
            amount = Decimal(payment_data.get("amount", {}).get("value", 0))
            
            # Создаем запись платежа
            payment = Payment(
                invoice_id=invoice.id,
                amount=amount,
                payment_method=PaymentMethod.ONLINE,
                transaction_id=payment_data.get("id"),
                reference_number=payment_data.get("payment_method", {}).get("id"),
                metadata=payment_data,
                status="completed"
            )
            
            self.db.add(payment)
            
            # Обновляем счет
            invoice.add_payment(amount, PaymentMethod.ONLINE, "Оплата онлайн")
            
            self.db.commit()
            
            # Отправляем уведомление
            self._send_payment_notification(invoice, amount)
            
            return True, "Payment processed successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Error processing payment: {str(e)}"
    
    def _make_yookassa_request(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Запрос к API ЮKassa"""
        # В продакшене используйте реальные ключи
        headers = {
            "Idempotence-Key": payment_id,
            "Content-Type": "application/json"
        }
        
        # Базовые auth (shopId + secret key)
        auth = (settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY)
        
        response = requests.post(
            "https://api.yookassa.ru/v3/payments",
            json=payload,
            headers=headers,
            auth=auth,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
    
    def _verify_webhook_signature(self, payload: Dict[str, Any]) -> bool:
        """Проверка подписи вебхука"""
        signature = payload.get("signature", "")
        body = payload.get("body", "")
        
        # Генерируем подпись для проверки
        expected_signature = hmac.new(
            settings.YOOKASSA_WEBHOOK_SECRET.encode(),
            body.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def _send_payment_notification(self, invoice: Invoice, amount: Decimal):
        """Отправка уведомления об оплате"""
        from app.tasks.notification_tasks import send_payment_notification
        send_payment_notification.delay(
            invoice_id=str(invoice.id),
            amount=float(amount)
        )
    
    def generate_receipt(self, invoice_id: str) -> Dict[str, Any]:
        """
        Генерация чека по 54-ФЗ (исправляю ошибки формата из vivag3.0).
        """
        invoice = self.db.query(Invoice).get(invoice_id)
        if not invoice:
            raise ValueError("Счет не найден")
        
        # Данные для чека
        items = []
        for item in invoice.items:
            items.append({
                "name": item.description,
                "price": float(item.unit_price),
                "quantity": float(item.quantity),
                "amount": float(item.total),
                "vat_code": self._get_vat_code(item.tax_rate),
                "payment_method": "full_payment",
                "payment_object": "service"
            })
        
        receipt = {
            "timestamp": datetime.now().isoformat(),
            "external_id": f"receipt_{invoice.invoice_number}",
            "company": {
                "email": settings.COMPANY_EMAIL,
                "sno": settings.TAX_SYSTEM,  # Система налогообложения
                "inn": settings.INN,
                "payment_address": settings.PAYMENT_ADDRESS
            },
            "payments": [
                {
                    "type": "card",  # или cash
                    "sum": float(invoice.paid_amount)
                }
            ],
            "total": float(invoice.total_amount),
            "items": items,
            "client": {
                "email": invoice.patient.email,
                "phone": invoice.patient.phone
            }
        }
        
        # Подписываем чек (для реальной системы)
        receipt["signature"] = self._sign_receipt(receipt)
        
        return receipt
    
    def _get_vat_code(self, tax_rate: Decimal) -> int:
        """Получение кода НДС для чека"""
        if tax_rate == Decimal('0'):
            return 6  # Без НДС
        elif tax_rate == Decimal('10'):
            return 2  # НДС 10%
        elif tax_rate == Decimal('20'):
            return 1  # НДС 20%
        else:
            return 6
    
    def _sign_receipt(self, receipt: Dict[str, Any]) -> str:
        """Генерация подписи чека (упрощенная)"""
        import json
        data = json.dumps(receipt, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(data.encode() + settings.RECEIPT_SECRET.encode()).hexdigest()