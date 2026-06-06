<template>
  <BContainer fluid>
    <BRow>
      <BCol>
        <h3>API Token Management</h3>
        <p class="text-muted">
          Generate a static API token for authenticating external applications and scripts to the
          DigiScript REST API. This token does not expire and can be used with the
          <code>X-API-Key</code> header.
        </p>
      </BCol>
    </BRow>

    <BRow class="mt-3">
      <BCol>
        <BCard>
          <template v-if="!hasToken">
            <BCardText>
              <BAlert :model-value="true" variant="info">
                You do not have an API token. Generate one to access the DigiScript API from
                external applications.
              </BAlert>
            </BCardText>
            <BButton variant="primary" :disabled="loading" @click="generateToken">
              <BSpinner v-if="loading" small />
              Generate API Token
            </BButton>
          </template>

          <template v-else>
            <BCardText>
              <BAlert :model-value="true" variant="success">
                <strong>API Token Active</strong>
                <p class="mb-0 mt-2">
                  Your API token is active. Keep this token secure and do not share it publicly.
                </p>
              </BAlert>

              <div v-if="newlyGeneratedToken">
                <label for="api-token-display"><strong>Your New API Token:</strong></label>
                <BInputGroup id="api-token-display">
                  <BFormInput :model-value="newlyGeneratedToken" readonly type="text" />
                  <template #append>
                    <BButton variant="outline-secondary" @click="copyToken">Copy</BButton>
                  </template>
                </BInputGroup>
                <BFormText class="text-warning">
                  <strong>IMPORTANT:</strong> This token will only be shown once. Save it securely
                  now - you will not be able to retrieve it again!
                </BFormText>
              </div>
            </BCardText>

            <BCardText class="mt-3">
              <h5>Usage Example:</h5>
              <pre
                class="bg-light p-3 rounded"
              ><code>curl -H "X-API-Key: YOUR_TOKEN_HERE" {{ apiBaseUrl }}/api/v1/auth</code></pre>
            </BCardText>

            <BButton variant="warning" :disabled="loading" @click="showRegenerateConfirm = true">
              <BSpinner v-if="loading" small />
              Regenerate Token
            </BButton>
            <BButton
              variant="danger"
              class="ms-2"
              :disabled="loading"
              @click="showRevokeConfirm = true"
            >
              <BSpinner v-if="loading" small />
              Revoke Token
            </BButton>
          </template>
        </BCard>
      </BCol>
    </BRow>

    <BModal
      v-model="showRegenerateConfirm"
      title="Regenerate API Token"
      ok-variant="warning"
      ok-title="Regenerate Token"
      cancel-title="Cancel"
      @ok="regenerateToken"
    >
      <p>
        Are you sure you want to regenerate your API token? Your old token will be immediately
        invalidated and any applications using it will no longer be able to access the API.
      </p>
      <p class="mb-0">
        <strong>You will need to update all applications with the new token.</strong>
      </p>
    </BModal>

    <BModal
      v-model="showRevokeConfirm"
      title="Revoke API Token"
      ok-variant="danger"
      ok-title="Revoke Token"
      cancel-title="Cancel"
      @ok="revokeToken"
    >
      <p>
        Are you sure you want to revoke your API token? Any applications using this token will no
        longer be able to access the API.
      </p>
      <p class="mb-0">
        <strong>This action cannot be undone.</strong>
      </p>
    </BModal>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useUserStore } from '@/stores/user';
import { baseURL } from '@/js/utils';
import { toast } from '@/js/toast';

const userStore = useUserStore();

const hasToken = ref(false);
const newlyGeneratedToken = ref<string | null>(null);
const loading = ref(false);
const showRegenerateConfirm = ref(false);
const showRevokeConfirm = ref(false);

const apiBaseUrl = computed(() => baseURL());
apiBaseUrl = apiBaseUrl.replace(/:\s*$/, "");

onMounted(async () => {
  await checkTokenStatus();
});

async function checkTokenStatus(): Promise<void> {
  loading.value = true;
  try {
    const data = await userStore.getApiToken();
    if (data) {
      hasToken.value = data.has_token as boolean;
    }
  } finally {
    loading.value = false;
  }
}

async function generateToken(): Promise<void> {
  loading.value = true;
  try {
    const data = await userStore.generateApiToken();
    if (data) {
      hasToken.value = true;
      newlyGeneratedToken.value = data.api_token as string;
    }
  } finally {
    loading.value = false;
  }
}

async function regenerateToken(): Promise<void> {
  loading.value = true;
  showRegenerateConfirm.value = false;
  try {
    const data = await userStore.generateApiToken();
    if (data) {
      hasToken.value = true;
      newlyGeneratedToken.value = data.api_token as string;
    }
  } finally {
    loading.value = false;
  }
}

async function revokeToken(): Promise<void> {
  loading.value = true;
  showRevokeConfirm.value = false;
  try {
    const success = await userStore.revokeApiToken();
    if (success) {
      hasToken.value = false;
      newlyGeneratedToken.value = null;
    }
  } finally {
    loading.value = false;
  }
}

async function copyToken(): Promise<void> {
  try {
    await navigator.clipboard.writeText(newlyGeneratedToken.value!);
    toast.success('Token copied to clipboard!');
  } catch {
    toast.error('Failed to copy token to clipboard');
  }
}
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
