<template>
  <div class="force-password-change-container">
    <BContainer fluid class="h-100 d-flex align-items-center justify-content-center">
      <BRow class="w-100 justify-content-center">
        <BCol cols="12" md="6" lg="4">
          <BCard class="shadow-lg">
            <template #header>
              <h4 class="mb-0 text-center">Password Change Required</h4>
            </template>

            <BAlert :model-value="true" variant="warning" class="mb-4">
              Your password must be changed before you can continue.
            </BAlert>

            <BForm @submit.prevent="handlePasswordChange">
              <BFormGroup
                id="new-password-input-group"
                label="New Password"
                label-for="new-password-input"
                description="Minimum 6 characters"
              >
                <BFormInput
                  id="new-password-input"
                  v-model="v$.newPassword.$model"
                  name="new-password-input"
                  type="password"
                  :state="validationState(v$.newPassword)"
                  aria-describedby="new-password-feedback"
                  autocomplete="new-password"
                />
                <BFormInvalidFeedback id="new-password-feedback">
                  This is a required field and must be at least 6 characters.
                </BFormInvalidFeedback>
              </BFormGroup>

              <BFormGroup
                id="confirm-password-input-group"
                label="Confirm New Password"
                label-for="confirm-password-input"
              >
                <BFormInput
                  id="confirm-password-input"
                  v-model="v$.confirmPassword.$model"
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

              <div class="d-flex justify-content-between align-items-center mt-4">
                <BButton variant="outline-secondary" :disabled="loading" @click="handleLogout">
                  Logout
                </BButton>

                <BButton type="submit" variant="primary" :disabled="v$.$invalid || loading">
                  <BSpinner v-if="loading" small class="me-1" />
                  Change Password
                </BButton>
              </div>
            </BForm>
          </BCard>
        </BCol>
      </BRow>
    </BContainer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useVuelidate } from '@vuelidate/core';
import { required, minLength, sameAs } from '@vuelidate/validators';
import { useUserStore } from '@/stores/user';
import { useFormValidation } from '@/composables/useFormValidation';

const router = useRouter();
const userStore = useUserStore();
const { validationState } = useFormValidation();

const state = ref({ newPassword: '', confirmPassword: '' });
const loading = ref(false);

const rules = computed(() => ({
  newPassword: { required, minLength: minLength(6) },
  confirmPassword: { required, sameAsPassword: sameAs(state.value.newPassword) },
}));

const v$ = useVuelidate(rules, state);

async function handlePasswordChange(): Promise<void> {
  v$.value.$touch();
  if (v$.value.$invalid) return;
  loading.value = true;
  try {
    const success = await userStore.changePassword(state.value.newPassword);
    if (success) {
      router.push('/');
    }
  } finally {
    loading.value = false;
  }
}

async function handleLogout(): Promise<void> {
  await userStore.logout();
}
</script>

<style scoped>
.force-password-change-container {
  margin-top: 2rem;
}
</style>
