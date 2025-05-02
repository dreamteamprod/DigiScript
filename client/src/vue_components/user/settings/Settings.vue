<template>
  <b-container
    class="mx-0"
    fluid
  >
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
              <b-button-group
                size="md"
                style="float: right"
              >
                <b-button
                  type="reset"
                  variant="danger"
                  :disabled="!$v.$anyDirty"
                >
                  Reset
                </b-button>
                <b-button
                  type="submit"
                  variant="primary"
                  :disabled="!$v.$anyDirty || $v.$anyError"
                >
                  Submit
                </b-button>
              </b-button-group>
            </div>
          </b-form>
        </template>
        <div
          v-else
          class="text-center center-spinner"
        >
          <b-spinner
            style="width: 10rem; height: 10rem;"
            variant="info"
          />
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

export default {
  name: 'UserSettingsConfig',
  data() {
    return {
      loaded: false,
      editSettings: {
        enable_script_auto_save: false,
        script_auto_save_interval: 10,
      },
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
      enable_script_auto_save: {},
      script_auto_save_interval: {
        required, integer,
      },
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

<style scoped>

</style>
