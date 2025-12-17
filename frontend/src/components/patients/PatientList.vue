<template>
  <div class="patient-list-container">
    <!-- Заголовок и кнопки -->
    <div class="list-header">
      <h1>Пациенты</h1>
      <div class="header-actions">
        <Button 
          label="Добавить пациента" 
          icon="pi pi-plus" 
          @click="showCreateDialog = true"
        />
        <span class="spacer"></span>
        <InputText 
          v-model="searchQuery" 
          placeholder="Поиск пациентов..." 
          @input="debouncedSearch"
        />
        <Button 
          icon="pi pi-filter" 
          severity="secondary" 
          @click="showFilters = !showFilters"
        />
      </div>
    </div>

    <!-- Фильтры -->
    <div v-if="showFilters" class="filters-panel">
      <div class="filter-row">
        <div class="filter-group">
          <label>Статус:</label>
          <Select v-model="filters.status" :options="statusOptions" />
        </div>
        <div class="filter-group">
          <label>Дата регистрации:</label>
          <Calendar 
            v-model="filters.createdAfter" 
            dateFormat="dd.mm.yy" 
            placeholder="От"
          />
          <Calendar 
            v-model="filters.createdBefore" 
            dateFormat="dd.mm.yy" 
            placeholder="До"
          />
        </div>
        <Button label="Применить" @click="applyFilters" />
        <Button label="Сбросить" severity="secondary" @click="resetFilters" />
      </div>
    </div>

    <!-- Таблица пациентов -->
    <DataTable 
      :value="patients" 
      :loading="isLoading"
      :paginator="true"
      :rows="pageSize"
      :totalRecords="total"
      :rowsPerPageOptions="[10, 20, 50]"
      @page="onPageChange"
      paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
      currentPageReportTemplate="Показано {first} - {last} из {totalRecords}"
    >
      <Column field="id" header="ID" :sortable="true">
        <template #body="{ data }">
          <span class="patient-id">{{ data.id.substring(0, 8) }}...</span>
        </template>
      </Column>
      
      <Column field="full_name" header="Пациент" :sortable="true">
        <template #body="{ data }">
          <div class="patient-info">
            <Avatar 
              :label="getInitials(data)" 
              :style="{ 
                'background-color': stringToColor(data.last_name),
                'color': 'white'
              }" 
              size="normal" 
              shape="circle"
            />
            <div class="patient-details">
              <router-link 
                :to="`/patients/${data.id}`" 
                class="patient-name"
              >
                {{ data.last_name }} {{ data.first_name }} {{ data.middle_name || '' }}
              </router-link>
              <div class="patient-contacts">
                <span class="phone">
                  <i class="pi pi-phone"></i> {{ formatPhone(data.phone) }}
                </span>
                <span v-if="data.email" class="email">
                  <i class="pi pi-envelope"></i> {{ data.email }}
                </span>
              </div>
            </div>
          </div>
        </template>
      </Column>
      
      <Column field="birth_date" header="Дата рождения" :sortable="true">
        <template #body="{ data }">
          {{ formatDate(data.birth_date) }}
        </template>
      </Column>
      
      <Column field="created_at" header="Дата регистрации" :sortable="true">
        <template #body="{ data }">
          {{ formatDateTime(data.created_at) }}
        </template>
      </Column>
      
      <Column field="status" header="Статус">
        <template #body="{ data }">
          <Tag 
            :value="data.is_active ? 'Активен' : 'Неактивен'" 
            :severity="data.is_active ? 'success' : 'danger'"
          />
        </template>
      </Column>
      
      <Column header="Действия">
        <template #body="{ data }">
          <div class="action-buttons">
            <Button 
              icon="pi pi-eye" 
              severity="info" 
              text 
              rounded 
              @click="viewPatient(data.id)"
            />
            <Button 
              icon="pi pi-pencil" 
              severity="warning" 
              text 
              rounded 
              @click="editPatient(data)"
            />
            <Button 
              icon="pi pi-trash" 
              severity="danger" 
              text 
              rounded 
              @click="confirmDelete(data)"
            />
          </div>
        </template>
      </Column>
    </DataTable>

    <!-- Диалог создания/редактирования -->
    <Dialog 
      v-model:visible="showCreateDialog" 
      :header="editingPatient ? 'Редактировать пациента' : 'Новый пациент'"
      :modal="true"
      :style="{ width: '600px' }"
    >
      <PatientForm 
        v-if="showCreateDialog"
        :patient="editingPatient"
        @submit="handleFormSubmit"
        @cancel="closeDialog"
      />
    </Dialog>

    <!-- Диалог подтверждения удаления -->
    <Dialog 
      v-model:visible="showDeleteDialog" 
      header="Подтверждение удаления"
      :modal="true"
      :style="{ width: '400px' }"
    >
      <div class="delete-confirm">
        <p>Вы уверены, что хотите удалить пациента?</p>
        <div class="patient-preview">
          <strong>{{ patientToDelete?.last_name }} {{ patientToDelete?.first_name }}</strong>
          <br />
          {{ patientToDelete?.phone }}
        </div>
      </div>
      <template #footer>
        <Button label="Отмена" severity="secondary" @click="showDeleteDialog = false" />
        <Button label="Удалить" severity="danger" @click="deletePatient" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { usePatientStore } from '@/stores/patient'
