<template>
  <v-container fluid class="pa-0">
    <v-row no-gutters>
      <!-- Sidebar -->
      <v-col cols="12" md="3" class="sidebar">
        <v-card height="100%" flat>
          <v-card-title class="d-flex align-center">
            <v-icon start icon="mdi-filter" />
            Фильтры
          </v-card-title>
          
          <v-card-text>
            <v-select
              v-model="filters.doctor_id"
              :items="doctors"
              item-title="full_name"
              item-value="id"
              label="Врач"
              variant="outlined"
              clearable
              @update:model-value="loadAppointments"
            />
            
            <v-select
              v-model="filters.status"
              :items="statusOptions"
              label="Статус"
              variant="outlined"
              clearable
              multiple
              @update:model-value="loadAppointments"
            />
            
            <v-menu v-model="dateMenu" :close-on-content-click="false">
              <template v-slot:activator="{ props }">
                <v-text-field
                  v-model="dateRangeText"
                  label="Период"
                  prepend-inner-icon="mdi-calendar"
                  readonly
                  variant="outlined"
                  v-bind="props"
                />
              </template>
              
              <v-date-picker
                v-model="filters.dateRange"
                range
                @update:model-value="handleDateChange"
              />
            </v-menu>
          </v-card-text>
          
          <!-- Quick stats -->
          <v-card-text>
            <v-list density="compact">
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon color="primary">mdi-calendar-check</v-icon>
                </template>
                <v-list-item-title>Запланировано</v-list-item-title>
                <v-list-item-subtitle>{{ stats.scheduled }}</v-list-item-subtitle>
              </v-list-item>
              
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon color="green">mdi-check-circle</v-icon>
                </template>
                <v-list-item-title>Завершено</v-list-item-title>
                <v-list-item-subtitle>{{ stats.completed }}</v-list-item-subtitle>
              </v-list-item>
              
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon color="red">mdi-close-circle</v-icon>
                </template>
                <v-list-item-title>Отменено</v-list-item-title>
                <v-list-item-subtitle>{{ stats.cancelled }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
      
      <!-- Main content -->
      <v-col cols="12" md="9">
        <v-card flat>
          <v-card-title class="d-flex align-center">
            <v-icon start icon="mdi-calendar" />
            Записи на прием
            <v-spacer />
            <v-btn
              color="primary"
              prepend-icon="mdi-plus"
              @click="showCreateDialog = true"
            >
              Новая запись
            </v-btn>
          </v-card-title>
          
          <v-card-text>
            <!-- Calendar view -->
            <v-calendar
              ref="calendar"
              v-model="selectedDate"
              :events="calendarEvents"
              :event-color="getEventColor"
              :event-height="24"
              @click:event="handleEventClick"
              @click:day="handleDayClick"
            />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    
    <!-- Create Appointment Dialog -->
    <v-dialog v-model="showCreateDialog" max-width="800">
      <appointment-form
        v-model="showCreateDialog"
        :selected-doctor="filters.doctor_id"
        :selected-date="selectedDate"
        @saved="handleAppointmentSaved"
      />
    </v-dialog>
    
    <!-- Event Details Dialog -->
    <v-dialog v-model="showEventDialog" max-width="500">
      <appointment-details
        v-if="selectedEvent"
        :appointment="selectedEvent"
        @close="showEventDialog = false"
        @updated="handleAppointmentUpdated"
        @cancelled="handleAppointmentCancelled"
      />
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useToast } from 'vue-toastification'
import { appointmentApi } from '@/api/endpoints'
import AppointmentForm from '@/components/appointments/AppointmentForm.vue'
import AppointmentDetails from '@/components/appointments/AppointmentDetails.vue'
import type { Appointment } from '@/types/appointment'
import type { Doctor } from '@/types/doctor'

const toast = useToast()

// Data
const appointments = ref<Appointment[]>([])
const doctors = ref<Doctor[]>([])
const selectedDate = ref(new Date().toISOString().split('T')[0])
const showCreateDialog = ref(false)
const showEventDialog = ref(false)
const selectedEvent = ref<Appointment | null>(null)
const dateMenu = ref(false)

