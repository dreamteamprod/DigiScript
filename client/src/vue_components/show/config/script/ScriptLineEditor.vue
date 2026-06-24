<template>
  <b-form-row>
    <b-col cols="2">
      <b-form-row>
        <b-col cols="6">
          <b-form-group id="act-input-group" label-size="sm" label=" " label-for="act-input">
            <b-form-select
              id="act-input"
              v-model="$v.state.act_id.$model"
              name="act-input"
              :options="actOptions"
              :state="validateState('act_id')"
              @change="stateChange"
            />
          </b-form-group>
        </b-col>
        <b-col cols="6">
          <b-form-group id="scene-input-group" label-size="sm" label=" " label-for="scene-input">
            <b-form-select
              id="scene-input"
              v-model="$v.state.scene_id.$model"
              name="scene-input"
              :options="sceneOptions"
              :state="validateState('scene_id')"
              @change="stateChange"
            />
          </b-form-group>
        </b-col>
      </b-form-row>
      <b-form-row>
        <b-col style="align-content: center">
          <b-button-group>
            <b-button variant="success" :disabled="!lineValid" @click="doneEditing">
              Done
            </b-button>
            <b-button variant="danger" @click.stop.prevent="deleteLine"> Delete </b-button>
          </b-button-group>
        </b-col>
      </b-form-row>
    </b-col>
    <template v-if="lineType === LINE_TYPES.DIALOGUE || lineType === LINE_TYPES.STAGE_DIRECTION">
      <template v-if="state.line_parts.length > 0">
        <script-line-part
          v-for="(part, index) in state.line_parts"
          :key="`line_${lineIndex}_part_${index}`"
          v-model="$v.state.line_parts.$model[index]"
          :focus-input="index === 0"
          :characters="characters"
          :character-groups="characterGroups"
          :show-add-button="
            index === state.line_parts.length - 1 &&
            lineType === LINE_TYPES.DIALOGUE &&
            CURRENT_SHOW.script_mode === 1
          "
          :enable-add-button="state.line_parts.length < 4 && lineType === LINE_TYPES.DIALOGUE"
          :show-remove-button="state.line_parts.length > 1 && lineType === LINE_TYPES.DIALOGUE"
          :line-type="lineType"
          :line-parts="state.line_parts"
          :stage-direction-styles="
            lineType === LINE_TYPES.STAGE_DIRECTION ? stageDirectionStyles : []
          "
          :stage-direction-style-id="state.stage_direction_style_id"
          @input="stateChange"
          @addLinePart="addLinePart"
          @removeLinePart="removeLinePart(index)"
          @tryFinishLine="tryFinishLine"
          @stage-direction-style-change="onStageDirectionStyleChange"
        />
      </template>
      <b-col v-else cols="10" style="text-align: right">
        <b-button v-b-popover.hover.top="'Add line part'" @click="addLinePart">
          <b-icon-plus-square-fill variant="success" />
        </b-button>
      </b-col>
    </template>
    <template v-else>
      <b-col>
        <b-alert variant="secondary" show>
          <p class="text-muted small" style="margin: 0">
            <template v-if="lineType === LINE_TYPES.CUE_LINE">
              Cue Lines have no editable content.
            </template>
            <template v-else-if="lineType === LINE_TYPES.SPACING">
              Spacing Lines have no editable content.
            </template>
            <template v-else> This line type is not recognized. </template>
          </p>
        </b-alert>
      </b-col>
    </template>
  </b-form-row>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapGetters } from 'vuex';
import { required, requiredIf } from 'vuelidate/lib/validators';
import ScriptLinePart from '@/vue_components/show/config/script/ScriptLinePart.vue';
import { notNull, notNullAndGreaterThanZero } from '@/js/customValidators';
import { LINE_TYPES } from '@/constants/lineTypes';

