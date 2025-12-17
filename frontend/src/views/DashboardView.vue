<template>
  <div class="dashboard">
    <!-- Заголовок -->
    <div class="dashboard-header">
      <h1>Панель управления</h1>
      <div class="date-range">
        <Calendar 
          v-model="dateRange" 
          selectionMode="range" 
          :manualInput="false"
          dateFormat="dd.mm.yy"
          placeholder="Выберите период"
        />
      </div>
    </div>
    
    <!-- KPI карточки -->
    <div class="kpi-grid">
      <KpiCard 
        title="Пациенты"
        :value="stats.patients.total"
        :change="stats.patients.change"
        icon="pi pi-users"
        color="blue"
      />
      <KpiCard 
        title="Записи сегодня"
        :value="stats.appointments.today"
        :change="stats.appointments.change"
        icon="pi pi-calendar"
        color="green"
      />
      <KpiCard 
        title="Выручка"
        :value="`${formatCurrency(stats.finance.revenue)}`"
        :change="stats.finance.change"
        icon="pi pi-money-bill"
        color="purple"
      />
      <KpiCard 
        title="Заполненность"
        :value="`${stats.occupancy.rate}%`"
        :change="stats.occupancy.change"
        icon="pi pi-chart-bar"
        color="orange"
      />
    </div>
    
    <!-- Графики и таблицы -->
    <div class="dashboard-content">
      <!-- График посещений -->
      <div class="chart-container">
        <div class="chart-header">
          <h3>Посещения по дням</h3>
          <Select 
            v-model="chartPeriod" 
            :options="periodOptions" 
            optionLabel="label"
            optionValue="value"
          />
        </div>
        <AppointmentsChart :period="chartPeriod" />
      </div>
      
      <!-- Финансовый график -->
      <div class="chart-container">
        <div class="chart-header">
          <h3>Финансы</h3>
        </div>
        <RevenueChart :period="chartPeriod" />
      </div>
      
      <!-- Предстоящие записи -->
      <div class="table-container">
        <div class="table-header">
          <h3>Предстоящие записи</h3>
          <Button label="Все записи" icon="pi pi-arrow-right" text />
        </div>
        <UpcomingAppointments />
      </div>
      
      <!-- Топ услуг -->
      <div class="table-container">
        <div class="table-header">
          <h3>Популярные услуги</h3>
        </div>
        <TopServices />
      </div>
    </div>
    
    <!-- Уведомления -->
    <div class="notifications-sidebar">
      <h3>Уведомления</h3>
      <NotificationsList />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import KpiCard from '@/components/dashboard/KpiCard.vue'
import AppointmentsChart from '@/components/dashboard/AppointmentsChart.vue'
import RevenueChart from '@/components/dashboard/RevenueChart.vue'
import UpcomingAppointments from '@/components/dashboard/UpcomingAppointments.vue'
import TopServices from '@/components/dashboard/TopServices.vue'
import NotificationsList from '@/components/dashboard/NotificationsList.vue'
import Calendar from 'primevue/calendar'
import Select from 'primevue/select'
import Button from 'primevue/button'

const dashboardStore = useDashboardStore()

// Состояние
const dateRange = ref([new Date(), new Date()])
const chartPeriod = ref('week')
const stats = ref({
  patients: { total: 0, change: 0 },
  appointments: { today: 0, change: 0 },
  finance: { revenue: 0, change: 0 },
  occupancy: { rate: 0, change: 0 }
})

const periodOptions = [
  { label: 'Неделя', value: 'week' },
  { label: 'Месяц', value: 'month' },
  { label: 'Квартал', value: 'quarter' },
  { label: 'Год', value: 'year' }
]

// Методы
const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0
  }).format(value)
}

const loadDashboardData = async () => {
  await dashboardStore.fetchStats()
  stats.value = dashboardStore.stats
}

// Хуки
onMounted(() => {
  loadDashboardData()
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 24px;
  background: #f9fafb;
  min-height: calc(100vh - 60px);
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dashboard-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #111827;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.dashboard-content {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.chart-container,
.table-container {
  background: white;
  border-radius: 8px;
  padding: 24px;
  border: 1px solid #e5e7eb;
}

.chart-header,
.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.chart-header h3,
.table-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.notifications-sidebar {
  position: fixed;
  right: 0;
  top: 60px;
  width: 320px;
  height: calc(100vh - 60px);
  background: white;
  border-left: 1px solid #e5e7eb;
  padding: 24px;
  overflow-y: auto;
}

.notifications-sidebar h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}
</style>