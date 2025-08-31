<template>
  <div class="user-settings-config">
    <div v-if="!loaded" class="flex justify-center items-center p-8">
      <ProgressSpinner style="width: 50px; height: 50px" stroke-width="4" />
    </div>

    <form v-else @submit.prevent="handleSubmit" @reset.prevent="resetForm" class="max-w-2xl">
      <div class="space-y-4">
        <div class="field">
          <label class="flex items-center space-x-2">
            <InputSwitch v-model="editSettings.enable_script_auto_save" />
            <span class="font-medium">Enable Script Autosave</span>
          </label>
        </div>

        <div class="field">
          <label for="autosave-interval" class="block text-sm font-medium text-gray-700 mb-2">
            Script Autosave Interval (seconds)
          </label>
          <InputNumber
            id="autosave-interval"
            v-model="editSettings.script_auto_save_interval"
            :class="{ 'p-invalid': intervalError }"
            :min="1"
            :step="1"
            show-buttons
            class="w-full"
          />
          <small v-if="intervalError" class="p-error">{{ intervalError }}</small>
        </div>

        <div class="field">
          <label class="flex items-center space-x-2">
            <InputSwitch v-model="editSettings.cue_position_right" />
            <span class="font-medium">Display cues on right side</span>
          </label>
        </div>

        <div class="flex justify-end space-x-2 pt-4">
          <Button
            type="reset"
            severity="danger"
            outlined
            :disabled="!hasChanges"
          >
            Reset
          </Button>

          <Button
            type="submit"
            :disabled="!hasChanges || !!intervalError || isSubmitting"
            :loading="isSubmitting"
          >
            Save Settings
          </Button>
        </div>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import {
  ref, computed, watch, onMounted,
} from 'vue';
import { useToast } from 'primevue/usetoast';
import InputSwitch from 'primevue/inputswitch';
import InputNumber from 'primevue/inputnumber';
import Button from 'primevue/button';
import ProgressSpinner from 'primevue/progressspinner';
import { useAuthStore, type UserSettings } from '../../stores/auth';

const authStore = useAuthStore();
const toast = useToast();

// Component state
const loaded = ref(false);
const isSubmitting = ref(false);

// Form data
const editSettings = ref<{
  enable_script_auto_save: boolean;
  script_auto_save_interval: number;
  cue_position_right: boolean;
}>({
  enable_script_auto_save: false,
  script_auto_save_interval: 10,
  cue_position_right: false,
});

// Track original settings for change detection
const originalSettings = ref<typeof editSettings.value>({
  enable_script_auto_save: false,
  script_auto_save_interval: 10,
  cue_position_right: false,
});

// Validation
const intervalError = computed(() => {
  const value = editSettings.value.script_auto_save_interval;
  if (value == null || value < 1) {
    return 'Autosave interval must be at least 1 second';
  }
  return null;
});

// Check if form has changes
const hasChanges = computed(() => (
  editSettings.value.enable_script_auto_save !== originalSettings.value.enable_script_auto_save
    || editSettings.value.script_auto_save_interval
       !== originalSettings.value.script_auto_save_interval
    || editSettings.value.cue_position_right !== originalSettings.value.cue_position_right
));

// Form handlers
function resetForm() {
  loaded.value = false;

  // Copy current settings from store
  const settings = authStore.userSettings;
  const newSettings = {
    enable_script_auto_save: settings.enable_script_auto_save as boolean || false,
    script_auto_save_interval: settings.script_auto_save_interval as number || 10,
    cue_position_right: settings.cue_position_right as boolean || false,
  };

  editSettings.value = { ...newSettings };
  originalSettings.value = { ...newSettings };

  loaded.value = true;
}

// Watch for settings changes from store
watch(() => authStore.userSettings, (newSettings) => {
  if (newSettings && Object.keys(newSettings).length > 0) {
    resetForm();
  }
});

async function handleSubmit() {
  if (intervalError.value || !hasChanges.value || isSubmitting.value) {
    return;
  }

  isSubmitting.value = true;

  try {
    const success = await authStore.updateUserSettings(editSettings.value as UserSettings);

    if (success) {
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'Settings saved successfully',
        life: 3000,
      });
      // Update original settings to reflect the saved state
      originalSettings.value = { ...editSettings.value };
    } else {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'Unable to save settings',
        life: 5000,
      });
    }
  } catch (error) {
    console.error('Error saving settings:', error);
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'An error occurred while saving settings',
      life: 5000,
    });
  } finally {
    isSubmitting.value = false;
  }
}

// Initialize component
onMounted(async () => {
  // Load user settings if not already loaded
  if (!authStore.userSettings || Object.keys(authStore.userSettings).length === 0) {
    await authStore.getUserSettings();
  }
  resetForm();
});
</script>

<style scoped>
.field {
  margin-bottom: 1.5rem;
}

:deep(.p-inputnumber) {
  width: 100%;
}

:deep(.p-inputnumber-input) {
  width: 100%;
}
</style>
