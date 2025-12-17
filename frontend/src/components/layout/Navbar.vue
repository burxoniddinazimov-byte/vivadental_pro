<template>
  <nav class="navbar">
    <div class="navbar-brand">
      <router-link to="/" class="logo">
        <span class="logo-icon">🦷</span>
        <span class="logo-text">VivaDental</span>
      </router-link>
    </div>
    
    <div class="navbar-menu">
      <router-link 
        v-for="item in menuItems" 
        :key="item.to"
        :to="item.to"
        class="navbar-item"
        active-class="active"
      >
        <i :class="item.icon"></i>
        <span>{{ item.text }}</span>
      </router-link>
    </div>
    
    <div class="navbar-user">
      <Dropdown v-model="selectedUserOption" :options="userOptions" optionLabel="label">
        <template #value="slotProps">
          <div class="user-info">
            <Avatar :label="userInitials" size="large" shape="circle" />
            <div class="user-details">
              <span class="user-name">{{ userName }}</span>
              <span class="user-role">{{ userRole }}</span>
            </div>
          </div>
        </template>
        <template #option="slotProps">
          <div class="dropdown-option" @click="slotProps.option.action">
            <i :class="slotProps.option.icon"></i>
            <span>{{ slotProps.option.label }}</span>
          </div>
        </template>
      </Dropdown>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Avatar from 'primevue/avatar'
import Dropdown from 'primevue/dropdown'

const router = useRouter()
const authStore = useAuthStore()

const menuItems = [
  { to: '/dashboard', icon: 'pi pi-home', text: 'Дашборд' },
  { to: '/patients', icon: 'pi pi-users', text: 'Пациенты' },
  { to: '/appointments', icon: 'pi pi-calendar', text: 'Записи' },
  { to: '/finance', icon: 'pi pi-money-bill', text: 'Финансы' },
  { to: '/reports', icon: 'pi pi-chart-bar', text: 'Отчеты' }
]

const selectedUserOption = ref(null)

const userName = computed(() => authStore.user?.name || 'Администратор')
const userRole = computed(() => {
  switch (authStore.user?.role) {
    case 'admin': return 'Администратор'
    case 'doctor': return 'Врач'
    case 'reception': return 'Ресепшен'
    default: return 'Пользователь'
  }
})

const userInitials = computed(() => {
  const name = userName.value
  return name.split(' ').map(n => n[0]).join('').toUpperCase()
})

const userOptions = [
  { label: 'Профиль', icon: 'pi pi-user', action: () => router.push('/profile') },
  { label: 'Настройки', icon: 'pi pi-cog', action: () => router.push('/settings') },
  { separator: true },
  { label: 'Выйти', icon: 'pi pi-sign-out', action: logout }
]

function logout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  padding: 0 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.navbar-brand .logo {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
  color: #3b82f6;
  font-weight: bold;
  font-size: 20px;
}

.logo-icon {
  font-size: 24px;
}

.navbar-menu {
  display: flex;
  gap: 24px;
}

.navbar-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  text-decoration: none;
  color: #6b7280;
  border-radius: 6px;
  transition: all 0.2s;
}

.navbar-item:hover {
  background: #f3f4f6;
  color: #374151;
}

.navbar-item.active {
  background: #3b82f6;
  color: white;
}

.navbar-user .user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.user-details {
  display: flex;
  flex-direction: column;
}

.user-name {
  font-weight: 600;
  color: #111827;
}

.user-role {
  font-size: 12px;
  color: #6b7280;
}

.dropdown-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  cursor: pointer;
}

.dropdown-option:hover {
  background: #f3f4f6;
}
</style>