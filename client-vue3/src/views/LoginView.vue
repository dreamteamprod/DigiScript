<template>
  <div class="flex items-center justify-center min-h-screen bg-gray-50">
    <Card style="width: 25rem" class="p-4">
      <template #header>
        <div class="text-center p-4">
          <h3 class="text-2xl font-semibold text-gray-800 mb-0">Login to DigiScript</h3>
        </div>
      </template>

      <template #content>
        <form @submit.prevent="handleLogin" class="space-y-4">
          <div class="field">
            <label
              for="username"
              class="block text-sm font-medium text-gray-700 mb-2"
            >
              Username
            </label>
            <InputText
              id="username"
              v-model="loginForm.username"
              :class="{ 'p-invalid': usernameError }"
              placeholder="Enter your username"
              class="w-full"
              @keydown.enter="handleLogin"
            />
            <small v-if="usernameError" class="p-error">{{ usernameError }}</small>
          </div>

          <div class="field">
            <label
              for="password"
              class="block text-sm font-medium text-gray-700 mb-2"
            >
              Password
            </label>
            <Password
              id="password"
              v-model="loginForm.password"
              :class="{ 'p-invalid': passwordError }"
              placeholder="Enter your password"
              :feedback="false"
              toggle-mask
              class="w-full"
              @keydown.enter="handleLogin"
            />
            <small v-if="passwordError" class="p-error">{{ passwordError }}</small>
          </div>

          <Button
            type="submit"
            :disabled="isSubmitting || !isFormValid"
            :loading="isSubmitting"
            class="w-full"
            severity="primary"
          >
            Login
          </Button>
        </form>

        <Message
          v-if="showLoginError"
          severity="error"
          class="mt-4"
          :closable="false"
        >
          Login unsuccessful. Please check your credentials and try again.
        </Message>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import Card from 'primevue/card';
import InputText from 'primevue/inputtext';
import Password from 'primevue/password';
import Button from 'primevue/button';
import Message from 'primevue/message';
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

// Validation
const usernameError = computed(() => {
  if (!loginForm.value.username.trim()) {
    return 'Username is required';
  }
  return null;
});

const passwordError = computed(() => {
  if (!loginForm.value.password.trim()) {
    return 'Password is required';
  }
  return null;
});

const isFormValid = computed(() => !usernameError.value && !passwordError.value
         && loginForm.value.username.trim() && loginForm.value.password.trim());

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
.field {
  margin-bottom: 1rem;
}

.p-password {
  width: 100%;
}

.p-password > .p-inputtext {
  width: 100%;
}
</style>
