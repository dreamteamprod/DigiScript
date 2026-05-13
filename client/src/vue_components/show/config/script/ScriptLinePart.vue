<template>
  <b-col>
    <b-form-row v-if="lineType === LINE_TYPES.DIALOGUE || lineType === LINE_TYPES.STAGE_DIRECTION">
      <template v-if="USER_SETTINGS && USER_SETTINGS.character_combined_dropdown">
        <b-col>
          <b-form-group
            id="character-combined-input-group"
            label-size="sm"
            label="Character / Character Group"
            label-for="character-combined-input"
          >
            <b-form-select
              id="character-combined-input"
              v-model="combinedValue"
              name="character-combined-input"
              :options="combinedOptions"
              :state="validateCombinedState()"
              @change="stateChange"
            />
          </b-form-group>
        </b-col>
      </template>
      <template v-else>
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
      </template>
      <b-col
        v-if="lineType === LINE_TYPES.STAGE_DIRECTION && stageDirectionStyles.length > 0"
        cols="3"
      >
        <b-form-group label-size="sm" label="Style" label-for="stage-direction-style-part">
          <b-form-select
            id="stage-direction-style-part"
            :value="stageDirectionStyleId"
            :options="stageDirectionStylesOptions"
            @change="$emit('stage-direction-style-change', $event)"
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

<script lang="ts">
import { defineComponent } from 'vue';
import { mapGetters } from 'vuex';
import { required, requiredIf } from 'vuelidate/lib/validators';
import { LINE_TYPES } from '@/constants/lineTypes';
import {
  buildMruCharacterOptions,
  buildMruCharacterGroupOptions,
  buildCombinedCharacterOptions,
  type CombinedSelectOption,
} from '@/js/mruSortUtils';

export default defineComponent({
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
    stageDirectionStyles: {
      required: false,
      type: Array,
      default: () => [],
    },
    stageDirectionStyleId: {
      required: false,
      type: Number,
      default: null,
    },
    value: {
      required: true,
      type: Object,
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
    };
  },
  computed: {
    ...mapGetters(['USER_SETTINGS', 'TMP_SCRIPT']),
    characterOptions(): any[] {
      const chars = this.characters as any[];
      if ((this.USER_SETTINGS as any)?.character_mru_sort) {
        const sorted = buildMruCharacterOptions(chars, this.TMP_SCRIPT);
        if (sorted) return sorted;
      }
      return [
        { value: null, text: 'N/A' },
        ...chars.map((c: any) => ({ value: c.id, text: c.name })),
      ];
    },
    characterGroupOptions(): any[] {
      const groups = this.characterGroups as any[];
      if ((this.USER_SETTINGS as any)?.character_mru_sort) {
        const sorted = buildMruCharacterGroupOptions(groups, this.TMP_SCRIPT);
        if (sorted) return sorted;
      }
      return [
        { value: null, text: 'N/A' },
        ...groups.map((g: any) => ({ value: g.id, text: g.name })),
      ];
    },
    stageDirectionStylesOptions(): { value: number | null; text: string }[] {
      return [
        { value: null, text: 'N/A' },
        ...(this.stageDirectionStyles as any[]).map((s: any) => ({
          value: s.id,
          text: s.description,
        })),
      ];
    },
    combinedOptions(): CombinedSelectOption[] {
      return buildCombinedCharacterOptions(
        this.characters as any[],
        this.characterGroups as any[],
        this.TMP_SCRIPT,
        !!(this.USER_SETTINGS as any)?.character_mru_sort
      );
    },
    combinedValue: {
      get(): string | null {
        const s = (this as any).state;
        if (s.character_id != null) return `c:${s.character_id}`;
        if (s.character_group_id != null) return `g:${s.character_group_id}`;
        return null;
      },
      set(val: string | null): void {
        const s = (this as any).state;
        if (val == null) {
          s.character_id = null;
          s.character_group_id = null;
        } else if (val.startsWith('c:')) {
          s.character_id = parseInt(val.slice(2), 10);
          s.character_group_id = null;
        } else if (val.startsWith('g:')) {
          s.character_id = null;
          s.character_group_id = parseInt(val.slice(2), 10);
        }
        (this as any).$v.state.$touch();
      },
    },
  },
  mounted(): void {
    (this as any).$v.state.$touch();
    if (this.focusInput) {
      // Use rAF + $nextTick so our focus fires after Bootstrap Vue's dropdown
      // focusToggler (which runs in its own rAF → $nextTick chain). Our rAF is
      // registered during the post-click microtask phase, so it fires after the
      // dropdown's earlier-registered rAF. Our $nextTick then runs last and wins.
      requestAnimationFrame(() => {
        this.$nextTick(() => {
          if (this.$refs.partInput) {
            (this.$refs.partInput as HTMLElement).focus();
          }
        });
      });
    }
  },
  methods: {
    validateState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.state[name];
      return $dirty ? !$error : null;
    },
    validateCombinedState(): boolean | null {
      const charV = (this as any).$v.state.character_id;
      const groupV = (this as any).$v.state.character_group_id;
      if (!charV.$dirty && !groupV.$dirty) return null;
      return !(charV.$error && groupV.$error);
    },
    addLinePart(): void {
      this.$emit('addLinePart');
    },
    stateChange(): void {
      (this as any).$v.state.$touch();
      this.$emit('input', (this as any).state);
      (this.$refs.partInput as HTMLElement).focus();
    },
    handleEnterPress(): void {
      (this as any).$v.state.$touch();
      this.$emit('tryFinishLine');
    },
  },
});
</script>
