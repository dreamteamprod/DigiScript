<template>
  <Form
    v-slot="$form"
    :initialValues="initialValues"
    :resolver="resolver"
    @submit="handleSubmit"
    class="create-user-form"
  >
    <!-- Username Field -->
    <TextInputField
      name="username"
      label="Username"
      placeholder="Enter username"
      :required="true"
      :disabled="isSubmitting"
      :has-error="$form.username?.invalid"
      :error-message="$form.username?.error?.message"
      help-text="Username must be at least 3 characters long"
    />

    <!-- Password Field -->
    <PasswordInputField
      name="password"
      label="Password"
      placeholder="Enter password"
      :required="true"
      :disabled="isSubmitting"
      :has-error="$form.password?.invalid"
      :error-message="$form.password?.error?.message"
      :show-feedback="false"
      :toggle-mask="true"
      help-text="Password must be at least 6 characters long"
    />

    <!-- Confirm Password Field -->
    <PasswordInputField
      name="confirmPassword"
      label="Confirm Password"
      placeholder="Confirm password"
      :required="true"
      :disabled="isSubmitting"
      :has-error="$form.confirmPassword?.invalid"
      :error-message="$form.confirmPassword?.error?.message"
      :show-feedback="false"
      :toggle-mask="true"
    />

    <!-- Admin Checkbox -->
    <CheckboxField
      name="isAdmin"
      label="Administrator privileges"
      :disabled="isSubmitting"
      :has-error="$form.isAdmin?.invalid"
      :error-message="$form.isAdmin?.error?.message"
      help-text="Admins can create users and modify system settings"
    />

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
import { zodResolver } from '@primevue/forms/resolvers/zod';

// PrimeVue components
import Form from '@primevue/forms/form';
import type { FormSubmitEvent } from '@primevue/forms/form';
import Button from 'primevue/button';

// Custom form components
import { TextInputField, PasswordInputField, CheckboxField } from '@/components/form';

// Validation schema and composables
import { createUserSchema, createUserDefaults, type CreateUserFormData } from '@/schemas/userValidation';
import { useFormValidation } from '@/composables/useFormValidation';
import { useAuthStore } from '@/stores/auth';

// Props and emits
const emit = defineEmits<{
  'user-created': [];
  'cancel': [];
}>();

// Composables
const { handleFormSubmit, isSubmitting } = useFormValidation();
const authStore = useAuthStore();

// Form configuration
const initialValues = createUserDefaults;
const resolver = zodResolver(createUserSchema);

// Event handlers
function handleCancel(): void {
  emit('cancel');
}

async function handleSubmit(event: FormSubmitEvent): Promise<void> {
  const success = await handleFormSubmit<CreateUserFormData>(
    event,
    async (formData) => {
      const result = await authStore.createUser({
        username: formData.username.trim(),
        password: formData.password,
        is_admin: formData.isAdmin,
      });

      return result;
    },
    {
      successMessage: 'User created successfully',
      errorMessage: 'Unable to create user',
      resetOnSuccess: true,
    },
  );

  if (success) {
    emit('user-created');
  }
}
</script>

<style scoped>
.create-user-form {
  padding: 1rem;
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
