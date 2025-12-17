export interface Invoice {
  id: string
  invoice_number: string
  patient_id: string
  appointment_id?: string
  issue_date: string
  due_date: string
  paid_date?: string
  subtotal: number
  discount_amount: number
  discount_percent: number
  tax_amount: number
  tax_rate: number
  total_amount: number
  paid_amount: number
  balance_due: number
  status: 'draft' | 'pending' | 'partially_paid' | 'paid' | 'overdue' | 'cancelled' | 'refunded'
  payment_method?: 'cash' | 'card' | 'bank_transfer' | 'insurance' | 'online'
  description?: string
  notes?: string
  terms?: string
  created_at: string
  updated_at: string
  
  // Relations
  patient: {
    id: string
    first_name: string
    last_name: string
  }
  items?: InvoiceItem[]
  payments?: Payment[]
}

export interface InvoiceItem {
  id: string
  invoice_id: string
  service_id?: string
  description: string
  quantity: number
  unit_price: number
  unit: string
  discount_percent: number
  discount_amount: number
  tax_rate: number
  tax_amount: number
  subtotal: number
  total: number
  created_at: string
  updated_at: string
}

export interface Payment {
  id: string
  invoice_id: string
  amount: number
  payment_method: 'cash' | 'card' | 'bank_transfer' | 'insurance' | 'online'
  transaction_id?: string
  reference_number?: string
  status: string
  error_message?: string
  notes?: string
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
}