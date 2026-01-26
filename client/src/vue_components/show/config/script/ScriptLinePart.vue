<template>
  <b-col>
    <b-form-row v-if="lineType === LINE_TYPES.DIALOGUE || lineType === LINE_TYPES.STAGE_DIRECTION">
      <b-col v-show="$v.state.character_group_id.$model == null">
        <b-form-group
          id="character-input-group"
          label-size="sm"
          label="Character"
          label-for="character-input"
        >
          <b-form-select
            id="character-input"
            v-model="$v.state.character_id.$model"
            name="character-input"
            :options="characterOptions"
            :state="validateState('character_id')"
            @change="stateChange"
          />
        </b-form-group>
      </b-col>
      <b-col v-show="$v.state.character_id.$model == null">
        <b-form-group
          id="character-group-input-group"
          label-size="sm"
          label="Character Group"
          label-for="character-group-input"
        >
          <b-form-select
            id="character-group-input"
            v-model="$v.state.character_group_id.$model"
            name="character-group-input"
            :options="characterGroupOptions"
            :state="validateState('character_group_id')"
            @change="stateChange"
          />
        </b-form-group>
      </b-col>
    </b-form-row>
    <b-form-row>
      <b-col style="display: inline-flex">
        <b-form-input
          ref="partInput"
          v-model="$v.state.line_text.$model"
          :state="validateState('line_text')"
          @change="stateChange"
          @keydown.enter.native="handleEnterPress"
        />
        <b-button
          v-if="showAddButton && lineType === LINE_TYPES.DIALOGUE"
          v-b-popover.hover.top="'Add line part'"
          :disabled="!enableAddButton"
          style="margin-left: 0.5em; float: right"
          @click="addLinePart"
        >
          <b-icon-plus-square-fill variant="success" />
        </b-button>
      </b-col>
    </b-form-row>
  </b-col>
</template>

<script>
import { required, requiredIf } from 'vuelidate/lib/validators';
import { LINE_TYPES } from '@/constants/lineTypes';

export default {
  name: 'ScriptLinePart',
  events: ['input', 'addLinePart', 'tryFinishLine'],
  props: {
    focusInput: {
      required: true,
      type: Boolean,
    },
    characters: {
      required: true,
      type: Array,
    },
    characterGroups: {
      required: true,
      type: Array,
    },
    showAddButton: {
      required: true,
      type: Boolean,
    },
    enableAddButton: {
      required: true,
      type: Boolean,
    },
    lineType: {
      required: true,
      type: Number,
    },
    lineParts: {
      required: true,
      type: Array,
    },
    value: {
      required: true,
      type: Object,
    },
  },
  validations: {
    state: {
      character_id: {
        // Required for DIALOGUE if no group selected; optional for STAGE_DIRECTION
        required: requiredIf(function isCharacterRequired() {
          return this.lineType === LINE_TYPES.DIALOGUE && this.state.character_group_id == null;
        }),
      },
      character_group_id: {
        // Required for DIALOGUE if no character selected; optional for STAGE_DIRECTION
        required: requiredIf(function isCharacterGroupRequired() {
          return this.lineType === LINE_TYPES.DIALOGUE && this.state.character_id == null;
        }),
      },
      line_text: {
        required: requiredIf(function isLineTextRequired() {
          return this.lineParts.length <= 1 || !this.lineParts.some((x) => x.line_text !== '');
        }),
      },
    },
  },
  data() {
    return {
      LINE_TYPES,
      state: this.value,
    };
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
      this.$refs.partInput.focus();
    },
    handleEnterPress() {
      this.$v.state.$touch();
      this.$emit('tryFinishLine');
    },
  },
};
</script>