import { useDebounceFn } from '@vueuse/core'
import { toast } from 'vue3-toastify'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Calendar from 'primevue/calendar'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import Avatar from 'primevue/avatar'
import PatientForm from './PatientForm.vue'
import type { Patient } from '@/types/patient'

const router = useRouter()
const patientStore = usePatientStore()

// Состояние
const searchQuery = ref('')
const showFilters = ref(false)
const showCreateDialog = ref(false)
const showDeleteDialog = ref(false)
const editingPatient = ref<Patient | null>(null)
const patientToDelete = ref<Patient | null>(null)
const page = ref(1)
const pageSize = ref(20)

// Фильтры
const filters = ref({
  status: 'active',
  createdAfter: null,
  createdBefore: null
})

const statusOptions = [
  { label: 'Все', value: 'all' },
  { label: 'Активные', value: 'active' },
  { label: 'Неактивные', value: 'inactive' }
]

// Компьютеды
const patients = computed(() => patientStore.patients)
const isLoading = computed(() => patientStore.isLoading)
const total = computed(() => patientStore.total)

// Хелперы
const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('ru-RU')
}

const formatDateTime = (dateString: string) => {
  return new Date(dateString).toLocaleString('ru-RU')
}

const formatPhone = (phone: string) => {
  return phone.replace(/(\d{1})(\d{3})(\d{3})(\d{2})(\d{2})/, '+$1 ($2) $3-$4-$5')
}

const getInitials = (patient: Patient) => {
  return (patient.last_name[0] + patient.first_name[0]).toUpperCase()
}

const stringToColor = (str: string) => {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
  }
  const color = Math.floor(Math.abs(Math.sin(hash) * 16777215)).toString(16)
  return `#${'000000'.substring(0, 6 - color.length)}${color}`
}

// Методы
const loadPatients = () => {
  patientStore.fetchPatients({
    page: page.value,
    limit: pageSize.value,
    search: searchQuery.value || undefined,
    is_active: filters.value.status === 'active' ? true : 
              filters.value.status === 'inactive' ? false : undefined
  })
}

const debouncedSearch = useDebounceFn(() => {
  page.value = 1
  loadPatients()
}, 500)

const onPageChange = (event: any) => {
  page.value = event.page + 1
  pageSize.value = event.rows
  loadPatients()
}

const applyFilters = () => {
  page.value = 1
  loadPatients()
}

const resetFilters = () => {
  filters.value = {
    status: 'active',
    createdAfter: null,
    createdBefore: null
  }
  searchQuery.value = ''
  loadPatients()
}

const viewPatient = (id: string) => {
  router.push(`/patients/${id}`)
}

const editPatient = (patient: Patient) => {
  editingPatient.value = patient
  showCreateDialog.value = true
}

const confirmDelete = (patient: Patient) => {
  patientToDelete.value = patient
  showDeleteDialog.value = true
}

const deletePatient = async () => {
  if (!patientToDelete.value) return
  
  try {
    await patientStore.deletePatient(patientToDelete.value.id)
    toast.success('Пациент удален')
    showDeleteDialog.value = false
  } catch (error) {
    toast.error('Ошибка при удалении пациента')
  }
}

const handleFormSubmit = async (patientData: any) => {
  try {
    if (editingPatient.value) {
      await patientStore.updatePatient(editingPatient.value.id, patientData)
      toast.success('Пациент обновлен')
    } else {
      await patientStore.createPatient(patientData)
      toast.success('Пациент создан')
    }
    showCreateDialog.value = false
    editingPatient.value = null
    loadPatients()
  } catch (error) {
    toast.error('Ошибка при сохранении пациента')
  }
}

const closeDialog = () => {
  showCreateDialog.value = false
  editingPatient.value = null
}

// Хуки
onMounted(() => {
  loadPatients()
})

// Вотчеры
watch([page, pageSize], loadPatients)
</script>

<style scoped>
.patient-list-container {
  padding: 24px;
  background: #f9fafb;
  min-height: calc(100vh - 60px);
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.list-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #111827;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.spacer {
  flex: 1;
}

.filters-panel {
  background: white;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
  border: 1px solid #e5e7eb;
}

.filter-row {
  display: flex;
  gap: 16px;
  align-items: flex-end;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-group label {
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
}

.patient-id {
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  color: #6b7280;
}

.patient-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.patient-details {
  display: flex;
  flex-direction: column;
}

.patient-name {
  font-weight: 600;
  color: #3b82f6;
  text-decoration: none;
}

.patient-name:hover {
  text-decoration: underline;
}

.patient-contacts {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #6b7280;
}

.patient-contacts .phone,
.patient-contacts .email {
  display: flex;
  align-items: center;
  gap: 4px;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.delete-confirm {
  text-align: center;
}

.delete-confirm p {
  margin-bottom: 16px;
}

.patient-preview {
  padding: 12px;
  background: #f3f4f6;
  border-radius: 6px;
  margin-bottom: 16px;
}
</style>