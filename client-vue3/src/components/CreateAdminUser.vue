<template>
  <div class="create-admin-user">
    <form @submit.prevent="createUser" class="admin-form">
      <div class="form-group">
        <label for="username" class="form-label">Username</label>
        <InputText
          id="username"
          v-model="formState.username"
          :disabled="true"
          :class="{ 'p-invalid': errors.username }"
          class="form-input"
        />
        <small v-if="errors.username" class="error-message">
          {{ errors.username }}
        </small>
      </div>

      <div class="form-group">
        <label for="password" class="form-label">Password</label>
        <Password
          id="password"
          v-model="formState.password"
          :class="{ 'p-invalid': errors.password }"
          :feedback="false"
          toggleMask
          class="form-input"
        />
        <small v-if="errors.password" class="error-message">
          {{ errors.password }}
        </small>
      </div>

      <div class="form-group">
        <label for="confirmPassword" class="form-label">Confirm Password</label>
        <Password
          id="confirmPassword"
          v-model="formState.confirmPassword"
          :class="{ 'p-invalid': errors.confirmPassword }"
          :feedback="false"
          toggleMask
          class="form-input"
        />
        <small v-if="errors.confirmPassword" class="error-message">
          {{ errors.confirmPassword }}
        </small>
      </div>

      <div class="form-actions">
        <Button
          type="submit"
          :disabled="!isFormValid || isSubmitting"
          :loading="isSubmitting"
          label="Save"
          icon="pi pi-check"
          severity="success"
          class="save-button"
        />
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import InputText from 'primevue/inputtext';
import Password from 'primevue/password';
import Button from 'primevue/button';
import { useToast } from 'primevue/usetoast';
import { useAuthStore } from '../stores/auth';
import { useSettingsStore } from '../stores/settings';

// Props (for future expansion)
interface Props {
  isFirstAdmin?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  isFirstAdmin: false,
});

// Emits
const emit = defineEmits<{
  'user-created': [];
}>();

// Dependencies
const toast = useToast();
const authStore = useAuthStore();
const settingsStore = useSettingsStore();

// Form state
const formState = ref({
  username: props.isFirstAdmin ? 'admin' : '',
  password: '',
  confirmPassword: '',
});

const errors = ref({
  username: '',
  password: '',
  confirmPassword: '',
});

const isSubmitting = ref(false);

// Computed
const isFormValid = computed(() => (
  formState.value.username.length > 0
    && formState.value.password.length >= 6
    && formState.value.confirmPassword === formState.value.password
    && !errors.value.username
    && !errors.value.password
    && !errors.value.confirmPassword
));

// Validation
function validateConfirmPassword() {
  if (!formState.value.confirmPassword) {
    errors.value.confirmPassword = 'This is a required field.';
  } else if (formState.value.confirmPassword !== formState.value.password) {
    errors.value.confirmPassword = 'Passwords do not match.';
  } else {
    errors.value.confirmPassword = '';
  }
}

function validateUsername() {
  if (!formState.value.username) {
    errors.value.username = 'This is a required field.';
  } else {
    errors.value.username = '';
  }
}

function validatePassword() {
  if (!formState.value.password) {
    errors.value.password = 'This is a required field and must be at least 6 characters.';
  } else if (formState.value.password.length < 6) {
    errors.value.password = 'This is a required field and must be at least 6 characters.';
  } else {
    errors.value.password = '';
  }

  // Also revalidate confirm password if it has a value
  if (formState.value.confirmPassword) {
    validateConfirmPassword();
  }
}

// Watch for changes and validate
watch(() => formState.value.username, validateUsername);
watch(() => formState.value.password, validatePassword);
watch(() => formState.value.confirmPassword, validateConfirmPassword);

// Actions
async function createUser() {
  // Final validation
  validateUsername();
  validatePassword();
  validateConfirmPassword();

  if (!isFormValid.value) {
    return;
  }

  isSubmitting.value = true;

  try {
    const userData = {
      username: formState.value.username,
      password: formState.value.password,
      is_admin: props.isFirstAdmin,
    };

    await authStore.createUser(userData);

    // If this was the first admin creation, refresh settings to update has_admin_user
    if (props.isFirstAdmin) {
      await settingsStore.getSettings();
    }

    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'User created successfully!',
      life: 3000,
    });

    emit('user-created');
  } catch (error) {
    console.error('Error creating user:', error);
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Unable to create user. Please try again.',
      life: 5000,
    });
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<style scoped>
.create-admin-user {
  width: 100%;
  max-width: 400px;
  margin: 0 auto;
}

.admin-form {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #2d3748;
  font-size: 0.875rem;
}

.form-input {
  width: 100%;
}

.error-message {
  color: #e53e3e;
  font-size: 0.75rem;
  margin-top: 0.25rem;
  display: block;
}

.form-actions {
  margin-top: 2rem;
  text-align: center;
}

.save-button {
  width: 100%;
}

/* Dark theme compatibility */
@media (prefers-color-scheme: dark) {
  .admin-form {
    background: #2d3748;
    border-color: #4a5568;
  }

  .form-label {
    color: #e2e8f0;
  }
}
</style>
