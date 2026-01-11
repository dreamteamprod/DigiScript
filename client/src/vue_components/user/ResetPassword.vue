<template>
  <div>
    <b-alert
      v-if="!temporaryPassword"
      show
      variant="warning"
    >
      <b-icon
        icon="exclamation-triangle-fill"
        class="mr-2"
      />
      This will reset <strong>{{ username }}</strong>'s password to a randomly generated temporary password.
      The user will be forced to change it on their next login.
    </b-alert>

    <b-alert
      v-if="temporaryPassword"
      show
      variant="success"
    >
      <h5 class="alert-heading">
        <b-icon
          icon="check-circle-fill"
          class="mr-2"
        />
        Password Reset Successfully
      </h5>
      <p class="mb-3">
        The temporary password for <strong>{{ username }}</strong> is:
      </p>
      <b-form-group>
        <b-input-group>
          <b-form-input
            :value="temporaryPassword"
            readonly
            :type="showPassword ? 'text' : 'password'"
          />
          <b-input-group-append>
            <b-button
              variant="outline-secondary"
              @click="showPassword = !showPassword"
            >
              <b-icon :icon="showPassword ? 'eye-slash' : 'eye'" />
            </b-button>
            <b-button
              variant="outline-secondary"
              @click="copyToClipboard"
            >
              <b-icon icon="clipboard" />
              Copy
            </b-button>
          </b-input-group-append>
        </b-input-group>
      </b-form-group>
      <p class="mb-0 small">
        <b-icon
          icon="info-circle"
          class="mr-1"
        />
        Make sure to share this password with the user securely. They will need to change it on their next login.
      </p>
    </b-alert>

    <div class="d-flex justify-content-end mt-3">
      <b-button
        v-if="!temporaryPassword"
        variant="outline-secondary"
        class="mr-2"
        @click="$emit('cancel')"
      >
        Cancel
      </b-button>
      <b-button
        v-if="!temporaryPassword"
        variant="danger"
        :disabled="loading"
        @click="handleReset"
      >
        <b-spinner
          v-if="loading"
          small
          class="mr-1"
        />
        <b-icon
          v-else
          icon="arrow-clockwise"
          class="mr-1"
        />
        Reset Password
      </b-button>
      <b-button
        v-if="temporaryPassword"
        variant="primary"
        @click="$emit('done')"
      >
        Done
      </b-button>
    </div>
  </div>
</template>

<script>
import { makeURL } from '@/js/utils';

export default {
  name: 'ResetPassword',
  props: {
    userId: {
      type: Number,
      required: true,
    },
    username: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      loading: false,
      temporaryPassword: null,
      showPassword: false,
    };
  },
  methods: {
    async handleReset() {
      this.loading = true;

      try {
        const response = await fetch(makeURL('/api/v1/auth/reset-password'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_id: this.userId,
          }),
        });

        if (response.ok) {
          const data = await response.json();
          this.temporaryPassword = data.temporary_password;
          this.$toast.success(`Password reset for ${this.username}`);
          this.$emit('password-reset');
        } else {
          const error = await response.json();
          this.$toast.error(error.message || 'Failed to reset password');
        }
      } catch (error) {
        this.$toast.error('An error occurred while resetting password');
      } finally {
        this.loading = false;
      }
    },
    async copyToClipboard() {
      try {
        await navigator.clipboard.writeText(this.temporaryPassword);
        this.$toast.success('Password copied to clipboard');
      } catch (error) {
        this.$toast.error('Failed to copy to clipboard');
      }
    },
  },
};
</script>