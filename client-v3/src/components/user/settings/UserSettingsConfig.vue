<template>
  <BContainer fluid class="mx-0">
    <BRow>
      <BCol>
        <template v-if="loaded">
          <BForm @submit.prevent="handleSubmit" @reset.prevent="resetForm">
            <BFormGroup
              label-cols="4"
              label="Enable Script Autosave"
              label-for="enable-autosave-input"
            >
              <BFormCheckbox
                id="enable-autosave-input"
                v-model="state.enable_script_auto_save"
                name="enable-autosave-input"
                switch
              />
            </BFormGroup>

            <BFormGroup
              label-cols="4"
              label="Script Autosave Interval"
              label-for="autosave-interval-input"
            >
              <BFormInput
                id="autosave-interval-input"
                v-model.number="state.script_auto_save_interval"
                name="autosave-interval-input"
                type="number"
                :state="validationState(v$.script_auto_save_interval)"
              />
              <BFormInvalidFeedback>
                This is a required field and must be greater than 0.
              </BFormInvalidFeedback>
            </BFormGroup>

            <BFormGroup
              label-cols="4"
              label="Display cues on right side"
              label-for="cue-position-input"
            >
              <BFormCheckbox
                id="cue-position-input"
                v-model="state.cue_position_right"
                name="cue-position-input"
                switch
              />
            </BFormGroup>

            <BFormGroup
              label-cols="4"
              label="Script Text Alignment"
              label-for="text-alignment-input"
            >
              <BFormSelect
                id="text-alignment-input"
                v-model.number="state.script_text_alignment"
                name="text-alignment-input"
                :options="textAlignmentOptions"
                :state="validationState(v$.script_text_alignment)"
              />
            </BFormGroup>

            <BFormGroup
              label-cols="4"
              label="Browser Console Log Level"
              label-for="console-log-level-input"
            >
              <BFormSelect
                id="console-log-level-input"
                v-model="state.console_log_level"
                name="console-log-level-input"
                :options="consoleLogLevelOptions"
                :state="validationState(v$.console_log_level)"
              />
            </BFormGroup>

            <BFormGroup
              label-cols="4"
              label="Sort characters by most recently used"
              label-for="character-mru-sort-input"
            >
              <BFormCheckbox
                id="character-mru-sort-input"
                v-model="state.character_mru_sort"
                name="character-mru-sort-input"
                switch
              />
            </BFormGroup>

            <BFormGroup
              label-cols="4"
              label="Use combined character/group dropdown"
              label-for="character-combined-dropdown-input"
            >
              <BFormCheckbox
                id="character-combined-dropdown-input"
                v-model="state.character_combined_dropdown"
                name="character-combined-dropdown-input"
                switch
              />
            </BFormGroup>

            <BFormGroup label-cols="4" label="Preferred UI Version" label-for="preferred-ui-input">
              <BFormSelect
                id="preferred-ui-input"
                v-model="state.preferred_ui"
                name="preferred-ui-input"
                :options="preferredUiOptions"
              />
            </BFormGroup>

            <BButtonGroup size="md" style="float: right">
              <BButton type="reset" variant="danger" :disabled="!v$.$anyDirty">Reset</BButton>
              <BButton type="submit" variant="primary" :disabled="!v$.$anyDirty || v$.$anyError">
                Submit
              </BButton>
            </BButtonGroup>
          </BForm>
        </template>
        <div v-else class="text-center">
          <BSpinner style="width: 10rem; height: 10rem" variant="info" />
        </div>
      </BCol>
    </BRow>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { useVuelidate } from '@vuelidate/core';
import { required, integer, minValue } from '@vuelidate/validators';
import log from 'loglevel';
import { makeURL } from '@/js/utils';
import { useUserStore } from '@/stores/user';
import { useFormValidation } from '@/composables/useFormValidation';
import { notNull, notNullAndGreaterThanZero } from '@/js/customValidators';
import { TEXT_ALIGNMENT } from '@/constants/textAlignment';
import type { UserSettings } from '@/types/api/user';
import { toast } from '@/js/toast';

const userStore = useUserStore();
const { validationState } = useFormValidation();

const loaded = ref(false);

const defaultState = (): UserSettings => ({
  enable_script_auto_save: false,
  script_auto_save_interval: 10,
  cue_position_right: false,
  script_text_alignment: TEXT_ALIGNMENT.CENTER,
  console_log_level: 'WARN',
  character_mru_sort: false,
  character_combined_dropdown: false,
  preferred_ui: null,
});

const state = ref<UserSettings>(defaultState());

const textAlignmentOptions = [
  { value: TEXT_ALIGNMENT.LEFT, text: 'Left' },
  { value: TEXT_ALIGNMENT.CENTER, text: 'Center' },
  { value: TEXT_ALIGNMENT.RIGHT, text: 'Right' },
];

const consoleLogLevelOptions = [
  { value: 'TRACE', text: 'TRACE' },
  { value: 'DEBUG', text: 'DEBUG' },
  { value: 'INFO', text: 'INFO' },
  { value: 'WARN', text: 'WARN' },
  { value: 'ERROR', text: 'ERROR' },
  { value: 'SILENT', text: 'SILENT' },
];

const preferredUiOptions = [
  { value: null, text: 'Use system default' },
  { value: 'old', text: 'Classic UI' },
  { value: 'new', text: 'New UI' },
];

const rules = computed(() => ({
  enable_script_auto_save: {},
  script_auto_save_interval: {
    required,
    integer,
    notNull,
    notNullAndGreaterThanZero,
    minValue: minValue(1),
  },
  cue_position_right: {},
  script_text_alignment: { required, integer },
  console_log_level: { required },
  character_mru_sort: {},
  character_combined_dropdown: {},
  preferred_ui: {},
}));

const v$ = useVuelidate(rules, state);

function resetForm(): void {
  loaded.value = false;
  const settings = userStore.userSettings as UserSettings;
  state.value = { ...defaultState(), ...settings };
  v$.value.$reset();
  loaded.value = true;
}

watch(() => userStore.userSettings, resetForm, { deep: true });

onMounted(() => {
  const settings = userStore.userSettings as UserSettings;
  state.value = { ...defaultState(), ...settings };
  loaded.value = true;
});

async function handleSubmit(): Promise<void> {
  const valid = await v$.value.$validate();
  if (!valid) return;

  const response = await fetch(makeURL('/api/v1/user/settings'), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(state.value),
  });

  if (response.ok) {
    toast.success('Saved settings');
    await userStore.getUserSettings();
    v$.value.$reset();
  } else {
    log.error('Unable to save settings');
    toast.error('Unable to save settings');
  }
}
</script>
