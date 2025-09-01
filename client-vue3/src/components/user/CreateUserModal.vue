<template>
  <div class="create-user-form">
    <!-- Username Field -->
    <div class="field">
      <label for="username" class="block text-900 font-medium mb-2">Username</label>
      <InputText
        id="username"
        v-model="form.username"
        placeholder="Enter username"
        class="w-full"
        :class="{ 'p-invalid': errors.username }"
        :disabled="isSubmitting"
        @blur="validateField('username')"
      />
      <small v-if="errors.username" class="p-error">{{ errors.username }}</small>
    </div>

    <!-- Password Field -->
    <div class="field">
      <label for="password" class="block text-900 font-medium mb-2">Password</label>
      <Password
        id="password"
        v-model="form.password"
        placeholder="Enter password"
        class="w-full"
        :class="{ 'p-invalid': errors.password }"
        :disabled="isSubmitting"
        :feedback="false"
        toggle-mask
        @blur="validateField('password')"
      />
      <small v-if="errors.password" class="p-error">{{ errors.password }}</small>
    </div>

    <!-- Confirm Password Field -->
    <div class="field">
      <label for="confirmPassword" class="block text-900 font-medium mb-2">Confirm Password</label>
      <Password
        id="confirmPassword"
        v-model="form.confirmPassword"
        placeholder="Confirm password"
        class="w-full"
        :class="{ 'p-invalid': errors.confirmPassword }"
        :disabled="isSubmitting"
        :feedback="false"
        toggle-mask
        @blur="validateField('confirmPassword')"
      />
      <small v-if="errors.confirmPassword" class="p-error">{{ errors.confirmPassword }}</small>
    </div>

    <!-- Admin Checkbox -->
    <div class="field-checkbox">
      <Checkbox
        id="isAdmin"
        v-model="form.isAdmin"
        binary
        :disabled="isSubmitting"
      />
      <label for="isAdmin" class="ml-2">Administrator privileges</label>
    </div>

    <!-- Action Buttons -->
    <div class="flex justify-content-end gap-2 mt-4">
      <Button
        label="Cancel"
        icon="pi pi-times"
        class="p-button-secondary"
        :disabled="isSubmitting"
        @click="handleCancel"
      />
      <Button
        label="Create User"
        icon="pi pi-check"
        class="p-button-success"
        :disabled="!isFormValid || isSubmitting"
        :loading="isSubmitting"
        @click="handleSubmit"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue';
import { useToast } from 'primevue/usetoast';
import { useAuthStore } from '@/stores/auth';

// PrimeVue components
import InputText from 'primevue/inputtext';
import Password from 'primevue/password';
import Checkbox from 'primevue/checkbox';
import Button from 'primevue/button';

// Props and emits
const emit = defineEmits<{
  'user-created': [];
  'cancel': [];
}>();

// Composables
const toast = useToast();
const authStore = useAuthStore();

// Form state
const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  isAdmin: false,
});

// Validation state
const errors = reactive({
  username: '',
  password: '',
  confirmPassword: '',
});

// UI state
const isSubmitting = ref(false);

// Form validation
const isFormValid = computed(() => (
  form.username.length > 0
    && form.password.length >= 6
    && form.confirmPassword === form.password
    && !errors.username
    && !errors.password
    && !errors.confirmPassword
));

// Validation functions
function validateField(field: keyof typeof errors): void {
  errors[field] = '';

  switch (field) {
    case 'username':
      if (!form.username.trim()) {
        errors.username = 'Username is required';
      } else if (form.username.trim().length < 3) {
        errors.username = 'Username must be at least 3 characters';
      }
      break;

    case 'password':
      if (!form.password) {
        errors.password = 'Password is required';
      } else if (form.password.length < 6) {
        errors.password = 'Password must be at least 6 characters';
      }
      // Also validate confirm password if it has been entered
      if (form.confirmPassword) {
        validateField('confirmPassword');
      }
      break;

    case 'confirmPassword':
      if (!form.confirmPassword) {
        errors.confirmPassword = 'Please confirm your password';
      } else if (form.confirmPassword !== form.password) {
        errors.confirmPassword = 'Passwords do not match';
      }
      break;

    default:
      // No validation needed for unknown fields
      break;
  }
}

function resetForm(): void {
  form.username = '';
  form.password = '';
  form.confirmPassword = '';
  form.isAdmin = false;
  errors.username = '';
  errors.password = '';
  errors.confirmPassword = '';
}

function validateForm(): boolean {
  validateField('username');
  validateField('password');
  validateField('confirmPassword');

  return isFormValid.value;
}

// Event handlers
function handleCancel(): void {
  resetForm();
  emit('cancel');
}

async function handleSubmit(): Promise<void> {
  if (!validateForm()) {
    return;
  }

  isSubmitting.value = true;

  try {
    const result = await authStore.createUser({
      username: form.username.trim(),
      password: form.password,
      is_admin: form.isAdmin,
    });

    if (result.success) {
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: result.message,
        life: 3000,
      });
      resetForm();
      emit('user-created');
    } else {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: result.message,
        life: 5000,
      });
    }
  } catch (error) {
    console.error('Error creating user:', error);
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'An unexpected error occurred while creating the user',
      life: 5000,
    });
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<style scoped>
.create-user-form {
  padding: 1rem;
}

.field {
  margin-bottom: 1.5rem;
}

.field-checkbox {
  display: flex;
  align-items: center;
  margin-bottom: 1.5rem;
}

/* Dark theme form styling */
:deep(.p-inputtext) {
  background-color: var(--surface-ground);
  border-color: var(--surface-border);
  color: var(--text-color);
}

:deep(.p-inputtext:focus) {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 0.2rem var(--primary-color-alpha);
}

:deep(.p-password .p-inputtext) {
  background-color: var(--surface-ground);
  border-color: var(--surface-border);
  color: var(--text-color);
}

:deep(.p-checkbox) {
  background-color: var(--surface-ground);
  border-color: var(--surface-border);
}

:deep(.p-checkbox.p-checkbox-checked) {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
}

/* Error styling */
:deep(.p-invalid) {
  border-color: var(--red-500) !important;
}

.p-error {
  color: var(--red-500);
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

/* Button styling */
:deep(.p-button-success) {
  background-color: #28a745;
  border-color: #28a745;
}

:deep(.p-button-success:hover) {
  background-color: #218838;
  border-color: #1e7e34;
}

:deep(.p-button-secondary) {
  background-color: var(--surface-500);
  border-color: var(--surface-500);
  color: var(--text-color);
}

:deep(.p-button-secondary:hover) {
  background-color: var(--surface-600);
  border-color: var(--surface-600);
}
</style>
