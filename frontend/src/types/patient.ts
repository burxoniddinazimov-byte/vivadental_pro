export interface Patient {
  id: string
  first_name: string
  last_name: string
  middle_name?: string
  phone: string
  email?: string
  birth_date: string
  gender?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface PatientCreate {
  first_name: string
  last_name: string
  middle_name?: string
  phone: string
  email?: string
  birth_date: string
  gender?: string
}

export interface PatientUpdate {
  first_name?: string
  last_name?: string
  phone?: string
  email?: string
  address_json?: Record<string, any>
  allergies?: string[]
  is_active?: boolean
}