export default defineComponent({
  name: 'ScriptLineEditor',
  components: { ScriptLinePart },
  events: ['input', 'doneEditing', 'deleteLine'],
  props: {
    lineIndex: {
      required: true,
      type: Number,
    },
    currentEditPage: {
      required: true,
      type: Number,
    },
    acts: {
      required: true,
      type: Array,
    },
    scenes: {
      required: true,
      type: Array,
    },
    characters: {
      required: true,
      type: Array,
    },
    characterGroups: {
      required: true,
      type: Array,
    },
    previousLineFn: {
      required: true,
      type: Function,
    },
    nextLineFn: {
      required: true,
      type: Function,
    },
    lineType: {
      required: true,
      type: Number,
    },
    stageDirectionStyles: {
      required: true,
      type: Array,
    },
    value: {
      required: true,
      type: Object,
    },
  },
  data() {
    return {
      LINE_TYPES,
      state: this.value,
      blankLinePartObj: {
        id: null,
        line_id: null,
        part_index: null,
        character_id: null,
        character_group_id: null,
        line_text: '',
      },
      previousLine: null as any,
      nextLine: null as any,
      recalculationTimeout: null as ReturnType<typeof setTimeout> | null,
      abortController: null as AbortController | null,
    };
  },
  validations: {
    state: {
      act_id: {
        required,
        notNull,
        notNullAndGreaterThanZero,
      },
      scene_id: {
        required,
        notNull,
        notNullAndGreaterThanZero,
      },
      line_parts: {
        required: requiredIf(function isLinePartsRequired() {
          return (
            this.lineType === LINE_TYPES.DIALOGUE || this.lineType === LINE_TYPES.STAGE_DIRECTION
          );
        }),
        $each: {
          character_id: {
            required: requiredIf(function isCharacterRequired(m) {
              return this.lineType === LINE_TYPES.DIALOGUE && m.character_group_id == null;
            }),
          },
          character_group_id: {
            required: requiredIf(function isCharacterGroupRequired(m) {
              return this.lineType === LINE_TYPES.DIALOGUE && m.character_id == null;
            }),
          },
          line_text: {
            required: requiredIf(function isLineTextRequired() {
              return (
                (this.lineType === LINE_TYPES.DIALOGUE ||
                  this.lineType === LINE_TYPES.STAGE_DIRECTION) &&
                (this.state.line_parts.length <= 1 ||
                  !this.state.line_parts.some((x) => x.line_text !== ''))
              );
            }),
          },
        },
      },
      stage_direction_style_id: {},
    },
  },
  computed: {
    ...mapGetters(['SCENE_BY_ID', 'ACT_BY_ID', 'TMP_SCRIPT', 'ALL_DELETED_LINES', 'CURRENT_SHOW']),
    currentPageScript(): any[] {
      return (
        ((this as any).TMP_SCRIPT as Record<string, any[]>)[this.currentEditPage.toString()] || []
      );
    },
    currentPageDeletedLines(): any[] {
      return (
        ((this as any).ALL_DELETED_LINES as Record<string, any[]>)[
          this.currentEditPage.toString()
        ] || []
      );
    },
    nextActs(): any[] {
      const acts = this.acts as any[];
      let startAct = acts.find((act: any) => act.previous_act == null);
      if (this.previousLine != null) {
        startAct = acts.find((act: any) => act.id === this.previousLine.act_id);
      }
      const validActs: any[] = [];
      let nextAct = startAct;
      while (nextAct != null) {
        validActs.push(JSON.parse(JSON.stringify(nextAct)));
        if (this.nextLine != null && this.nextLine.act_id === nextAct.id) {
          break;
        }
        nextAct = (this as any).ACT_BY_ID(nextAct.next_act);
      }
      return validActs;
    },
    actOptions(): any[] {
      return [
        { value: null, text: 'N/A', disabled: true },
        ...(this as any).nextActs.map((act: any) => ({ value: act.id, text: act.name })),
      ];
    },
    nextScenes(): any[] {
      const state = (this as any).state;
      if (state.act_id == null) {
        return [];
      }
      const scenes = (this.scenes as any[]).filter((scene: any) => scene.act === state.act_id);
      let startScene = scenes.find((scene: any) => scene.previous_scene == null);
      if (this.previousLine != null && this.previousLine.act_id === state.act_id) {
        startScene = scenes.find((scene: any) => scene.id === this.previousLine.scene_id);
      }
      const validScenes: any[] = [];
      let nextScene = startScene;
      while (nextScene != null) {
        validScenes.push(JSON.parse(JSON.stringify(nextScene)));
        if (this.nextLine != null && this.nextLine.scene_id === nextScene.id) {
          break;
        }
        nextScene = (this as any).SCENE_BY_ID(nextScene.next_scene);
      }
      return validScenes;
    },
    sceneOptions(): any[] {
      return [
        { value: null, text: 'N/A', disabled: true },
        ...(this as any).nextScenes.map((scene: any) => ({ value: scene.id, text: scene.name })),
      ];
    },
    lineValid(): boolean {
      return !(this as any).$v.state.$anyError;
    },
    stageDirectionStylesOptions(): any[] {
      return [
        { value: null, text: 'N/A' },
        ...(this.stageDirectionStyles as any[]).map((style: any) => ({
          value: style.id,
          text: style.description,
        })),
      ];
    },
  },
  watch: {
    currentPageScript: {
      handler(): void {
        this.scheduleRecalculation();
      },
      deep: true,
    },
    currentPageDeletedLines: {
      handler(): void {
        this.scheduleRecalculation();
      },
      deep: true,
    },
    lineIndex(): void {
      this.scheduleRecalculation();
    },
    ALL_DELETED_LINES: {
      handler(): void {
        this.scheduleRecalculation();
      },
      deep: true,
    },
  },
  async created(): Promise<void> {
    this.previousLine = await (this.previousLineFn as Function)(this.lineIndex);
    this.nextLine = await (this.nextLineFn as Function)(this.lineIndex);
    const state = (this as any).state;
    if (
      state.line_parts.length === 0 &&
      (this.lineType === LINE_TYPES.DIALOGUE || this.lineType === LINE_TYPES.STAGE_DIRECTION)
    ) {
      this.addLinePart();
    }
  },
  mounted(): void {
    (this as any).$v.state.$touch();
  },
  beforeDestroy(): void {
    if (this.recalculationTimeout) {
      clearTimeout(this.recalculationTimeout);
    }
    if (this.abortController) {
      this.abortController.abort();
    }
  },
  methods: {
    scheduleRecalculation(): void {
      if (this.recalculationTimeout) {
        clearTimeout(this.recalculationTimeout);
      }

      this.recalculationTimeout = setTimeout(() => {
        this.recalculatePreviousNextLines();
      }, 100);
    },
    async recalculatePreviousNextLines(): Promise<void> {
      if (this.abortController) {
        this.abortController.abort();
      }

      this.abortController = new AbortController();
      const { signal } = this.abortController;

      try {
        const prevLine = await (this.previousLineFn as Function)(this.lineIndex);
        if (signal.aborted) return;
        this.previousLine = prevLine;

        const nxtLine = await (this.nextLineFn as Function)(this.lineIndex);
        if (signal.aborted) return;
        this.nextLine = nxtLine;
      } catch (error: any) {
        if (error.name !== 'AbortError') {
          console.error('Error recalculating previous/next lines:', error);
        }
      }
    },
    validateState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.state[name];
      return $dirty ? !$error : null;
    },
    doneEditing(): void {
      this.$emit('doneEditing');
    },
    stateChange(): void {
      (this as any).$v.state.$touch();
      this.$emit('input', (this as any).state);
    },
    removeLinePart(index: number): void {
      const state = (this as any).state;
      state.line_parts = state.line_parts
        .filter((_: any, i: number) => i !== index)
        .map((part: any, i: number) => ({ ...part, part_index: i }));
      this.stateChange();
    },
    addLinePart(): void {
      const state = (this as any).state;
      const blankLine = JSON.parse(JSON.stringify(this.blankLinePartObj));
      blankLine.line_id = state.id;
      blankLine.part_index = state.line_parts.length;
      state.line_parts.push(blankLine);
      if (this.lineType === LINE_TYPES.DIALOGUE && this.previousLine != null) {
        const newPartIndex = state.line_parts.length - 1;
        const newPart = state.line_parts[newPartIndex];
        if (this.previousLine.line_parts.length >= newPartIndex + 1) {
          const previousPart = this.previousLine.line_parts[newPartIndex];
          if (previousPart.character_id != null) {
            newPart.character_id = previousPart.character_id;
          } else if (previousPart.character_group_id != null) {
            newPart.character_group_id = previousPart.character_group_id;
          }
        }
      }
      this.stateChange();
    },
    onStageDirectionStyleChange(styleId: number | null): void {
      (this as any).state.stage_direction_style_id = styleId;
      this.stateChange();
    },
    deleteLine(): void {
      this.$emit('deleteLine');
    },
    tryFinishLine(): void {
      (this as any).$v.state.$touch();
      if (this.lineValid) {
        this.doneEditing();
      }
    },
  },
});
</script>

<style scoped></style>
