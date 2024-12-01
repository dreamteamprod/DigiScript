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
                v-for="(setting, key) in RAW_SETTINGS"
                :id="`${key}-input-group`"
                :key="key"
                :label-for="`${key}-input`"
                :label-cols="true"
              >
                <template #label>
                  <p>
                    <template v-if="setting.display_name !== ''">
                      {{ setting.display_name }}
                    </template>
                    <template v-else>
                      {{ key }}
                    </template>
                    <template v-if="setting.help_text !== ''">
                      <b-icon-question-circle-fill :id="`${key}-help-icon`" />
                      <b-tooltip
                        :target="`${key}-help-icon`"
                        triggers="hover"
                      >
                        {{ setting.help_text }}
                      </b-tooltip>
                    </template>
                  </p>
                </template>
                <b-form-input
                  v-if="setting.type !== 'bool'"
                  :id="`${key}-input`"
                  v-model="$v.editSettings[key].$model"
                  :name="`${key}-input`"
                  :type="inputType(setting.type)"
                  :state="validateState(key)"
                  :readonly="!setting.can_edit"
                  :number="setting.type === 'int'"
                />
                <b-form-checkbox
                  v-else
                  :id="`${key}-input`"
                  v-model="$v.editSettings[key].$model"
                  :name="`${key}-input`"
                  :disabled="!setting.can_edit"
                  :switch="true"
                />
              </b-form-group>
              <b-button-group
                size="md"
                style="float: right"
              >
                <b-button
                  type="reset"
                  variant="danger"
                >
                  Reset
                </b-button>
                <b-button
                  type="submit"
                  variant="primary"
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
  name: 'ConfigSettings',
  data() {
    return {
      loaded: false,
      editSettings: {},
      toggle: 0,
    };
  },
  watch: {
    RAW_SETTINGS() {
      this.resetForm();
    },
  },
  mounted() {
    Object.keys(this.RAW_SETTINGS).forEach(function (x) {
      this.editSettings[x] = this.RAW_SETTINGS[x].value;
    }, this);
    this.loaded = true;
  },
  validations() {
    const editSettings = {};
    Object.keys(this.editSettings).forEach((x) => {
      if (this.RAW_SETTINGS[x].type === 'int') {
        editSettings[x] = {
          required,
          integer,
        };
      } else {
        editSettings[x] = {};
      }
    }, this);
    return { editSettings };
  },
  methods: {
    inputType(fieldType) {
      const mapping = {
        int: 'number',
        str: 'text',
      };
      if (!Object.keys(mapping).includes(fieldType)) {
        return 'text';
      }
      return mapping[fieldType];
    },
    validateState(name) {
      const { $dirty, $error } = this.$v.editSettings[name];
      return $dirty ? !$error : null;
    },
    async handleSubmit() {
      const response = await fetch(`${makeURL('/api/v1/settings')}`, {
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
      Object.keys(this.RAW_SETTINGS).forEach(function (x) {
        this.editSettings[x] = this.RAW_SETTINGS[x].value;
      }, this);
      this.loaded = true;
    },
  },
  computed: {
    ...mapGetters(['RAW_SETTINGS']),
  },
};
</script>
