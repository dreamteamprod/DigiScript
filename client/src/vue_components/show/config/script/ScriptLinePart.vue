<template>
  <b-col>
    <b-form-row v-if="!isStageDirection">
      <b-col v-show="$v.state.character_group_id.$model == null">
        <b-form-group
          id="character-input-group"
          label-size="sm"
          label="Character"
          label-for="character-input">
          <b-form-select
            id="character-input"
            name="character-input"
            :options="characterOptions"
            v-model="$v.state.character_id.$model"
            :state="validateState('character_id')"
            @change="stateChange">
          </b-form-select>
        </b-form-group>
      </b-col>
      <b-col v-show="$v.state.character_id.$model == null">
        <b-form-group
          id="character-group-input-group"
          label-size="sm"
          label="Character Group"
          label-for="character-group-input">
          <b-form-select
            id="character-group-input"
            name="character-group-input"
            :options="characterGroupOptions"
            v-model="$v.state.character_group_id.$model"
            :state="validateState('character_group_id')"
            @change="stateChange">
          </b-form-select>
        </b-form-group>
      </b-col>
    </b-form-row>
    <b-form-row>
      <b-col style="display: inline-flex">
        <b-form-input v-model="$v.state.line_text.$model" @change="stateChange"
                      :state="validateState('line_text')" ref="partInput"/>
        <b-button v-if="showAddButton && !isStageDirection"
                  :disabled="!enableAddButton"
                  style="margin-left: 0.5em; float: right"
                  v-b-popover.hover.top="'Add line part'" @click="addLinePart">
          <b-icon-plus-square-fill variant="success"/>
        </b-button>
      </b-col>
    </b-form-row>
  </b-col>
</template>

<script>
import { required, requiredIf } from 'vuelidate/lib/validators';

export default {
  name: 'ScriptLinePart',
  events: ['input', 'addLinePart'],
  props: {
    focusInput: {
      required: true,
      type: Boolean,
    },
    characters: {
      required: true,
    },
    characterGroups: {
      required: true,
    },
    showAddButton: {
      required: true,
      type: Boolean,
    },
    enableAddButton: {
      required: true,
      type: Boolean,
    },
    isStageDirection: {
      required: true,
      type: Boolean,
    },
    lineParts: {
      required: true,
      type: Array,
    },
    value: {
      required: true,
    },
  },
  validations: {
    state: {
      character_id: {
        required: requiredIf(function () {
          return this.isStageDirection === false && this.state.character_group_id == null;
        }),
      },
      character_group_id: {
        required: requiredIf(function () {
          return this.isStageDirection === false && this.state.character_id == null;
        }),
      },
      line_text: {
        required: requiredIf(function () {
          return this.lineParts.length <= 1 || !this.lineParts.some((x) => x.line_text !== '');
        }),
      },
    },
  },
  data() {
    return {
      state: this.value,
    };
  },
  mounted() {
    this.$v.state.$touch();
    if (this.focusInput) {
      this.$refs.partInput.focus();
    }
  },
  methods: {
    validateState(name) {
      const { $dirty, $error } = this.$v.state[name];
      return $dirty ? !$error : null;
    },
    addLinePart() {
      this.$emit('addLinePart');
    },
    stateChange() {
      this.$v.state.$touch();
      this.$emit('input', this.state);
    },
  },
  computed: {
    characterOptions() {
      return [
        { value: null, text: 'N/A' },
        ...this.characters.map((char) => ({ value: char.id, text: char.name })),
      ];
    },
    characterGroupOptions() {
      return [
        { value: null, text: 'N/A' },
        ...this.characterGroups.map((char) => ({ value: char.id, text: char.name })),
      ];
    },
  },
};
</script>
