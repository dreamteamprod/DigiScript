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
              <b-button-group size="md" style="float: right">
                <b-button type="reset" variant="danger" :disabled="!$v.$anyDirty"> Reset </b-button>
                <b-button type="submit" variant="primary" :disabled="!$v.$anyDirty || $v.$anyError">
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

<script>
import { mapGetters } from 'vuex';
import { required, integer } from 'vuelidate/lib/validators';
import log from 'loglevel';
import { makeURL } from '@/js/utils';
import { TEXT_ALIGNMENT } from '@/constants/textAlignment';

export default {
  name: 'UserSettingsConfig',
  data() {
    return {
      loaded: false,
      editSettings: {
        cue_position_right: false,
        script_text_alignment: TEXT_ALIGNMENT.CENTER,
        console_log_level: 'WARN',
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
      toggle: 0,
    };
  },
  computed: {
    ...mapGetters(['USER_SETTINGS']),
  },
  watch: {
    USER_SETTINGS() {
      this.resetForm();
    },
  },
  validations: {
    editSettings: {
      cue_position_right: {},
      script_text_alignment: {
        required,
        integer,
      },
      console_log_level: { required },
    },
  },
  mounted() {
    this.editSettings = JSON.parse(JSON.stringify(this.USER_SETTINGS));
    this.loaded = true;
  },
  methods: {
    validateState(name) {
      const { $dirty, $error } = this.$v.editSettings[name];
      return $dirty ? !$error : null;
    },
    async handleSubmit() {
      const response = await fetch(`${makeURL('/api/v1/user/settings')}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(this.editSettings),
      });
      if (!response.ok) {
        this.$toast.error('Unable to save settings');
        log.error('Unable to save settings');
      } else {
        this.$toast.success('Saved settings');
      }
    },
    resetForm() {
      this.loaded = false;
      this.toggle = !this.toggle;
      this.editSettings = JSON.parse(JSON.stringify(this.USER_SETTINGS));
      this.loaded = true;
    },
  },
};
</script>

<style scoped></style>
