<template>
  <b-container fluid>
    <b-row>
      <b-col>
        <h3>API Token Management</h3>
        <p class="text-muted">
          Generate a static API token for authenticating external applications and scripts
          to the DigiScript REST API. This token does not expire and can be used with the
          <code>X-API-Key</code> header.
        </p>
      </b-col>
    </b-row>

    <b-row class="mt-3">
      <b-col>
        <b-card>
          <template v-if="!hasToken">
            <b-card-text>
              <b-alert
                variant="info"
                show
              >
                You do not have an API token. Generate one to access the DigiScript API
                from external applications.
              </b-alert>
            </b-card-text>
            <b-button
              variant="primary"
              :disabled="loading"
              @click="generateToken"
            >
              <b-spinner
                v-if="loading"
                small
              />
              Generate API Token
            </b-button>
          </template>

          <template v-else>
            <b-card-text>
              <b-alert
                variant="success"
                show
              >
                <strong>API Token Active</strong>
                <p class="mb-0 mt-2">
                  Your API token is active. Keep this token secure and do not share it publicly.
                </p>
              </b-alert>

              <div v-if="newlyGeneratedToken">
                <label for="api-token-display"><strong>Your New API Token:</strong></label>
                <b-input-group id="api-token-display">
                  <b-form-input
                    :value="newlyGeneratedToken"
                    readonly
                    type="text"
                  />
                  <b-input-group-append>
                    <b-button
                      variant="outline-secondary"
                      @click="copyToken"
                    >
                      <b-icon-clipboard />
                      Copy
                    </b-button>
                  </b-input-group-append>
                </b-input-group>
                <b-form-text class="text-warning">
                  <strong>IMPORTANT:</strong> This token will only be shown once.
                  Save it securely now - you will not be able to retrieve it again!
                </b-form-text>
              </div>
            </b-card-text>

            <b-card-text class="mt-3">
              <h5>Usage Example:</h5>
              <pre class="bg-light p-3 rounded"><code>curl -H "X-API-Key: YOUR_TOKEN_HERE" {{ apiBaseUrl }}/api/v1/auth</code></pre>
            </b-card-text>

            <b-button
              variant="warning"
              :disabled="loading"
              @click="showRegenerateConfirm = true"
            >
              <b-spinner
                v-if="loading"
                small
              />
              Regenerate Token
            </b-button>

            <b-button
              variant="danger"
              class="ml-2"
              :disabled="loading"
              @click="showRevokeConfirm = true"
            >
              <b-spinner
                v-if="loading"
                small
              />
              Revoke Token
            </b-button>
          </template>
        </b-card>
      </b-col>
    </b-row>

    <!-- Regenerate Confirmation Modal -->
    <b-modal
      v-model="showRegenerateConfirm"
      title="Regenerate API Token"
      ok-variant="warning"
      ok-title="Regenerate Token"
      cancel-title="Cancel"
      @ok="regenerateToken"
    >
      <p>
        Are you sure you want to regenerate your API token?
        Your old token will be immediately invalidated and any applications using it
        will no longer be able to access the API.
      </p>
      <p class="mb-0">
        <strong>You will need to update all applications with the new token.</strong>
      </p>
    </b-modal>

    <!-- Revoke Confirmation Modal -->
    <b-modal
      v-model="showRevokeConfirm"
      title="Revoke API Token"
      ok-variant="danger"
      ok-title="Revoke Token"
      cancel-title="Cancel"
      @ok="revokeToken"
    >
      <p>
        Are you sure you want to revoke your API token? Any applications using this token
        will no longer be able to access the API.
      </p>
      <p class="mb-0">
        <strong>This action cannot be undone.</strong>
      </p>
    </b-modal>
  </b-container>
</template>

<script>
import { mapActions } from 'vuex';
import { baseURL } from '@/js/utils';
import { BIconClipboard } from 'bootstrap-vue';

export default {
  name: 'ApiToken',
  components: {
    BIconClipboard,
  },
  data() {
    return {
      hasToken: false,
      newlyGeneratedToken: null,
      loading: false,
      showRegenerateConfirm: false,
      showRevokeConfirm: false,
    };
  },
  computed: {
    apiBaseUrl() {
      return baseURL();
    },
  },
  async mounted() {
    await this.checkTokenStatus();
  },
  methods: {
    ...mapActions(['GENERATE_API_TOKEN', 'REVOKE_API_TOKEN', 'GET_API_TOKEN']),
    async checkTokenStatus() {
      this.loading = true;
      try {
        const data = await this.GET_API_TOKEN();
        if (data) {
          this.hasToken = data.has_token;
        }
      } finally {
        this.loading = false;
      }
    },
    async generateToken() {
      this.loading = true;
      try {
        const data = await this.GENERATE_API_TOKEN();
        if (data) {
          this.hasToken = true;
          this.newlyGeneratedToken = data.api_token;
        }
      } finally {
        this.loading = false;
      }
    },
    async regenerateToken() {
      this.loading = true;
      this.showRegenerateConfirm = false;
      try {
        const data = await this.GENERATE_API_TOKEN();
        if (data) {
          this.hasToken = true;
          this.newlyGeneratedToken = data.api_token;
        }
      } finally {
        this.loading = false;
      }
    },
    async revokeToken() {
      this.loading = true;
      this.showRevokeConfirm = false;
      try {
        const success = await this.REVOKE_API_TOKEN();
        if (success) {
          this.hasToken = false;
          this.newlyGeneratedToken = null;
        }
      } finally {
        this.loading = false;
      }
    },
    async copyToken() {
      try {
        await navigator.clipboard.writeText(this.newlyGeneratedToken);
        this.$toast.success('Token copied to clipboard!');
      } catch (err) {
        this.$toast.error('Failed to copy token to clipboard');
      }
    },
  },
};
</script>

<style scoped>
pre {
  white-space: pre-wrap;
  word-wrap: break-word;
}

code {
  color: #e83e8c;
}
</style>
