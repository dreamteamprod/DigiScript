<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col>
        <template v-if="Object.keys(RAW_SETTINGS).length > 0">
          <b-form>
            <b-form-group v-for="(setting, key) in editSettings" :key="key"
                          :id="`${key}-input-group`" :label="key" :label-for="`${key}-input`"
                          :label-cols="true">
              <b-form-input v-if="setting.type !== 'bool'"
                            :id="`${key}-input`" :name="`${key}-input`"
                            v-model="editSettings[key].value"
                            :readonly="!setting.can_edit" />
              <b-form-checkbox v-else :id="`${key}-input`" :name="`${key}-input`"
                               v-model="editSettings[key].value"
                               :disabled="!setting.can_edit" />
            </b-form-group>
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

export default {
  name: 'ConfigSettings',
  data() {
    return {
      editSettings: null,
    };
  },
  mounted() {
    this.editSettings = JSON.parse(JSON.stringify(this.RAW_SETTINGS));
  },
  computed: {
    ...mapGetters(['RAW_SETTINGS']),
  },
};
</script>
