<template>
  <div class="system-settings">
    <div class="container-fluid mx-0">
      <div class="row">
        <div class="col">
          <h1>System Settings</h1>

          <div v-if="!loaded" class="ds-loading-spinner">
            <ProgressSpinner />
          </div>

          <Form
            v-else
            v-slot="$form"
            :initialValues="initialValues"
            :resolver="resolver || undefined"
            @submit="handleSubmit"
            class="system-settings-form"
          >
            <div class="ds-tab-content">
              <div
                v-for="(setting, key) in settingsStore.rawSettings"
                :key="key"
                class="ds-form-field"
              >
                <label :for="`${key}-input`" class="ds-form-field-label">
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
                    class="help-button"
                    @click="showHelpTooltip($event, setting.help_text)"
                  />
                </label>

                <!-- Text/Number Input -->
                <InputText
                  v-if="setting.type !== 'bool'"
                  :id="`${key}-input`"
                  :name="key"
                  :type="getInputType(setting.type)"
                  :readonly="!setting.can_edit"
                  :class="{ 'p-invalid': $form[key]?.invalid, 'error': $form[key]?.invalid }"
                  class="ds-form-field-input"
                  :disabled="isSubmitting"
                  fluid
                />

                <!-- Boolean Switch -->
                <ToggleSwitch
                  v-else
                  :id="`${key}-input`"
                  :name="key"
                  :disabled="!setting.can_edit || isSubmitting"
                />

                <!-- Validation Error -->
                <div v-if="$form[key]?.invalid" class="ds-form-field-error">
                  {{ $form[key].error?.message }}
                </div>
              </div>
            </div>

            <div class="ds-modal-footer">
              <Button
                type="button"
                label="Reset"
                severity="secondary"
                outlined
                :disabled="isSubmitting"
                @click="$form.reset()"
              />
              <Button
                type="submit"
                label="Save Settings"
                :loading="isSubmitting"
                :disabled="!$form.valid || isSubmitting"
              />
            </div>
          </Form>
        </div>
      </div>
    </div>

    <!-- Help Tooltip -->
    <OverlayPanel ref="helpOverlay">
      <div class="help-tooltip-content">
        {{ currentHelpText }}
      </div>
    </OverlayPanel>
  </div>
</template>

<script setup lang="ts">
import {
  ref, onMounted, computed, watch,
} from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { useSettingsStore } from '@/stores/settings';
import { useAuthStore } from '@/stores/auth';
import { zodResolver } from '@primevue/forms/resolvers/zod';

// PrimeVue Components
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import ToggleSwitch from 'primevue/toggleswitch';
import ProgressSpinner from 'primevue/progressspinner';
import OverlayPanel from 'primevue/overlaypanel';
import Form from '@primevue/forms/form';
import type { FormSubmitEvent } from '@primevue/forms/form';

// Validation schema
import {
  createSystemSettingsSchema,
  createSystemSettingsDefaults,
  getInputType,
  type SystemSettingsFormData,
} from '@/schemas/systemSettingsValidation';

const router = useRouter();
const toast = useToast();
const settingsStore = useSettingsStore();
const authStore = useAuthStore();

// State
const loaded = ref(false);
const helpOverlay = ref();
const currentHelpText = ref('');
const isSubmitting = ref(false);

// Dynamic form configuration based on settings
const initialValues = ref<SystemSettingsFormData>({});
const resolver = ref<ReturnType<typeof zodResolver> | undefined>(undefined);

// Computed
const isAdmin = computed(() => authStore.currentUser?.is_admin === true);

// Watch for changes in rawSettings to update form configuration
watch(
  () => settingsStore.rawSettings,
  (newRawSettings) => {
    if (Object.keys(newRawSettings).length > 0) {
      initialValues.value = createSystemSettingsDefaults(newRawSettings);
      resolver.value = zodResolver(createSystemSettingsSchema(newRawSettings));
    }
  },
  { immediate: true, deep: true },
);

// Methods
async function handleSubmit(event: FormSubmitEvent): Promise<void> {
  if (!event.valid) {
    return;
  }

  const formData = event.values as SystemSettingsFormData;
  isSubmitting.value = true;

  try {
    const result = await settingsStore.updateSystemSettings(formData);

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
  } catch (error) {
    console.error('Error saving settings:', error);
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'An unexpected error occurred while saving settings',
      life: 5000,
    });
  } finally {
    isSubmitting.value = false;
  }
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
  background-color: var(--ds-bg-primary);
  color: var(--ds-text-primary);
}

h1 {
  color: var(--ds-text-primary);
  text-align: center;
  margin-bottom: 2rem;
  font-weight: 600;
}

.help-button {
  margin-left: 0.5rem;
  padding: 0.25rem;
}

.help-tooltip-content {
  max-width: 300px;
  color: var(--ds-text-primary);
}

/* Custom styling for specific elements that need adjustment */
.ds-form-field-input {
  min-width: 300px;
  max-width: 600px;
}
</style>
