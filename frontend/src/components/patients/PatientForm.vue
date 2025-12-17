<template>
  <v-card>
    <v-card-title>
      <span v-if="props.patient">Редактирование пациента</span>
      <span v-else>Новый пациент</span>
    </v-card-title>
    
    <v-card-text>
      <v-form ref="form" v-model="isValid" @submit.prevent="save">
        <v-row>
          <v-col cols="12" md="4">
            <v-text-field
              v-model="formData.last_name"
              label="Фамилия"
              :rules="[requiredRule]"
              variant="outlined"
            />
          </v-col>
          
          <v-col cols="12" md="4">
            <v-text-field
              v-model="formData.first_name"
              label="Имя"
              :rules="[requiredRule]"
              variant="outlined"
            />
          </v-col>
          
          <v-col cols="12" md="4">
            <v-text-field
              v-model="formData.middle_name"
              label="Отчество"
              variant="outlined"
            />
          </v-col>
        </v-row>
        
        <v-row>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="formData.phone"
              label="Телефон"
              :rules="[requiredRule, phoneRule]"
              variant="outlined"
            />
          </v-col>
          
          <v-col cols="12" md="6">
            <v-text-field
              v-model="formData.email"
              label="Email"
              :rules="[emailRule]"
              variant="outlined"
            />
          </v-col>
        </v-row>
        
        <v-row>
          <v-col cols="12" md="6">
            <v-date-picker
              v-model="formData.birth_date"
              label="Дата рождения"
              :max="maxDate"
              variant="outlined"
            />
          </v-col>
          
          <v-col cols="12" md="6">
            <v-select
              v-model="formData.gender"
              :items="genderOptions"
              label="Пол"
              variant="outlined"
            />
          </v-col>
        </v-row>
        
        <v-row>
          <v-col cols="12">
            <v-textarea
              v-model="formData.notes"
              label="Примечания"
              variant="outlined"
              rows="2"
            />
          </v-col>
        </v-row>
      </v-form>
    </v-card-text>
    
    <v-card-actions>
      <v-spacer />
      <v-btn
        variant="text"
        @click="emit('update:modelValue', false)"
      >
        Отмена
      </v-btn>
      <v-btn
        color="primary"
        :loading="isSaving"
        @click="save"
      >
        Сохранить
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from 'vue'
import { useToast } from 'vue-toastification'
import { patientApi } from '@/api/endpoints'
import type { Patient } from '@/types/patient'

const props = defineProps<{
  modelValue: boolean
  patient?: Patient | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: []
}>()

const toast = useToast()
const form = ref()
const isValid = ref(false)
const isSaving = ref(false)

// Form data
const formData = reactive({
  last_name: '',
  first_name: '',
  middle_name: '',
  phone: '',
  email: '',
  birth_date: '',
  gender: '',
  notes: '',
})

// Validation rules
const requiredRule = (v: string) => !!v || 'Обязательное поле'
const phoneRule = (v: string) => /^\+?[1-9]\d{1,14}$/.test(v) || 'Некорректный телефон'
const emailRule = (v: string) => !v || /.+@.+\..+/.test(v) || 'Некорректный email'

const maxDate = computed(() => {
  const date = new Date()
  date.setFullYear(date.getFullYear() - 18)
  return date.toISOString().split('T')[0]
})

const genderOptions = [
  { title: 'Мужской', value: 'male' },
  { title: 'Женский', value: 'female' },
  { title: 'Другой', value: 'other' },
]

// Load patient data for editing
watch(() => props.patient, (patient) => {
  if (patient) {
    Object.assign(formData, {
      last_name: patient.last_name,
      first_name: patient.first_name,
      middle_name: patient.middle_name || '',
      phone: patient.phone,
      email: patient.email || '',
      birth_date: patient.birth_date,
      gender: patient.gender || '',
      notes: patient.notes || '',
    })
  } else {
    // Reset form for new patient
    Object.keys(formData).forEach(key => {
      formData[key as keyof typeof formData] = ''
    })
  }
}, { immediate: true })

const save = async () => {
  const { valid } = await form.value.validate()
  
  if (!valid) {
    toast.error('Заполните все обязательные поля')
    return
  }
  
  isSaving.value = true
  
  try {
    if (props.patient) {
      // Update existing patient
      await patientApi.updatePatient(props.patient.id, formData)
      toast.success('Данные пациента обновлены')
    } else {
      // Create new patient
      await patientApi.createPatient(formData)
      toast.success('Пациент успешно создан')
    }
    
    emit('saved')
    emit('update:modelValue', false)
  } catch (error: any) {
    toast.error(error.response?.data?.detail || 'Ошибка сохранения')
  } finally {
    isSaving.value = false
  }
}
</script>