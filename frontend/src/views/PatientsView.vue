<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon start icon="mdi-account-group" />
            Пациенты
            <v-spacer />
            <v-btn
              color="primary"
              prepend-icon="mdi-plus"
              @click="showCreateDialog = true"
            >
              Новый пациент
            </v-btn>
          </v-card-title>
          
          <v-card-text>
            <!-- Filters -->
            <v-row class="mb-4">
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="filters.search"
                  label="Поиск пациентов"
                  prepend-inner-icon="mdi-magnify"
                  variant="outlined"
                  clearable
                  @update:model-value="debouncedSearch"
                />
              </v-col>
              
              <v-col cols="12" md="3">
                <v-select
                  v-model="filters.status"
                  :items="statusOptions"
                  label="Статус"
                  variant="outlined"
                  clearable
                />
              </v-col>
              
              <v-col cols="12" md="3">
                <v-select
                  v-model="filters.sortBy"
                  :items="sortOptions"
                  label="Сортировка"
                  variant="outlined"
                />
              </v-col>
            </v-row>
            
            <!-- Patients table -->
            <v-data-table
              :headers="headers"
              :items="patients"
              :loading="isLoading"
              :items-per-page="10"
              :page="page"
              @update:page="page = $event"
            >
              <template v-slot:item.full_name="{ item }">
                <div class="d-flex align-center">
                  <v-avatar size="36" class="mr-3">
                    <v-img
                      v-if="item.avatar"
                      :src="item.avatar"
                    />
                    <v-icon v-else>mdi-account</v-icon>
                  </v-avatar>
                  <div>
                    <strong>{{ item.last_name }} {{ item.first_name }}</strong>
                    <div class="text-caption text-grey">
                      {{ item.middle_name || '' }}
                    </div>
                  </div>
                </div>
              </template>
              
              <template v-slot:item.contacts="{ item }">
                <div>
                  <div class="d-flex align-center">
                    <v-icon size="small" class="mr-1">mdi-phone</v-icon>
                    {{ item.phone }}
                  </div>
                  <div v-if="item.email" class="d-flex align-center">
                    <v-icon size="small" class="mr-1">mdi-email</v-icon>
                    {{ item.email }}
                  </div>
                </div>
              </template>
              
              <template v-slot:item.stats="{ item }">
                <div class="text-caption">
                  <div>Записей: {{ item.total_appointments || 0 }}</div>
                  <div>Последний визит: {{ formatDate(item.last_visit) }}</div>
                </div>
              </template>
              
              <template v-slot:item.status="{ item }">
                <v-chip
                  :color="item.is_active ? 'success' : 'grey'"
                  size="small"
                >
                  {{ item.is_active ? 'Активен' : 'Неактивен' }}
                </v-chip>
              </template>
              
              <template v-slot:item.actions="{ item }">
                <v-btn
                  icon
                  size="small"
                  @click="viewPatient(item.id)"
                >
                  <v-icon>mdi-eye</v-icon>
                </v-btn>
                <v-btn
                  icon
                  size="small"
                  @click="editPatient(item)"
                >
                  <v-icon>mdi-pencil</v-icon>
                </v-btn>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    
    <!-- Create/Edit Patient Dialog -->
    <v-dialog v-model="showCreateDialog" max-width="600">
      <patient-form
        v-model="showCreateDialog"
        :patient="editingPatient"
        @saved="handlePatientSaved"
      />
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
import { patientApi } from '@/api/endpoints'
import PatientForm from '@/components/patients/PatientForm.vue'
import type { Patient } from '@/types/patient'

const router = useRouter()

// Data
const patients = ref<Patient[]>([])
const isLoading = ref(false)
const page = ref(1)
const showCreateDialog = ref(false)
const editingPatient = ref<Patient | null>(null)

// Filters
const filters = reactive({
  search: '',
  status: 'active',
  sortBy: 'last_name',
})

// Table headers
const headers = [
  { title: 'Пациент', key: 'full_name', sortable: true },
  { title: 'Контакты', key: 'contacts', sortable: false },
  { title: 'Дата рождения', key: 'birth_date', sortable: true },
  { title: 'Статистика', key: 'stats', sortable: false },
  { title: 'Статус', key: 'status', sortable: true },
  { title: 'Действия', key: 'actions', sortable: false, align: 'end' },
]

const statusOptions = [
  { title: 'Активные', value: 'active' },
  { title: 'Все', value: 'all' },
]

const sortOptions = [
  { title: 'По фамилии', value: 'last_name' },
  { title: 'По дате регистрации', value: 'created_at' },
  { title: 'По последнему визиту', value: 'last_visit' },
]

// Methods
const fetchPatients = async () => {
  isLoading.value = true
  try {
    const params = {
      search: filters.search,
      is_active: filters.status === 'active' ? true : undefined,
      sort_by: filters.sortBy,
      page: page.value,
    }
    
    const response = await patientApi.getPatients(params)
    patients.value = response.data.items
  } catch (error) {
    console.error('Error fetching patients:', error)
  } finally {
    isLoading.value = false
  }
}

const debouncedSearch = useDebounceFn(() => {
  fetchPatients()
}, 500)

const formatDate = (dateString: string) => {
  if (!dateString) return '—'
  return new Date(dateString).toLocaleDateString('ru-RU')
}

const viewPatient = (id: string) => {
  router.push(`/patients/${id}`)
}

const editPatient = (patient: Patient) => {
  editingPatient.value = patient
  showCreateDialog.value = true
}

const handlePatientSaved = () => {
  showCreateDialog.value = false
  editingPatient.value = null
  fetchPatients()
}

// Watchers
watch([() => filters.status, () => filters.sortBy, page], () => {
  fetchPatients()
})

// Lifecycle
onMounted(() => {
  fetchPatients()
})
</script>