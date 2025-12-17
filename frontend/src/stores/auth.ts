import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/services/api'

interface User {
  id: string
  email: string
  name: string
  role: string
}

interface LoginData {
  email: string
  password: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token'))
  const user = ref<User | null>(null)
  const isLoading = ref(false)

  const isAuthenticated = computed(() => !!token.value)

  async function login(credentials: LoginData) {
    try {
      isLoading.value = true
      const response = await api.post<{ access_token: string; user: User }>('/api/v1/auth/login', credentials)
      
      token.value = response.access_token
      user.value = response.user
      
      localStorage.setItem('token', response.access_token)
      localStorage.setItem('user', JSON.stringify(response.user))
      
      return response
    } catch (error) {
      throw error
    } finally {
      isLoading.value = false
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  function loadFromStorage() {
    const storedToken = localStorage.getItem('token')
    const storedUser = localStorage.getItem('user')
    
    if (storedToken) {
      token.value = storedToken
    }
    
    if (storedUser) {
      user.value = JSON.parse(storedUser)
    }
  }

  return {
    token,
    user,
    isLoading,
    isAuthenticated,
    login,
    logout,
    loadFromStorage
  }
})