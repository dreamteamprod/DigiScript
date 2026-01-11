<template>
  <b-card title="Change Password">
    <b-form @submit.prevent="handlePasswordChange">
      <b-form-group
        id="current-password-input-group"
        label="Current Password"
        label-for="current-password-input"
      >
        <b-form-input
          id="current-password-input"
          v-model="$v.state.currentPassword.$model"
          name="current-password-input"
          type="password"
          :state="validateState('currentPassword')"
          aria-describedby="current-password-feedback"
          autocomplete="current-password"
        />
        <b-form-invalid-feedback id="current-password-feedback">
          This is a required field.
        </b-form-invalid-feedback>
      </b-form-group>

      <b-form-group
        id="new-password-input-group"
        label="New Password"
        label-for="new-password-input"
        description="Minimum 6 characters"
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
          This is a required field and must be at least 6 characters.
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

      <b-button type="submit" variant="primary" :disabled="isDisabled || loading">
        <b-spinner v-if="loading" small class="mr-1" />
        <b-icon v-else icon="key" class="mr-1" />
        Change Password
      </b-button>
    </b-form>
  </b-card>
</template>

<script>
import { required } from 'vuelidate/lib/validators';
import { makeURL } from '@/js/utils';
import passwordValidationMixin from '@/mixins/passwordValidation';

export default {
  name: 'ChangePassword',
  mixins: [passwordValidationMixin],
  data() {
    return {
      state: {
        currentPassword: '',
        newPassword: '',
        confirmPassword: '',
      },
      loading: false,
    };
  },
  validations() {
    return {
      state: {
        currentPassword: {
          required,
        },
        newPassword: this.getPasswordValidations(),
        confirmPassword: this.getConfirmPasswordValidations('newPassword'),
      },
    };
  },
  computed: {
    isDisabled() {
      return Boolean(this.$v.state.$invalid);
    },
  },
  methods: {
    async handlePasswordChange() {
      this.$v.state.$touch();
      if (this.$v.state.$anyError) {
        return;
      }

      this.loading = true;

      try {
        const response = await fetch(makeURL('/api/v1/auth/change-password'), {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            old_password: this.state.currentPassword,
            new_password: this.state.newPassword,
          }),
        });

        if (response.ok) {
          const data = await response.json();

          // Update auth token with new token
          if (data.access_token) {
            await this.$store.commit('SET_AUTH_TOKEN', data.access_token);
          }

          // Refresh current user
          await this.$store.dispatch('GET_CURRENT_USER');

          this.$toast.success('Password changed successfully!');

          // Reset form
          this.state.currentPassword = '';
          this.state.newPassword = '';
          this.state.confirmPassword = '';
          this.$v.$reset();
        } else {
          const error = await response.json();
          this.$toast.error(error.message || 'Failed to change password');
        }
      } catch (error) {
        this.$toast.error('An error occurred while changing password');
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>
