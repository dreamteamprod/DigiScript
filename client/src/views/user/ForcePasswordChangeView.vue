<template>
  <div class="force-password-change-container">
    <b-container fluid class="h-100 d-flex align-items-center justify-content-center">
      <b-row class="w-100 justify-content-center">
        <b-col cols="12" md="6" lg="4">
          <b-card class="shadow-lg">
            <template #header>
              <h4 class="mb-0 text-center">
                <b-icon icon="shield-lock" class="mr-2" />
                Password Change Required
              </h4>
            </template>

            <b-alert show variant="warning" class="mb-4">
              <b-icon icon="exclamation-triangle-fill" class="mr-2" />
              Your password must be changed before you can continue.
            </b-alert>

            <b-form @submit.prevent="handlePasswordChange">
              <b-form-group
                id="new-password-input-group"
                label="New Password"
                label-for="new-password-input"
                description="6–72 characters"
              >
                <b-form-input
                  id="new-password-input"
                  v-model="$v.state.newPassword.$model"
                  name="new-password-input"
                  type="password"
                  :state="validateState('newPassword')"
                  aria-describedby="new-password-feedback"
                  autocomplete="new-password"
                />
                <b-form-invalid-feedback id="new-password-feedback">
                  This is a required field and must be between 6 and 72 characters.
                </b-form-invalid-feedback>
              </b-form-group>

              <b-form-group
                id="confirm-password-input-group"
                label="Confirm New Password"
                label-for="confirm-password-input"
              >
                <b-form-input
                  id="confirm-password-input"
                  v-model="$v.state.confirmPassword.$model"
                  name="confirm-password-input"
                  type="password"
                  :state="validateState('confirmPassword')"
                  aria-describedby="confirm-password-feedback"
                  autocomplete="new-password"
                />
                <b-form-invalid-feedback id="confirm-password-feedback">
                  Passwords do not match.
                </b-form-invalid-feedback>
              </b-form-group>

              <div class="d-flex justify-content-between align-items-center mt-4">
                <b-button variant="outline-secondary" :disabled="loading" @click="handleLogout">
                  <b-icon icon="box-arrow-left" class="mr-1" />
                  Logout
                </b-button>

                <b-button type="submit" variant="primary" :disabled="isDisabled || loading">
                  <b-spinner v-if="loading" small class="mr-1" />
                  <b-icon v-else icon="check-circle" class="mr-1" />
                  Change Password
                </b-button>
              </div>
            </b-form>
          </b-card>
        </b-col>
      </b-row>
    </b-container>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { makeURL } from '@/js/utils';
import passwordValidationMixin from '@/mixins/passwordValidation';

export default defineComponent({
  name: 'ForcePasswordChangeView',
  mixins: [passwordValidationMixin],
  data() {
    return {
      state: {
        newPassword: '',
        confirmPassword: '',
      },
      loading: false,
    };
  },
  validations() {
    return {
      state: {
        newPassword: (this as any).getPasswordValidations(),
        confirmPassword: (this as any).getConfirmPasswordValidations('newPassword'),
      },
    };
  },
  computed: {
    isDisabled(): boolean {
      return Boolean((this as any).$v.state.$invalid);
    },
  },
  methods: {
    async handlePasswordChange(): Promise<void> {
      (this as any).$v.state.$touch();
      if ((this as any).$v.state.$anyError) {
        return;
      }

      this.loading = true;

      try {
        const response = await fetch(makeURL('/api/v1/auth/change-password'), {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ new_password: this.state.newPassword }),
        });

        if (response.ok) {
          const data = await response.json();
          if (data.access_token) {
            await this.$store.commit('SET_AUTH_TOKEN', data.access_token);
          }
          await this.$store.dispatch('GET_CURRENT_USER');
          this.$toast.success('Password changed successfully!');
          this.$router.push('/');
        } else {
          const error = await response.json();
          this.$toast.error(error.message || 'Failed to change password');
        }
      } catch {
        this.$toast.error('An error occurred while changing password');
      } finally {
        this.loading = false;
      }
    },
    async handleLogout(): Promise<void> {
      await this.$store.dispatch('USER_LOGOUT');
      this.$router.push('/login');
    },
  },
});
</script>

<style scoped>
.force-password-change-container {
  margin-top: 2rem;
}
</style>
