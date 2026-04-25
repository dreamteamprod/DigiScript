<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col>
        <template v-if="loaded">
          <b-form
            :key="`settings-${toggle}`"
            @submit.stop.prevent="handleSubmit"
            @reset.stop.prevent="resetForm(true)"
          >
            <div>
              <b-card
                v-for="(settings, category) in settingsByCategory"
                :key="`settings-${category}`"
                no-body
                class="section-card mt-2"
              >
                <b-card-header class="section-card-header" @click="expandCategory(category)">
                  <div class="d-flex justify-content-between align-items-center">
                    <span>
                      {{ category }}
                      <b-badge variant="success" class="ml-1">
                        {{ Object.keys(settings).length - dirtySettingsByCategory[category] }}
                      </b-badge>
                      <b-badge
                        v-if="dirtySettingsByCategory[category] > 0"
                        variant="warning"
                        class="ml-1"
                      >
                        {{ dirtySettingsByCategory[category] }}
                      </b-badge>
                    </span>
                    <b-icon-chevron-down v-if="categoryExpanded(category)" font-scale="0.8" />
                    <b-icon-chevron-up v-else font-scale="0.8" />
                  </div>
                </b-card-header>
                <b-collapse :visible="categoryExpanded(category)">
                  <b-card-body>
                    <b-form-group
                      v-for="(setting, key) in settings"
                      :id="`${key}-input-group`"
                      :key="key"
                      :label-for="`${key}-input`"
                      :label-cols="true"
                      style="margin-bottom: 0"
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
                            <b-tooltip :target="`${key}-help-icon`" triggers="hover">
                              {{ setting.help_text }}
                            </b-tooltip>
                          </template>
                        </p>
                      </template>
                      <b-form-select
                        v-if="setting.choice_options != null"
                        :id="`${key}-input`"
                        v-model="$v.editSettings[key].$model"
                        :name="`${key}-input`"
                        :options="getChoiceOptions(setting)"
                        :state="validateState(key)"
                        :disabled="!setting.can_edit"
                      >
                      </b-form-select>
                      <b-form-input
                        v-else-if="setting.type !== 'bool'"
                        :id="`${key}-input`"
                        v-model="$v.editSettings[key].$model"
                        :name="`${key}-input`"
                        :type="inputType(setting.type)"
                        :state="validateState(key)"
                        :readonly="!setting.can_edit"
                        :number="setting.type === 'int'"
                      />
                      <b-form-checkbox
                        v-else-if="setting.type === 'bool'"
                        :id="`${key}-input`"
                        v-model="$v.editSettings[key].$model"
                        :name="`${key}-input`"
                        :disabled="!setting.can_edit"
                        :switch="true"
                      />
                      <b-alert v-else show variant="danger">
                        Unknown setting type {{ setting.type }} for setting {{ key }}.
                      </b-alert>
                    </b-form-group>
                  </b-card-body>
                </b-collapse>
              </b-card>
              <b-button-group
                size="md"
                style="float: right; padding-top: 1rem; padding-bottom: 0.5rem"
              >
                <b-button type="reset" variant="danger"> Reset </b-button>
                <b-button type="submit" variant="primary"> Submit </b-button>
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
import { mapGetters, mapActions } from 'vuex';
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
      expandedCategories: ['General'],
    };
  },
  computed: {
    ...mapGetters(['RAW_SETTINGS', 'SETTINGS_CATEGORIES']),
    visibleSettings() {
      const visibleSettings = {};
      Object.keys(this.RAW_SETTINGS).forEach((x) => {
        if (!this.RAW_SETTINGS[x].hide_from_ui) {
          visibleSettings[x] = this.RAW_SETTINGS[x];
        }
      });
      return visibleSettings;
    },
    settingsByCategory() {
      const settingsByCategory = {};
      Object.keys(this.SETTINGS_CATEGORIES).forEach((category) => {
        settingsByCategory[category] = {};
        this.SETTINGS_CATEGORIES[category].forEach((setting) => {
          if (Object.keys(this.visibleSettings).includes(setting)) {
            settingsByCategory[category][setting] = this.visibleSettings[setting];
          }
        });
      });
      return settingsByCategory;
    },
    dirtySettingsByCategory() {
      const dirtySettingsByCategory = {};
      Object.keys(this.SETTINGS_CATEGORIES).forEach((category) => {
        dirtySettingsByCategory[category] = 0;
        this.SETTINGS_CATEGORIES[category].forEach((setting) => {
          if (Object.keys(this.visibleSettings).includes(setting)) {
            if (this.$v.editSettings[setting].$dirty) {
              dirtySettingsByCategory[category] += 1;
            }
          }
        });
      });
      return dirtySettingsByCategory;
    },
  },
  watch: {
    RAW_SETTINGS() {
      this.loaded = false;
      this.resetForm(false);
      this.resetEditSettings();
      this.loaded = true;
    },
  },
  async mounted() {
    await this.GET_SETTINGS_CATEGORIES();
    this.resetEditSettings();
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
    getChoiceOptions(setting) {
      const options = [];
      if (setting._nullable) {
        options.push({ value: null, text: 'N/A' });
      }
      setting.choice_options.forEach((option) => {
        options.push({ value: option, text: option });
      });
      return options;
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
    resetEditSettings() {
      Object.keys(this.visibleSettings).forEach(function setEditSettings(x) {
        this.editSettings[x] = this.visibleSettings[x].value;
      }, this);
    },
    resetForm(toggleLoaded) {
      if (toggleLoaded) {
        this.loaded = false;
      }
      this.toggle = !this.toggle;
      Object.keys(this.RAW_SETTINGS).forEach(function resetEditSettings(x) {
        this.editSettings[x] = this.RAW_SETTINGS[x].value;
      }, this);
      this.$v.editSettings.$reset();
      if (toggleLoaded) {
        this.loaded = true;
      }
    },
    expandCategory(category) {
      if (this.categoryExpanded(category)) {
        this.expandedCategories = this.expandedCategories.filter((x) => x !== category);
      } else {
        this.expandedCategories.push(category);
      }
    },
    categoryExpanded(category) {
      return this.expandedCategories.includes(category);
    },
    ...mapActions(['GET_SETTINGS_CATEGORIES']),
  },
};
</script>
