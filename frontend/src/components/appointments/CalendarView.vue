<template>
  <div class="calendar-container">
    <!-- Календарь -->
    <FullCalendar :options="calendarOptions" />
    
    <!-- Панель фильтров -->
    <div class="calendar-sidebar">
      <div class="sidebar-section">
        <h3>Фильтры</h3>
        <div class="filter-group">
          <label>Врачи:</label>
          <MultiSelect 
            v-model="selectedDoctors" 
            :options="doctors" 
            optionLabel="name"
            placeholder="Все врачи"
          />
        </div>
        <div class="filter-group">
          <label>Статус:</label>
          <MultiSelect 
            v-model="selectedStatuses" 
            :options="statusOptions" 
            placeholder="Все статусы"
          />
        </div>
      </div>
      
      <!-- Быстрая запись -->
      <div class="sidebar-section">
        <h3>Быстрая запись</h3>
        <QuickAppointmentForm @appointment-created="refreshCalendar" />
      </div>
      
      <!-- Статистика дня -->
      <div class="sidebar-section">
        <h3>Сегодня</h3>
        <div class="day-stats">
          <div class="stat-item">
            <span class="stat-label">Всего записей</span>
            <span class="stat-value">{{ todayStats.total }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Завершено</span>
            <span class="stat-value success">{{ todayStats.completed }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Отменено</span>
            <span class="stat-value danger">{{ todayStats.cancelled }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Диалог редактирования записи -->
    <AppointmentDialog 
      v-model:visible="showAppointmentDialog"
      :appointment="selectedAppointment"
      @save="handleAppointmentSave"
      @delete="handleAppointmentDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import ruLocale from '@fullcalendar/core/locales/ru'
import MultiSelect from 'primevue/multiselect'
import { appointmentService } from '@/services/appointment.service'
import QuickAppointmentForm from './QuickAppointmentForm.vue'
import AppointmentDialog from './AppointmentDialog.vue'
import type { Appointment } from '@/types/appointment'

// Календарь
const calendarOptions = ref({
  plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
  initialView: 'timeGridWeek',
  locale: ruLocale,
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'dayGridMonth,timeGridWeek,timeGridDay'
  },
  events: [],
  editable: true,
  selectable: true,
  selectMirror: true,
  dayMaxEvents: true,
  weekends: true,
  businessHours: {
    daysOfWeek: [1, 2, 3, 4, 5],
    startTime: '09:00',
    endTime: '18:00'
  },
  select: handleDateSelect,
  eventClick: handleEventClick,
  eventDrop: handleEventDrop,
  eventResize: handleEventResize,
  height: 'calc(100vh - 140px)'
})

// Состояние
const selectedDoctors = ref([])
const selectedStatuses = ref([])
const showAppointmentDialog = ref(false)
const selectedAppointment = ref<Appointment | null>(null)
const doctors = ref([])
const todayStats = ref({
  total: 0,
  completed: 0,
  cancelled: 0
})

const statusOptions = [
  'scheduled',
  'confirmed',
  'in_progress',
  'completed',
  'cancelled',
  'no_show'
]

// Методы
async function loadCalendarData() {
  try {
    const appointments = await appointmentService.getAppointments({
      start_date: getCalendarStartDate(),
      end_date: getCalendarEndDate(),
      doctor_id: selectedDoctors.value.map(d => d.id).join(','),
      status: selectedStatuses.value.join(',')
    })
    
    calendarOptions.value.events = appointments.map(app => ({
      id: app.id,
      title: `${app.patient.last_name} ${app.patient.first_name[0]}.`,
      start: app.scheduled_start,
      end: app.scheduled_end,
      color: getStatusColor(app.status),
      extendedProps: app
    }))
    
    loadTodayStats()
  } catch (error) {
    console.error('Error loading calendar:', error)
  }
}

async function loadTodayStats() {
  const stats = await appointmentService.getTodayStats()
  todayStats.value = stats
}

function getCalendarStartDate() {
  // Логика получения даты начала календаря
  return new Date().toISOString()
}

function getCalendarEndDate() {
  // Логика получения даты окончания календаря
  const date = new Date()
  date.setDate(date.getDate() + 30)
  return date.toISOString()
}

function getStatusColor(status: string) {
  const colors = {
    scheduled: '#3b82f6',
    confirmed: '#10b981',
    in_progress: '#f59e0b',
    completed: '#6366f1',
    cancelled: '#ef4444',
    no_show: '#6b7280'
  }
  return colors[status] || '#6b7280'
}

function handleDateSelect(selectInfo: any) {
  selectedAppointment.value = {
    scheduled_start: selectInfo.startStr,
    scheduled_end: selectInfo.endStr
  }
  showAppointmentDialog.value = true
}

function handleEventClick(clickInfo: any) {
  selectedAppointment.value = clickInfo.event.extendedProps
  showAppointmentDialog.value = true
}

async function handleEventDrop(dropInfo: any) {
  try {
    const appointment = dropInfo.event.extendedProps
    await appointmentService.updateAppointment(appointment.id, {
      scheduled_start: dropInfo.event.startStr,
      scheduled_end: dropInfo.event.endStr
    })
  } catch (error) {
    dropInfo.revert()
    console.error('Error moving appointment:', error)
  }
}

async function handleAppointmentSave() {
  await loadCalendarData()
  showAppointmentDialog.value = false
}

async function handleAppointmentDelete() {
  await loadCalendarData()
  showAppointmentDialog.value = false
}

function refreshCalendar() {
  loadCalendarData()
}

// Хуки
onMounted(() => {
  loadCalendarData()
})
</script>

<style scoped>
.calendar-container {
  display: flex;
  height: calc(100vh - 60px);
}

.calendar-sidebar {
  width: 320px;
  background: white;
  border-left: 1px solid #e5e7eb;
  padding: 24px;
  overflow-y: auto;
}

.sidebar-section {
  margin-bottom: 32px;
}

.sidebar-section h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.filter-group {
  margin-bottom: 16px;
}

.filter-group label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
  margin-bottom: 8px;
}

.day-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f9fafb;
  border-radius: 6px;
}

.stat-label {
  font-size: 14px;
  color: #6b7280;
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.stat-value.success {
  color: #10b981;
}

.stat-value.danger {
  color: #ef4444;
}
</style>