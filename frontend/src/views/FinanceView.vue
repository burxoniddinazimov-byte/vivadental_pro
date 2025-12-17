<template>
  <v-container fluid>
    <!-- Summary cards -->
    <v-row>
      <v-col cols="12" sm="6" md="3">
        <summary-card
          title="Выручка"
          :value="summary.revenue"
          icon="mdi-cash"
          color="green"
          trend="+12%"
        />
      </v-col>
      
      <v-col cols="12" sm="6" md="3">
        <summary-card
          title="Оплачено"
          :value="summary.collected"
          icon="mdi-credit-card-check"
          color="blue"
          trend="+8%"
        />
      </v-col>
      
      <v-col cols="12" sm="6" md="3">
        <summary-card
          title="Долги"
          :value="summary.debt"
          icon="mdi-alert-circle"
          color="red"
          trend="-5%"
        />
      </v-col>
      
      <v-col cols="12" sm="6" md="3">
        <summary-card
          title="Средний чек"
          :value="summary.avg_invoice"
          icon="mdi-calculator"
          color="orange"
          trend="+3%"
        />
      </v-col>
    </v-row>
    
    <!-- Charts and tables -->
    <v-row>
      <v-col cols="12" lg="8">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon start icon="mdi-chart-line" />
            Финансовая динамика
            <v-spacer />
            <v-select
              v-model="chartPeriod"
              :items="periodOptions"
              density="compact"
              variant="outlined"
              style="max-width: 150px;"
            />
          </v-card-title>
          
          <v-card-text>
            <apexchart
              type="line"
              height="350"
              :options="chartOptions"
              :series="chartSeries"
            />
          </v-card-text>
        </v-card>
      </v-col>
      
      <v-col cols="12" lg="4">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon start icon="mdi-chart-pie" />
            По услугам
          </v-card-title>
          
          <v-card-text>
            <apexchart
              type="donut"
              height="350"
              :options="pieChartOptions"
              :series="pieChartSeries"
            />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    
    <!-- Recent invoices -->
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon start icon="mdi-receipt" />
            Последние счета
            <v-spacer />
            <v-btn
              color="primary"
              variant="text"
              to="/finance/invoices"
            >
              Все счета
            </v-btn>
          </v-card-title>
          
          <v-card-text>
            <v-data-table
              :headers="invoiceHeaders"
              :items="recentInvoices"
              :loading="isLoading"
              hide-default-footer
            >
              <template v-slot:item.invoice_number="{ item }">
                <router-link
                  :to="`/finance/invoices/${item.id}`"
                  class="text-primary text-decoration-none"
                >
                  {{ item.invoice_number }}
                </router-link>
              </template>
              
              <template v-slot:item.patient="{ item }">
                {{ item.patient.last_name }} {{ item.patient.first_name }}
              </template>
              
              <template v-slot:item.status="{ item }">
                <v-chip
                  :color="getStatusColor(item.status)"
                  size="small"
                >
                  {{ getStatusText(item.status) }}
                </v-chip>
              </template>
              
              <template v-slot:item.balance_due="{ item }">
                <span :class="item.balance_due > 0 ? 'text-red' : 'text-green'">
                  {{ formatCurrency(item.balance_due) }}
                </span>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    
    <!-- Aging report -->
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon start icon="mdi-clock-alert" />
            Старение долгов
          </v-card-title>
          
          <v-card-text>
            <v-row>
              <v-col
                v-for="(item, index) in agingReport"
                :key="index"
                cols="12"
                sm="6"
                md="2"
              >
                <v-card variant="outlined">
                  <v-card-text class="text-center">
                    <div class="text-h6">{{ item.amount }}</div>
                    <div class="text-caption text-grey">{{ item.label }}</div>
                    <div class="text-caption">{{ item.count }} счетов</div>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useToast } from 'vue-toastification'
import { financeApi } from '@/api/endpoints'
import SummaryCard from '@/components/dashboard/SummaryCard.vue'
import type { Invoice } from '@/types/finance'

