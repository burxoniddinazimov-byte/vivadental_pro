import { defineStore } from 'pinia'
import { ref } from 'vue'
import { patientService } from '@/services/patient.service'
import type { Patient, PatientCreate, PatientUpdate } from '@/types/patient'

export const usePatientStore = defineStore('patient', () => {
  const patients = ref<Patient[]>([])
  const currentPatient = ref<Patient | null>(null)
  const isLoading = ref(false)
  const total = ref(0)

  async function fetchPatients(params?: {
    page?: number
    limit?: number
    search?: string
    is_active?: boolean
  }) {
    try {
      isLoading.value = true
      const response = await patientService.getPatients({
        skip: ((params?.page || 1) - 1) * (params?.limit || 20),
        limit: params?.limit || 20,
        search: params?.search,
        is_active: params?.is_active
      })
      
      patients.value = response.items
      total.value = response.total
    } catch (error) {
      throw error
    } finally {
      isLoading.value = false
    }
  }

  async function fetchPatient(id: string) {
    try {
      isLoading.value = true
      const patient = await patientService.getPatient(id)
      currentPatient.value = patient
      return patient
    } catch (error) {
      throw error
    } finally {
      isLoading.value = false
    }
  }

  async function createPatient(data: PatientCreate) {
    try {
      const patient = await patientService.createPatient(data)
      patients.value.unshift(patient)
      return patient
    } catch (error) {
      throw error
    }
  }

  async function updatePatient(id: string, data: PatientUpdate) {
    try {
      const patient = await patientService.updatePatient(id, data)
      
      // Обновляем в списке
      const index = patients.value.findIndex(p => p.id === id)
      if (index !== -1) {
        patients.value[index] = patient
      }
      
      // Обновляем текущего пациента
      if (currentPatient.value?.id === id) {
        currentPatient.value = patient
      }
      
      return patient
    } catch (error) {
      throw error
    }
  }

  async function deletePatient(id: string) {
    try {
      await patientService.deletePatient(id)
      patients.value = patients.value.filter(p => p.id !== id)
    } catch (error) {
      throw error
    }
  }

  return {
    patients,
    currentPatient,
    isLoading,
    total,
    fetchPatients,
    fetchPatient,
    createPatient,
    updatePatient,
    deletePatient
  }
})