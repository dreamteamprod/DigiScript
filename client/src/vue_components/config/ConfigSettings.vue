<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col>
        <template v-if="loaded">
          <b-form @submit.stop.prevent="handleSubmit" @reset.stop.prevent="resetForm"
                  :key="`settings-${toggle}`">
            <div>
              <b-form-group v-for="(setting, key) in RAW_SETTINGS" :key="key"
                            :id="`${key}-input-group`" :label="key" :label-for="`${key}-input`"
                            :label-cols="true">
                <b-form-input v-if="setting.type !== 'bool'"
                              :id="`${key}-input`" :name="`${key}-input`"
                              :type="inputType(setting.type)"
                              v-model="$v.editSettings[key].$model"
                              :state="validateState(key)"
                              :readonly="!setting.can_edit"
                              :number="setting.type === 'int'" />
                <b-form-checkbox v-else
                                 :id="`${key}-input`" :name="`${key}-input`"
                                 v-model="$v.editSettings[key].$model"
                                 :disabled="!setting.can_edit" :switch="true" />
              </b-form-group>
              <b-button-group size="md" style="float: right">
                <b-button type="reset" variant="danger">Reset</b-button>
                <b-button type="submit" variant="primary">Submit</b-button>
              </b-button-group>
            </div>
          </b-form>
        </template>
        <div class="text-center center-spinner" v-else>
          <b-spinner style="width: 10rem; height: 10rem;" variant="info" />
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
  mounted() {
    Object.keys(this.RAW_SETTINGS).forEach(function (x) {
      this.editSettings[x] = this.RAW_SETTINGS[x].value;
    }, this);
    this.loaded = true;
  },
  watch: {
    RAW_SETTINGS() {
      this.resetForm();
    },
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
