<template>
  <div class="system-settings">
    <div class="container-fluid mx-0">
      <div class="row">
        <div class="col">
          <h1>System Settings</h1>

          <div v-if="!loaded" class="d-flex justify-content-center align-items-center" style="height: 400px;">
            <ProgressSpinner />
          </div>

          <form v-else @submit.prevent="handleSubmit" @reset.prevent="resetForm">
            <div v-for="(setting, key) in settingsStore.rawSettings" :key="key" class="mb-4">
              <div class="field">
                <label :for="`${key}-input`" class="font-bold">
                  <span v-if="setting.display_name">{{ setting.display_name }}</span>
                  <span v-else>{{ key }}</span>

                  <Button
                    v-if="setting.help_text"
                    :id="`${key}-help-btn`"
                    icon="pi pi-question-circle"
                    text
                    rounded
                    severity="secondary"
                    size="small"
                    style="margin-left: 0.5rem; padding: 0.25rem;"
                    @click="showHelpTooltip($event, setting.help_text)"
                  />
                </label>

                <!-- Text/Number Input -->
                <InputText
                  v-if="setting.type !== 'bool'"
                  :id="`${key}-input`"
                  :model-value="String(settingsStore.settingsForm[key] || '')"
                  :type="getInputType(setting.type)"
                  :readonly="!setting.can_edit"
                  :class="{ 'p-invalid': validationErrors[key] }"
                  class="w-full"
                  @update:model-value="(value: string | undefined) => settingsStore.settingsForm[key] = value || ''"
                />

                <!-- Boolean Switch -->
                <InputSwitch
                  v-else
                  :id="`${key}-input`"
                  :model-value="Boolean(settingsStore.settingsForm[key])"
                  :disabled="!setting.can_edit"
                  @update:model-value="(value: boolean) => settingsStore.settingsForm[key] = value"
                />

                <!-- Validation Error -->
                <small v-if="validationErrors[key]" class="p-error">{{ validationErrors[key] }}</small>
              </div>
            </div>

            <div class="d-flex justify-content-end gap-2 mt-4">
              <Button
                type="reset"
                label="Reset"
                severity="secondary"
                outlined
                :disabled="settingsStore.isSubmittingSettings"
              />
              <Button
                type="submit"
                label="Save Settings"
                :loading="settingsStore.isSubmittingSettings"
                :disabled="settingsStore.isSubmittingSettings"
              />
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Help Tooltip -->
    <OverlayPanel ref="helpOverlay">
      <div style="max-width: 300px;">
        {{ currentHelpText }}
      </div>
    </OverlayPanel>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { useSettingsStore } from '@/stores/settings';
import { useAuthStore } from '@/stores/auth';

// PrimeVue Components
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import InputSwitch from 'primevue/inputswitch';
import ProgressSpinner from 'primevue/progressspinner';
import OverlayPanel from 'primevue/overlaypanel';

const router = useRouter();
const toast = useToast();
const settingsStore = useSettingsStore();
const authStore = useAuthStore();

// State
const loaded = ref(false);
const validationErrors = ref<Record<string, string>>({});
const helpOverlay = ref();
const currentHelpText = ref('');

// Computed
const isAdmin = computed(() => authStore.currentUser?.is_admin === true);

// Methods
function getInputType(fieldType: string): string {
  const mapping: Record<string, string> = {
    int: 'number',
    str: 'text',
  };
  return mapping[fieldType] || 'text';
}

function validateForm(): boolean {
  validationErrors.value = {};
  let isValid = true;

  Object.keys(settingsStore.rawSettings).forEach((key) => {
    const setting = settingsStore.rawSettings[key];
    const value = settingsStore.settingsForm[key];

    if (setting.type === 'int') {
      if (value === null || value === undefined || value === '') {
        validationErrors.value[key] = 'This field is required.';
        isValid = false;
      } else if (Number.isNaN(Number(value))) {
        validationErrors.value[key] = 'This field must be a valid number.';
        isValid = false;
      }
    }
  });

  return isValid;
}

async function handleSubmit() {
  if (!validateForm()) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Please correct the errors in the form.',
      life: 3000,
    });
    return;
  }

  const result = await settingsStore.updateSystemSettings(settingsStore.settingsForm);

  if (result.success) {
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Settings saved successfully',
      life: 3000,
    });
  } else {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: result.error || 'Unable to save settings',
      life: 5000,
    });
  }
}

function resetForm() {
  settingsStore.resetSettingsForm();
  validationErrors.value = {};
}

function showHelpTooltip(event: Event, helpText: string) {
  currentHelpText.value = helpText;
  helpOverlay.value.toggle(event);
}

// Lifecycle
onMounted(async () => {
  // Check admin permissions
  if (!isAdmin.value) {
    toast.add({
      severity: 'error',
      summary: 'Access Denied',
      detail: 'Admin access required',
      life: 5000,
    });
    router.push('/');
    return;
  }

  try {
    await settingsStore.getRawSettings();
    loaded.value = true;
  } catch (error) {
    console.error('Error loading system settings:', error);
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Unable to load system settings',
      life: 5000,
    });
  }
});
</script>

<style scoped>
.system-settings {
  padding: 2rem;
}

.field {
  margin-bottom: 1.5rem;
}

.field label {
  display: block;
  margin-bottom: 0.5rem;
  color: var(--text-color);
}

.p-invalid {
  border-color: var(--red-500);
}

.p-error {
  color: var(--red-500);
  font-size: 0.875rem;
  margin-top: 0.25rem;
  display: block;
}
</style>
