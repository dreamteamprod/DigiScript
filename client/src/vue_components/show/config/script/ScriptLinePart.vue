<template>
  <b-col>
    <b-form-row v-if="lineType === LINE_TYPES.DIALOGUE">
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
          @input="onTextInput"
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
import log from 'loglevel';
import { required, requiredIf } from 'vuelidate/lib/validators';
import { LINE_TYPES } from '@/constants/lineTypes';
import { nullToZero, zeroToNull } from '@/utils/yjs/yjsBridge';

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
    yPartMap: {
      type: Object,
      default: null,
    },
  },
  validations: {
    state: {
      character_id: {
        required: requiredIf(function isCharacterRequired() {
          return this.lineType === LINE_TYPES.DIALOGUE && this.state.character_group_id == null;
        }),
      },
      character_group_id: {
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
      ytextObserverCleanup: null,
      ymapObserverCleanup: null,
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
  watch: {
    yPartMap(newVal, oldVal) {
      if (oldVal) this.teardownYPartObservers();
      if (newVal) this.setupYPartObservers();
    },
  },
  created() {
    if (this.yPartMap) {
      this.setupYPartObservers();
    }
  },
  mounted() {
    this.$v.state.$touch();
    if (this.focusInput) {
      this.$refs.partInput.focus();
    }
  },
  beforeDestroy() {
    this.teardownYPartObservers();
  },
  methods: {
    validateState(name) {
      const { $dirty, $error } = this.$v.state[name];
      return $dirty ? !$error : null;
    },
    addLinePart() {
      this.$emit('addLinePart');
    },
    onTextInput() {
      log.debug(`ScriptLinePart: onTextInput yPartMap=${!!this.yPartMap}`);
      if (!this.yPartMap) return;
      const ytext = this.yPartMap.get('line_text');
      log.debug(`ScriptLinePart: onTextInput ytext=${!!ytext} doc=${!!(ytext && ytext.doc)}`);
      if (!ytext || !ytext.doc) return;
      ytext.doc.transact(() => {
        ytext.delete(0, ytext.length);
        ytext.insert(0, this.state.line_text || '');
      }, 'local-edit');
    },
    stateChange() {
      this.$v.state.$touch();
      if (this.yPartMap && this.yPartMap.doc) {
        this.yPartMap.doc.transact(() => {
          this.yPartMap.set('character_id', nullToZero(this.state.character_id));
          this.yPartMap.set('character_group_id', nullToZero(this.state.character_group_id));
        }, 'local-edit');
      }
      this.$emit('input', this.state);
      this.$refs.partInput.focus();
    },
    setupYPartObservers() {
      const ytext = this.yPartMap.get('line_text');
      if (ytext) {
        const textObserver = (event) => {
          if (event.transaction.origin === 'local-edit') return;
          this.state.line_text = ytext.toString();
        };
        ytext.observe(textObserver);
        this.ytextObserverCleanup = () => ytext.unobserve(textObserver);
      }

      const mapObserver = (event) => {
        if (event.transaction.origin === 'local-edit') return;
        for (const key of event.keysChanged) {
          if (key === 'character_id') {
            this.state.character_id = zeroToNull(this.yPartMap.get('character_id'));
          } else if (key === 'character_group_id') {
            this.state.character_group_id = zeroToNull(this.yPartMap.get('character_group_id'));
          }
        }
      };
      this.yPartMap.observe(mapObserver);
      this.ymapObserverCleanup = () => this.yPartMap.unobserve(mapObserver);
    },
    teardownYPartObservers() {
      if (this.ytextObserverCleanup) {
        this.ytextObserverCleanup();
        this.ytextObserverCleanup = null;
      }
      if (this.ymapObserverCleanup) {
        this.ymapObserverCleanup();
        this.ymapObserverCleanup = null;
      }
    },
    handleEnterPress() {
      this.$v.state.$touch();
      this.$emit('tryFinishLine');
    },
  },
};
</script>
