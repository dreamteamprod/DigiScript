<template>
  <Form
    v-slot="$form"
    :initialValues="initialValues"
    :resolver="resolver"
    @submit="handleSubmit"
    class="create-user-form"
  >
    <!-- Username Field -->
    <div class="field">
      <label for="username" class="block text-900 font-medium mb-2">Username</label>
      <InputText
        id="username"
        name="username"
        placeholder="Enter username"
        class="w-full"
        :class="{ 'p-invalid': $form.username?.invalid }"
        :disabled="isSubmitting"
        fluid
      />
      <Message
        v-if="$form.username?.invalid"
        severity="error"
        size="small"
        variant="simple"
      >
        {{ $form.username.error?.message }}
      </Message>
    </div>

    <!-- Password Field -->
    <div class="field">
      <label for="password" class="block text-900 font-medium mb-2">Password</label>
      <Password
        id="password"
        name="password"
        placeholder="Enter password"
        class="w-full"
        :class="{ 'p-invalid': $form.password?.invalid }"
        :disabled="isSubmitting"
        :feedback="false"
        toggle-mask
        fluid
      />
      <Message
        v-if="$form.password?.invalid"
        severity="error"
        size="small"
        variant="simple"
      >
        {{ $form.password.error?.message }}
      </Message>
    </div>

    <!-- Confirm Password Field -->
    <div class="field">
      <label for="confirmPassword" class="block text-900 font-medium mb-2">Confirm Password</label>
      <Password
        id="confirmPassword"
        name="confirmPassword"
        placeholder="Confirm password"
        class="w-full"
        :class="{ 'p-invalid': $form.confirmPassword?.invalid }"
        :disabled="isSubmitting"
        :feedback="false"
        toggle-mask
        fluid
      />
      <Message
        v-if="$form.confirmPassword?.invalid"
        severity="error"
        size="small"
        variant="simple"
      >
        {{ $form.confirmPassword.error?.message }}
      </Message>
    </div>

    <!-- Admin Checkbox -->
    <div class="field-checkbox">
      <Checkbox
        id="isAdmin"
        name="isAdmin"
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
        type="button"
        :disabled="isSubmitting"
        @click="handleCancel"
      />
      <Button
        label="Create User"
        icon="pi pi-check"
        class="p-button-success"
        type="submit"
        :disabled="!$form.valid || isSubmitting"
        :loading="isSubmitting"
      />
    </div>
  </Form>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useToast } from 'primevue/usetoast';
import { useAuthStore } from '@/stores/auth';
import { zodResolver } from '@primevue/forms/resolvers/zod';

// PrimeVue components
import Form from '@primevue/forms/form';
import type { FormSubmitEvent } from '@primevue/forms/form';
import InputText from 'primevue/inputtext';
import Password from 'primevue/password';
import Checkbox from 'primevue/checkbox';
import Button from 'primevue/button';
import Message from 'primevue/message';

// Validation schema
import { createUserSchema, createUserDefaults, type CreateUserFormData } from '@/schemas/userValidation';

// Props and emits
const emit = defineEmits<{
  'user-created': [];
  'cancel': [];
}>();

// Composables
const toast = useToast();
const authStore = useAuthStore();

// Form configuration
const initialValues = createUserDefaults;
const resolver = zodResolver(createUserSchema);

// UI state
const isSubmitting = ref(false);

// Event handlers
function handleCancel(): void {
  emit('cancel');
}

async function handleSubmit(event: FormSubmitEvent): Promise<void> {
  if (!event.valid) {
    return;
  }

  const formData = event.values as CreateUserFormData;
  isSubmitting.value = true;

  try {
    const result = await authStore.createUser({
      username: formData.username.trim(),
      password: formData.password,
      is_admin: formData.isAdmin,
    });

    if (result.success) {
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: result.message,
        life: 3000,
      });
      // Reset form using the provided reset function
      event.reset();
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
