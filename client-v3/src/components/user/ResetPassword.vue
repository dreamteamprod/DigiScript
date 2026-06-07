<template>
  <div>
    <BAlert v-if="!temporaryPassword" variant="warning" :model-value="true">
      This will reset <strong>{{ username }}</strong
      >'s password to a randomly generated temporary password. The user will be forced to change it
      on their next login.
    </BAlert>

    <BAlert v-if="temporaryPassword" variant="success" :model-value="true">
      <h5 class="alert-heading">Password Reset Successfully</h5>
      <p class="mb-3">
        The temporary password for <strong>{{ username }}</strong> is:
      </p>
      <BFormGroup>
        <BInputGroup>
          <BFormInput
            :value="temporaryPassword"
            readonly
            :type="showPassword ? 'text' : 'password'"
          />
          <BButton variant="outline-secondary" @click="showPassword = !showPassword">
            {{ showPassword ? 'Hide' : 'Show' }}
          </BButton>
          <BButton variant="outline-secondary" @click="copyToClipboard">Copy</BButton>
        </BInputGroup>
      </BFormGroup>
      <p class="mb-0 small">
        Make sure to share this password with the user securely. They will need to change it on
        their next login.
      </p>
    </BAlert>

    <div class="d-flex justify-content-end mt-3">
      <BButton
        v-if="!temporaryPassword"
        variant="outline-secondary"
        class="me-2"
        @click="emit('cancel')"
      >
        Cancel
      </BButton>
      <BButton v-if="!temporaryPassword" variant="danger" :disabled="loading" @click="handleReset">
        <BSpinner v-if="loading" small class="me-1" />
        Reset Password
      </BButton>
      <BButton v-if="temporaryPassword" variant="primary" @click="emit('done')">Done</BButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { makeURL } from '@/js/utils';
import { toast } from '@/js/toast';

const props = defineProps<{
  userId: number;
  username: string;
}>();

const emit = defineEmits<{
  (e: 'cancel'): void;
  (e: 'password-reset'): void;
  (e: 'done'): void;
}>();

const loading = ref(false);
const temporaryPassword = ref<string | null>(null);
const showPassword = ref(false);

async function handleReset(): Promise<void> {
  loading.value = true;
  try {
    const response = await fetch(makeURL('/api/v1/auth/reset-password'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: props.userId }),
    });
    if (response.ok) {
      const data = await response.json();
      temporaryPassword.value = data.temporary_password;
      toast.success(`Password reset for ${props.username}`);
      emit('password-reset');
    } else {
      const error = await response.json();
      toast.error(error.message || 'Failed to reset password');
    }
  } catch {
    toast.error('An error occurred while resetting password');
  } finally {
    loading.value = false;
  }
}

async function copyToClipboard(): Promise<void> {
  try {
    await navigator.clipboard.writeText(temporaryPassword.value!);
    toast.success('Password copied to clipboard');
  } catch {
    toast.error('Failed to copy to clipboard');
  }
}
</script>
