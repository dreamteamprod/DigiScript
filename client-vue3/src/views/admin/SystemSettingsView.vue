<template>
  <div class="system-settings">
    <div class="container-fluid mx-0">
      <div class="row">
        <div class="col">
          <h1>System Settings</h1>

          <div
            v-if="!loaded"
            class="d-flex justify-content-center align-items-center"
            style="height: 400px;"
          >
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
                  :name="key"
                  :type="getInputType(setting.type)"
                  :readonly="!setting.can_edit"
                  :class="{ 'p-invalid': $form[key]?.invalid }"
                  class="w-full"
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
                <Message
                  v-if="$form[key]?.invalid"
                  severity="error"
                  size="small"
                  variant="simple"
                >
                  {{ $form[key].error?.message }}
                </Message>
              </div>
            </div>

            <div class="d-flex justify-content-end gap-2 mt-4">
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
      <div style="max-width: 300px;">
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
import Message from 'primevue/message';

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
  background-color: #343a40;
  color: white;
  /* Remove min-height: 100vh as this is inside a tab panel */
}

.system-settings-form {
  padding: 0;
}

.field {
  margin-bottom: 1.5rem;
}

.field label {
  display: block;
  margin-bottom: 0.5rem;
  color: white;
  font-weight: bold;
}

/* Force dark theme on all input components */
h1 {
  color: white !important;
}

/* Fix input styling - make wider and proper dark theme */
:deep(.p-inputtext) {
  background-color: #495057 !important;
  color: white !important;
  border: 1px solid #6c757d !important;
  min-width: 300px !important;
  max-width: 600px !important;
}

:deep(.p-inputtext:focus) {
  background-color: #495057 !important;
  color: white !important;
  border-color: #17a2b8 !important;
  box-shadow: 0 0 0 0.2rem rgba(23, 162, 184, 0.25) !important;
}

:deep(.p-inputtext[readonly]) {
  background-color: #6c757d !important;
  color: #adb5bd !important;
}

/* Fix switch styling */
:deep(.p-inputswitch) {
  background-color: #495057 !important;
}

:deep(.p-inputswitch.p-inputswitch-checked) {
  background-color: #28a745 !important;
}

/* Fix button styling to match Vue 2 */
:deep(.p-button) {
  background-color: #007bff !important;
  border-color: #007bff !important;
  color: white !important;
}

:deep(.p-button:hover) {
  background-color: #0056b3 !important;
  border-color: #0056b3 !important;
}

:deep(.p-button.p-button-outlined) {
  background-color: transparent !important;
  color: #6c757d !important;
  border-color: #6c757d !important;
}

:deep(.p-button.p-button-outlined:hover) {
  background-color: #6c757d !important;
  color: white !important;
  border-color: #6c757d !important;
}

:deep(.p-button.p-button-secondary) {
  background-color: #6c757d !important;
  border-color: #6c757d !important;
}

:deep(.p-button.p-button-secondary:hover) {
  background-color: #5a6268 !important;
  border-color: #5a6268 !important;
}

/* Fix help button visibility - make visible by default */
:deep(.p-button.p-button-text) {
  color: #adb5bd !important;
}

:deep(.p-button.p-button-text:hover) {
  color: white !important;
  background-color: rgba(108, 117, 125, 0.1) !important;
}

/* Fix reset button visibility */
:deep(.p-button.p-button-secondary.p-button-outlined) {
  background-color: transparent !important;
  color: #adb5bd !important;
  border-color: #6c757d !important;
}

:deep(.p-button.p-button-secondary.p-button-outlined:hover) {
  background-color: #6c757d !important;
  color: white !important;
  border-color: #6c757d !important;
}

/* Fix progress spinner */
:deep(.p-progress-spinner-circle) {
  stroke: #17a2b8 !important;
}

/* Fix OverlayPanel */
:deep(.p-overlaypanel) {
  background-color: #495057 !important;
  color: white !important;
  border: 1px solid #6c757d !important;
}

:deep(.p-overlaypanel-content) {
  background-color: #495057 !important;
  color: white !important;
}

/* Error styling */
:deep(.p-invalid) {
  border-color: var(--red-500) !important;
}

</style>
