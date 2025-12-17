<template>
  <v-app>
    <app-navbar />
    
    <v-main>
      <v-container fluid class="pa-0">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </v-container>
    </v-main>
    
    <app-footer />
    
    <v-snackbar
      v-model="snackbar.visible"
      :color="snackbar.color"
      :timeout="3000"
    >
      {{ snackbar.message }}
    </v-snackbar>
  </v-app>
</template>

<script setup lang="ts">
import { ref, provide } from 'vue'
import AppNavbar from '@/components/layout/AppNavbar.vue'
import AppFooter from '@/components/layout/AppFooter.vue'

// Global snackbar
const snackbar = ref({
  visible: false,
  message: '',
  color: 'success',
})

const showSnackbar = (message: string, color = 'success') => {
  snackbar.value = {
    visible: true,
    message,
    color,
  }
}

// Provide snackbar to child components
provide('snackbar', { showSnackbar })
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>