const toast = useToast()

// Data
const summary = reactive({
  revenue: 0,
  collected: 0,
  debt: 0,
  avg_invoice: 0,
})

const recentInvoices = ref<Invoice[]>([])
const isLoading = ref(false)
const chartPeriod = ref('30d')

// Charts
const chartSeries = ref([
  {
    name: 'Выручка',
    data: [30000, 32000, 28000, 35000, 40000, 38000, 42000],
  },
  {
    name: 'Оплачено',
    data: [25000, 28000, 24000, 32000, 35000, 33000, 38000],
  },
])

const chartOptions = computed(() => ({
  chart: {
    type: 'line',
    toolbar: { show: false },
  },
  colors: ['#4CAF50', '#2196F3'],
  stroke: {
    curve: 'smooth',
    width: 3,
  },
  xaxis: {
    categories: ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'],
  },
  yaxis: {
    labels: {
      formatter: (value: number) => `₽${value.toLocaleString()}`,
    },
  },
  tooltip: {
    y: {
      formatter: (value: number) => `₽${value.toLocaleString()}`,
    },
  },
}))

const pieChartSeries = ref([35, 25, 20, 15, 5])
const pieChartOptions = {
  chart: {
    type: 'donut',
  },
  labels: ['Лечение', 'Диагностика', 'Чистка', 'Имплантация', 'Прочее'],
  colors: ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#607D8B'],
  legend: {
    position: 'bottom',
  },
}

// Table
const invoiceHeaders = [
  { title: 'Номер счета', key: 'invoice_number' },
  { title: 'Пациент', key: 'patient' },
  { title: 'Дата', key: 'issue_date' },
  { title: 'Сумма', key: 'total_amount', align: 'end' },
  { title: 'Оплачено', key: 'paid_amount', align: 'end' },
  { title: 'Долг', key: 'balance_due', align: 'end' },
  { title: 'Статус', key: 'status' },
]

const agingReport = ref([
  { label: 'Текущие', amount: '₽120,000', count: 15 },
  { label: '1-30 дней', amount: '₽45,000', count: 8 },
  { label: '31-60 дней', amount: '₽28,000', count: 5 },
  { label: '61-90 дней', amount: '₽15,000', count: 3 },
  { label: '90+ дней', amount: '₽8,000', count: 2 },
  { label: 'Всего', amount: '₽216,000', count: 33 },
])

const periodOptions = [
  { title: '7 дней', value: '7d' },
  { title: '30 дней', value: '30d' },
  { title: '90 дней', value: '90d' },
  { title: 'Год', value: '1y' },
]

// Methods
const loadFinancialData = async () => {
  isLoading.value = true
  try {
    // Load summary
    const reportResponse = await financeApi.getFinancialReport({
      start_date: '2024-01-01',
      end_date: new Date().toISOString().split('T')[0],
      group_by: 'month',
    })
    
    const report = reportResponse.data
    summary.revenue = report.metrics.total_revenue
    summary.collected = report.metrics.collected_revenue
    summary.debt = report.metrics.outstanding_debt
    summary.avg_invoice = report.metrics.avg_invoice_amount
    
    // Load recent invoices
    const invoicesResponse = await financeApi.getInvoices({
      limit: 10,
      sort_by: 'issue_date',
      order: 'desc',
    })
    
    recentInvoices.value = invoicesResponse.data.items
  } catch (error) {
    console.error('Error loading financial data:', error)
    toast.error('Ошибка загрузки финансовых данных')
  } finally {
    isLoading.value = false
  }
}

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    paid: 'success',
    pending: 'warning',
    overdue: 'error',
    draft: 'grey',
  }
  return colors[status] || 'grey'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    paid: 'Оплачен',
    pending: 'Ожидает',
    overdue: 'Просрочен',
    draft: 'Черновик',
  }
  return texts[status] || status
}

// Lifecycle
onMounted(() => {
  loadFinancialData()
})
</script>