// Filters
const filters = reactive({
  doctor_id: null as string | null,
  status: [] as string[],
  dateRange: [
    new Date().toISOString().split('T')[0],
    new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
  ] as string[],
})

// Stats
const stats = reactive({
  scheduled: 0,
  completed: 0,
  cancelled: 0,
})

const statusOptions = [
  { title: 'Запланировано', value: 'scheduled' },
  { title: 'Подтверждено', value: 'confirmed' },
  { title: 'В процессе', value: 'in_progress' },
  { title: 'Завершено', value: 'completed' },
  { title: 'Отменено', value: 'cancelled' },
  { title: 'Неявка', value: 'no_show' },
]

const dateRangeText = computed(() => {
  if (filters.dateRange.length === 2) {
    const start = new Date(filters.dateRange[0]).toLocaleDateString('ru-RU')
    const end = new Date(filters.dateRange[1]).toLocaleDateString('ru-RU')
    return `${start} - ${end}`
  }
  return 'Выберите период'
})

// Calendar events
const calendarEvents = computed(() => {
  return appointments.value.map(appointment => ({
    id: appointment.id,
    name: `${appointment.patient.last_name} ${appointment.patient.first_name}`,
    start: appointment.scheduled_start,
    end: appointment.scheduled_end,
    color: getEventColor(appointment),
    timed: true,
  }))
})

const getEventColor = (appointment: Appointment) => {
  const statusColors = {
    scheduled: 'blue',
    confirmed: 'green',
    in_progress: 'orange',
    completed: 'success',
    cancelled: 'red',
    no_show: 'grey',
  }
  return statusColors[appointment.status] || 'blue'
}

// Methods
const loadAppointments = async () => {
  try {
    const params = {
      doctor_id: filters.doctor_id,
      status: filters.status.length ? filters.status : undefined,
      start_date: filters.dateRange[0],
      end_date: filters.dateRange[1],
    }
    
    const response = await appointmentApi.getAppointments(params)
    appointments.value = response.data.items
    
    // Calculate stats
    calculateStats()
  } catch (error) {
    console.error('Error loading appointments:', error)
    toast.error('Ошибка загрузки записей')
  }
}

const loadDoctors = async () => {
  try {
    // Здесь загрузка врачей
    // const response = await doctorApi.getDoctors()
    // doctors.value = response.data
  } catch (error) {
    console.error('Error loading doctors:', error)
  }
}

const calculateStats = () => {
  stats.scheduled = appointments.value.filter(a => 
    ['scheduled', 'confirmed'].includes(a.status)
  ).length
  
  stats.completed = appointments.value.filter(a => 
    a.status === 'completed'
  ).length
  
  stats.cancelled = appointments.value.filter(a => 
    ['cancelled', 'no_show'].includes(a.status)
  ).length
}

const handleDateChange = () => {
  dateMenu.value = false
  loadAppointments()
}

const handleEventClick = ({ event }: any) => {
  const appointment = appointments.value.find(a => a.id === event.id)
  if (appointment) {
    selectedEvent.value = appointment
    showEventDialog.value = true
  }
}

const handleDayClick = ({ date }: any) => {
  selectedDate.value = date
  // Можно открыть диалог создания записи на выбранный день
}

const handleAppointmentSaved = () => {
  showCreateDialog.value = false
  loadAppointments()
}

const handleAppointmentUpdated = () => {
  showEventDialog.value = false
  loadAppointments()
}

const handleAppointmentCancelled = () => {
  showEventDialog.value = false
  loadAppointments()
}

// Lifecycle
onMounted(() => {
  loadDoctors()
  loadAppointments()
})
</script>

<style scoped>
.sidebar {
  border-right: 1px solid rgba(0, 0, 0, 0.12);
  height: calc(100vh - 64px);
  overflow-y: auto;
}
</style>