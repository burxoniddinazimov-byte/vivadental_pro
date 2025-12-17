import { api } from './api'
import type { Patient, PatientCreate, PatientUpdate } from '@/types/patient'

class PatientService {
  async getPatients(params?: {
    skip?: number
    limit?: number
    search?: string
    is_active?: boolean
  }) {
    return api.get<{
      items: Patient[]
      total: number
      page: number
      size: number
      pages: number
    }>('/api/v1/patients', { params })
  }

  async getPatient(id: string) {
    return api.get<Patient>(`/api/v1/patients/${id}`)
  }

  async createPatient(data: PatientCreate) {
    return api.post<Patient>('/api/v1/patients', data)
  }

  async updatePatient(id: string, data: PatientUpdate) {
    return api.put<Patient>(`/api/v1/patients/${id}`, data)
  }

  async deletePatient(id: string) {
    return api.delete(`/api/v1/patients/${id}`)
  }

  async getPatientStats(id: string) {
    return api.get(`/api/v1/patients/${id}/stats`)
  }
}

export const patientService = new PatientService()