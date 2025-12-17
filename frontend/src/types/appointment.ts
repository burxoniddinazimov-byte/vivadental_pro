export interface Appointment {
  id: string
  patient_id: string
  doctor_id: string
  scheduled_start: string
  scheduled_end: string
  actual_start?: string
  actual_end?: string
  status: 'scheduled' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'no_show'
  appointment_type?: string
  reason?: string
  diagnosis?: string
  treatment_plan?: string
  notes?: string
  created_at: string
  updated_at: string
  
  // Relations
  patient: {
    id: string
    first_name: string
    last_name: string
    phone: string
  }
  doctor: {
    id: string
    first_name: string
    last_name: string
    specialization: string
  }
}