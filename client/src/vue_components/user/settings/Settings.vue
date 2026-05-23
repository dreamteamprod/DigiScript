<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col>
        <template v-if="loaded">
          <b-form
            :key="`settings-${toggle}`"
            @submit.stop.prevent="handleSubmit"
            @reset.stop.prevent="resetForm"
          >
            <div>
              <b-form-group
                :label-cols="true"
                label="Enable Script Autosave"
                label-for="enable-autosave-input"
              >
                <b-form-checkbox
                  id="enable-autosave-input"
                  v-model="$v.editSettings.enable_script_auto_save.$model"
                  name="enable-autosave-input"
                  :switch="true"
                />
              </b-form-group>
              <b-form-group
                :label-cols="true"
                label="Script Autosave Interval"
                label-for="autosave-interval-input"
              >
                <b-form-input
                  id="autosave-interval-input"
                  v-model="$v.editSettings.script_auto_save_interval.$model"
                  name="autosave-interval-input"
                  type="number"
                  :number="true"
                  :state="validateState('script_auto_save_interval')"
                />
              </b-form-group>
              <b-form-group
                :label-cols="true"
                label="Display cues on right side"
                label-for="cue-position-input"
              >
                <b-form-checkbox
                  id="cue-position-input"
                  v-model="$v.editSettings.cue_position_right.$model"
                  name="cue-position-input"
                  :switch="true"
                />
              </b-form-group>
              <b-form-group
                :label-cols="true"
                label="Script Text Alignment"
                label-for="text-alignment-input"
              >
                <b-form-select
                  id="text-alignment-input"
                  v-model="$v.editSettings.script_text_alignment.$model"
                  name="text-alignment-input"
                  :options="textAlignmentOptions"
                  :state="validateState('script_text_alignment')"
                />
              </b-form-group>
              <b-form-group :label-cols="true" label-for="console-log-level-input">
                <template #label>
                  <p>
                    Browser Console Log Level
                    <b-icon-question-circle-fill id="console-log-level-help-icon" />
                    <b-tooltip target="console-log-level-help-icon" triggers="hover">
                      Controls which log messages appear in your browser's developer console.
                    </b-tooltip>
                  </p>
                </template>
                <b-form-select
                  id="console-log-level-input"
                  v-model="$v.editSettings.console_log_level.$model"
                  name="console-log-level-input"
                  :options="consoleLogLevelOptions"
                  :state="validateState('console_log_level')"
                />
              </b-form-group>
              <b-form-group
                :label-cols="true"
                label="Sort characters by most recently used"
                label-for="character-mru-sort-input"
              >
                <b-form-checkbox
                  id="character-mru-sort-input"
                  v-model="$v.editSettings.character_mru_sort.$model"
                  name="character-mru-sort-input"
                  :switch="true"
                />
              </b-form-group>
              <b-form-group
                :label-cols="true"
                label="Use combined character/group dropdown"
                label-for="character-combined-dropdown-input"
              >
                <b-form-checkbox
                  id="character-combined-dropdown-input"
                  v-model="$v.editSettings.character_combined_dropdown.$model"
                  name="character-combined-dropdown-input"
                  :switch="true"
                />
              </b-form-group>
              <b-form-group
                :label-cols="true"
                label="Preferred UI Version"
                label-for="preferred-ui-input"
              >
                <b-form-select
                  id="preferred-ui-input"
                  v-model="$v.editSettings.preferred_ui.$model"
                  name="preferred-ui-input"
                  :options="preferredUiOptions"
                />
              </b-form-group>
              <b-button-group size="md" style="float: right">
                <b-button type="reset" variant="danger" :disabled="!formDirty"> Reset </b-button>
                <b-button type="submit" variant="primary" :disabled="!formDirty || $v.$anyError">
                  Submit
                </b-button>
              </b-button-group>
            </div>
          </b-form>
        </template>
        <div v-else class="text-center center-spinner">
          <b-spinner style="width: 10rem; height: 10rem" variant="info" />
        </div>
      </b-col>
    </b-row>
  </b-container>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapGetters } from 'vuex';
import { required, integer, minValue } from 'vuelidate/lib/validators';
import log from 'loglevel';
import { makeURL } from '@/js/utils';
import { notNull, notNullAndGreaterThanZero } from '@/js/customValidators';
import { TEXT_ALIGNMENT } from '@/constants/textAlignment';

export default defineComponent({
  name: 'UserSettingsConfig',
  data() {
    return {
      loaded: false,
      savedSettings: null as Record<string, unknown> | null,
      editSettings: {
        enable_script_auto_save: false,
        script_auto_save_interval: 10,
        cue_position_right: false,
        script_text_alignment: TEXT_ALIGNMENT.CENTER,
        console_log_level: 'WARN',
        character_mru_sort: false,
        character_combined_dropdown: false,
        preferred_ui: null as string | null,
      },
      textAlignmentOptions: [
        { value: TEXT_ALIGNMENT.LEFT, text: 'Left' },
        { value: TEXT_ALIGNMENT.CENTER, text: 'Center' },
        { value: TEXT_ALIGNMENT.RIGHT, text: 'Right' },
      ],
      consoleLogLevelOptions: [
        { value: 'TRACE', text: 'TRACE' },
        { value: 'DEBUG', text: 'DEBUG' },
        { value: 'INFO', text: 'INFO' },
        { value: 'WARN', text: 'WARN' },
        { value: 'ERROR', text: 'ERROR' },
        { value: 'SILENT', text: 'SILENT' },
      ],
      preferredUiOptions: [
        { value: null, text: 'Use system default' },
        { value: 'old', text: 'Classic UI' },
        { value: 'new', text: 'New UI' },
      ],
      toggle: 0,
    };
  },
  computed: {
    ...mapGetters(['USER_SETTINGS']),
    formDirty(): boolean {
      return JSON.stringify(this.editSettings) !== JSON.stringify(this.savedSettings);
    },
  },
  watch: {
    USER_SETTINGS(): void {
      this.resetForm();
    },
  },
  validations: {
    editSettings: {
      enable_script_auto_save: {},
      script_auto_save_interval: {
        required,
        integer,
        notNull,
        notNullAndGreaterThanZero,
        minValue: minValue(1),
      },
      cue_position_right: {},
      script_text_alignment: {
        required,
        integer,
      },
      console_log_level: { required },
      character_mru_sort: {},
      character_combined_dropdown: {},
      preferred_ui: { isValidUi: (val: unknown) => val === null || val === 'old' || val === 'new' },
    },
  },
  mounted(): void {
    const settings = JSON.parse(JSON.stringify((this as any).USER_SETTINGS));
    this.savedSettings = settings;
    this.editSettings = JSON.parse(JSON.stringify(settings));
    this.loaded = true;
  },
  methods: {
    validateState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.editSettings[name];
      return $dirty ? !$error : null;
    },
    async handleSubmit(): Promise<void> {
      const response = await fetch(`${makeURL('/api/v1/user/settings')}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(this.editSettings),
      });
      if (!response.ok) {
        (this as any).$toast.error('Unable to save settings');
        log.error('Unable to save settings');
      } else {
        (this as any).$toast.success('Saved settings');
        this.savedSettings = JSON.parse(JSON.stringify(this.editSettings));
      }
    },
    resetForm(): void {
      this.loaded = false;
      this.toggle = Number(!this.toggle);
      const settings = JSON.parse(JSON.stringify((this as any).USER_SETTINGS));
      this.savedSettings = settings;
      this.editSettings = JSON.parse(JSON.stringify(settings));
      this.loaded = true;
    },
  },
});
</script>

<style scoped></style>
