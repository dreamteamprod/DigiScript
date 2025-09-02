<template>
  <div class="login-container">
    <div class="login-form-container">
      <h3 class="login-title">Login to DigiScript</h3>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="username" class="form-label">Username</label>
          <InputText
            id="username"
            v-model="loginForm.username"
            type="text"
            class="form-control"
            @keydown.enter="handleLogin"
          />
        </div>

        <div class="form-group">
          <label for="password" class="form-label">Password</label>
          <Password
            id="password"
            v-model="loginForm.password"
            :feedback="false"
            toggleMask
            class="form-control"
            @keydown.enter="handleLogin"
          />
        </div>

        <Button
          type="submit"
          :disabled="isSubmitting || !isFormValid"
          :loading="isSubmitting"
          :label="isSubmitting ? 'Logging in...' : 'Login'"
          class="login-btn"
        />
      </form>

      <Message
        v-if="showLoginError"
        severity="error"
        :closable="false"
        class="login-error"
      >
        Login unsuccessful. Please check your credentials and try again.
      </Message>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';

// PrimeVue Components
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import Password from 'primevue/password';

import { useAuthStore } from '../stores/auth';

const router = useRouter();
const authStore = useAuthStore();

// Form state
const loginForm = ref({
  username: '',
  password: '',
});

// UI state
const isSubmitting = ref(false);
const showLoginError = ref(false);

// Validation - simple validation without showing errors initially
const isFormValid = computed(() => loginForm.value.username.trim().length > 0
  && loginForm.value.password.trim().length > 0);

// Login handler
async function handleLogin() {
  if (!isFormValid.value || isSubmitting.value) {
    return;
  }

  isSubmitting.value = true;
  showLoginError.value = false;

  try {
    const loginSuccess = await authStore.userLogin({
      username: loginForm.value.username.trim(),
      password: loginForm.value.password,
    });

    if (loginSuccess) {
      // Redirect to home page
      await router.push('/');
    } else {
      showLoginError.value = true;
    }
  } catch (error) {
    console.error('Login error:', error);
    showLoginError.value = true;
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<style scoped>
/* Login container matching Vue 2 exactly */
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 120px); /* Account for header height */
  background-color: #343a40;
  text-align: center;
  padding: 2rem 1rem;
}

.login-form-container {
  width: 100%;
  max-width: 400px;
}

.login-title {
  color: white;
  font-size: 1.5rem;
  margin-bottom: 2rem;
  font-weight: normal;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  text-align: left;
}

.form-label {
  display: block;
  color: white;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
  font-weight: normal;
}

/* PrimeVue component styling overrides */
.form-control {
  width: 100%;
}

.form-control :deep(.p-inputtext),
.form-control :deep(.p-password-input) {
  width: 100%;
  padding: 0.5rem 0.75rem;
  font-size: 1rem;
  line-height: 1.5;
  color: #495057;
  background-color: #fff;
  border: 1px solid #ced4da;
  border-radius: 0.25rem;
  transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
}

.form-control :deep(.p-inputtext:focus),
.form-control :deep(.p-password-input:focus) {
  color: #495057;
  background-color: #fff;
  border-color: #80bdff;
  outline: 0;
  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}

.login-btn {
  margin-top: 1rem;
  width: 100%;
}

.login-btn :deep(.p-button) {
  width: 100%;
  padding: 0.5rem 1rem;
  font-size: 1rem;
  line-height: 1.5;
  border-radius: 0.25rem;
  background-color: #007bff;
  border-color: #007bff;
  transition: color 0.15s ease-in-out, background-color 0.15s ease-in-out,
    border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
}

.login-btn :deep(.p-button:hover:not(:disabled)) {
  background-color: #0056b3;
  border-color: #004085;
}

.login-btn :deep(.p-button:focus) {
  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.5);
}

.login-btn :deep(.p-button:disabled) {
  opacity: 0.65;
  cursor: not-allowed;
}

.login-error {
  margin-top: 1.5rem;
}

.login-error :deep(.p-message) {
  text-align: left;
}

/* Responsive adjustments */
@media (max-width: 576px) {
  .login-form-container {
    max-width: 320px;
  }

  .login-title {
    font-size: 1.25rem;
  }
}
</style>
