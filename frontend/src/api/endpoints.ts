import apiClient from './client'

// Auth endpoints
export const authApi = {
  login: (credentials: { email: string; password: string }) =>
    apiClient.post('/auth/login', credentials),
  refresh: (refreshToken: string) =>
    apiClient.post('/auth/refresh', { refresh_token: refreshToken }),
  logout: () => apiClient.post('/auth/logout'),
}

// Patient endpoints
export const patientApi = {
  getPatients: (params?: any) =>
    apiClient.get('/patients', { params }),
  getPatient: (id: string) =>
    apiClient.get(`/patients/${id}`),
  createPatient: (data: any) =>
    apiClient.post('/patients', data),
  updatePatient: (id: string, data: any) =>
    apiClient.put(`/patients/${id}`, data),
}

// Appointment endpoints
export const appointmentApi = {
  getAppointments: (params?: any) =>
    apiClient.get('/appointments', { params }),
  getAvailableSlots: (doctorId: string, params: any) =>
    apiClient.get(`/appointments/available-slots/${doctorId}`, { params }),
  createAppointment: (data: any) =>
    apiClient.post('/appointments', data),
  cancelAppointment: (id: string, reason?: string) =>
    apiClient.post(`/appointments/${id}/cancel`, { reason }),
}

// Finance endpoints
export const financeApi = {
  getInvoices: (params?: any) =>
    apiClient.get('/finance/invoices', { params }),
  createInvoice: (data: any) =>
    apiClient.post('/finance/invoices', data),
  createPayment: (data: any) =>
    apiClient.post('/finance/payments', data),
  getFinancialReport: (params: any) =>
    apiClient.post('/finance/reports/financial', params),
}