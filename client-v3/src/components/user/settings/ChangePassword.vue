<template>
  <BCard title="Change Password">
    <BForm @submit.prevent="handlePasswordChange">
      <BFormGroup
        id="current-password-input-group"
        label="Current Password"
        label-for="current-password-input"
      >
        <BFormInput
          id="current-password-input"
          v-model="state.currentPassword"
          name="current-password-input"
          type="password"
          :state="validationState(v$.currentPassword)"
          aria-describedby="current-password-feedback"
          autocomplete="current-password"
        />
        <BFormInvalidFeedback id="current-password-feedback">
          This is a required field.
        </BFormInvalidFeedback>
      </BFormGroup>

      <BFormGroup
        id="new-password-input-group"
        label="New Password"
        label-for="new-password-input"
        description="6–72 characters"
      >
        <BFormInput
          id="new-password-input"
          v-model="state.newPassword"
          name="new-password-input"
          type="password"
          :state="validationState(v$.newPassword)"
          aria-describedby="new-password-feedback"
          autocomplete="new-password"
        />
        <BFormInvalidFeedback id="new-password-feedback">
          This is a required field and must be between 6 and 72 characters.
        </BFormInvalidFeedback>
      </BFormGroup>

      <BFormGroup
        id="confirm-password-input-group"
        label="Confirm New Password"
        label-for="confirm-password-input"
      >
        <BFormInput
          id="confirm-password-input"
          v-model="state.confirmPassword"
          name="confirm-password-input"
          type="password"
          :state="validationState(v$.confirmPassword)"
          aria-describedby="confirm-password-feedback"
          autocomplete="new-password"
        />
        <BFormInvalidFeedback id="confirm-password-feedback">
          Passwords do not match.
        </BFormInvalidFeedback>
      </BFormGroup>

      <BButton type="submit" variant="primary" :disabled="v$.$invalid || loading">
        <BSpinner v-if="loading" small class="me-1" />
        Change Password
      </BButton>
    </BForm>
  </BCard>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useVuelidate } from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import { useUserStore } from '@/stores/user';
import { useFormValidation } from '@/composables/useFormValidation';
import { usePasswordValidation } from '@/composables/usePasswordValidation';

const userStore = useUserStore();
const { validationState } = useFormValidation();
const { passwordRules, confirmPasswordRules } = usePasswordValidation();

const state = ref({ currentPassword: '', newPassword: '', confirmPassword: '' });
const loading = ref(false);

const rules = computed(() => ({
  currentPassword: { required },
  newPassword: passwordRules,
  confirmPassword: confirmPasswordRules(() => state.value.newPassword).value,
}));

const v$ = useVuelidate(rules, state);

async function handlePasswordChange(): Promise<void> {
  const valid = await v$.value.$validate();
  if (!valid) return;

  loading.value = true;
  try {
    const success = await userStore.changePassword(
      state.value.newPassword,
      state.value.currentPassword
    );
    if (success) {
      state.value = { currentPassword: '', newPassword: '', confirmPassword: '' };
      v$.value.$reset();
    }
  } finally {
    loading.value = false;
  }
}
</script>
