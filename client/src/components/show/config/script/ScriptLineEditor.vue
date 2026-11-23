<template>
  <BRow class="line-editor-card" @keydown.esc="onEsc">
    <!-- No previous line to inherit an act/scene from (the very first line of an
         empty script/page) — the only case this card still asks for them directly.
         Every other line already inherited its act/scene from the line it was
         added next to (see ScriptEditor.vue's addNewLine/insertLineAt); structural
         moves happen via "Start New Scene Here" / "Move to Scene" instead. -->
    <BCol v-if="!previousLine" cols="2">
      <BRow>
        <BCol cols="6">
          <BFormGroup label-size="sm" label=" ">
            <BFormSelect
              v-model="state.act_id"
              data-testid="line-act-select"
              :options="actOptions"
              :state="actState"
              @update:model-value="onStateChange"
            />
          </BFormGroup>
        </BCol>
        <BCol cols="6">
          <BFormGroup label-size="sm" label=" ">
            <BFormSelect
              v-model="state.scene_id"
              data-testid="line-scene-select"
              :options="sceneOptions"
              :state="sceneState"
              @update:model-value="onStateChange"
            />
          </BFormGroup>
        </BCol>
      </BRow>
    </BCol>

    <BCol :cols="previousLine ? 12 : 10">
      <template v-if="lineType === LINE_TYPES.DIALOGUE || lineType === LINE_TYPES.STAGE_DIRECTION">
        <template v-if="state.line_parts.length > 0">
          <ScriptLinePart
            v-for="(part, index) in state.line_parts"
            :key="`line_${lineIndex}_part_${index}`"
            :model-value="state.line_parts[index]"
            :focus-input="index === 0"
            :characters="characters"
            :character-groups="characterGroups"
            :show-add-button="
              index === state.line_parts.length - 1 &&
              lineType === LINE_TYPES.DIALOGUE &&
              scriptMode === 1
            "
            :enable-add-button="state.line_parts.length < 4 && lineType === LINE_TYPES.DIALOGUE"
            :show-remove-button="state.line_parts.length > 1 && lineType === LINE_TYPES.DIALOGUE"
            :line-type="lineType"
            :line-parts="state.line_parts"
            :stage-direction-styles="
              lineType === LINE_TYPES.STAGE_DIRECTION ? stageDirectionStyles : []
            "
            :stage-direction-style-id="state.stage_direction_style_id"
            @update:model-value="onPartUpdate(index, $event)"
            @add-line-part="addLinePart"
            @remove-line-part="removeLinePart(index)"
            @try-finish-line="tryFinishLine"
            @navigate-up="$emit('navigateUp')"
            @navigate-down="$emit('navigateDown')"
            @stage-direction-style-change="onStageDirectionStyleChange"
          />
        </template>
        <BCol v-else cols="10" style="text-align: right">
          <BButton v-b-tooltip.hover.top="'Add line part'" @click="addLinePart"
            ><IMdiPlusBox
          /></BButton>
        </BCol>
      </template>
      <template v-else>
        <BCol>
          <BAlert variant="secondary" :model-value="true">
            <p class="text-muted small" style="margin: 0">
              <template v-if="lineType === LINE_TYPES.CUE_LINE"
                >Cue Lines have no editable content.</template
              >
              <template v-else-if="lineType === LINE_TYPES.SPACING"
                >Spacing Lines have no editable content.</template
              >
              <template v-else>This line type is not recognized.</template>
            </p>
          </BAlert>
        </BCol>
      </template>

      <BRow class="mt-2 align-items-center">
        <BCol cols="auto">
          <LineTypeSegmented
            :model-value="state.line_type"
            :disabled="state.id != null"
            @update:model-value="onLineTypeChange"
          />
        </BCol>
        <BCol class="text-end">
          <BButtonGroup>
            <BButton variant="danger" @click.stop.prevent="$emit('deleteLine')"
              >Delete Line</BButton
            >
            <BButton variant="success" :disabled="!lineValid" @click="$emit('doneEditing')">
              Done
            </BButton>
          </BButtonGroup>
        </BCol>
      </BRow>
    </BCol>
  </BRow>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useVuelidate } from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import { LINE_TYPES } from '@/constants/lineTypes';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import { computeValidActs, computeValidScenes } from '@/js/scriptLineActScene';
import ScriptLinePart from './ScriptLinePart.vue';
import LineTypeSegmented from './LineTypeSegmented.vue';
import type {
  ScriptLine,
  ScriptLinePart as ScriptLinePartType,
  StageDirectionStyle,
} from '@/types/api/script';
import type { Act, Scene, Character, CharacterGroup } from '@/types/api/show';

const props = defineProps<{
  lineIndex: number;
  currentEditPage: number;
  acts: Act[];
  scenes: Scene[];
  characters: Character[];
  characterGroups: CharacterGroup[];
  previousLine: ScriptLine | null;
  nextLine: ScriptLine | null;
  stageDirectionStyles: StageDirectionStyle[];
  modelValue: ScriptLine;
}>();

const emit = defineEmits<{
  'update:modelValue': [line: ScriptLine];
  doneEditing: [];
  /** Enter in the text field: close this line and open a new blank dialogue line
   * right below it (Design E's keyboard flow) — distinct from plain `doneEditing`
   * (Done button / Esc), which never adds anything. */
  finishAndAddLine: [];
  deleteLine: [];
  navigateUp: [];
  navigateDown: [];
}>();

const showStore = useShowStore();
const systemStore = useSystemStore();

// JSON round-trip instead of structuredClone — modelValue is a Vue reactive Proxy that structuredClone cannot handle
const state = ref<ScriptLine>(JSON.parse(JSON.stringify(props.modelValue))); // NOSONAR

const scriptMode = computed(() => systemStore.currentShow?.script_mode ?? 0);
// `lineType` the parent passes is a stable prop (it's what decides which branch of
// ScriptEditor.vue's own v-if renders this component) but a brand-new, not-yet-saved
// line can still change its own type locally via LineTypeSegmented — `state.line_type`
// is the one actually read by this component's own template so that switch is live
// without the parent having to re-key/remount the editor.
const lineType = computed(() => state.value.line_type);

const blankLinePart = (): ScriptLinePartType => ({
  id: null,
  line_id: state.value.id,
  part_index: state.value.line_parts.length,
  character_id: null,
  character_group_id: null,
  line_text: '',
});

const validActs = computed<Act[]>(() =>
  computeValidActs(props.acts, props.previousLine, props.nextLine)
);
const actOptions = computed(() => [
  { value: null, text: 'N/A', disabled: true },
  ...validActs.value.map((a) => ({ value: a.id, text: a.name })),
]);

const validScenes = computed<Scene[]>(() =>
  computeValidScenes(props.scenes, state.value.act_id, props.previousLine, props.nextLine)
);
const sceneOptions = computed(() => [
  { value: null, text: 'N/A', disabled: true },
  ...validScenes.value.map((s) => ({ value: s.id, text: s.name })),
]);

const rules = computed(() => ({
  act_id: { required },
  scene_id: { required },
}));

const v$ = useVuelidate(rules, state);

const actState = computed<boolean | null>(() => {
  const f = v$.value.act_id;
  return f.$dirty ? !f.$error : null;
});
const sceneState = computed<boolean | null>(() => {
  const f = v$.value.scene_id;
  return f.$dirty ? !f.$error : null;
});

const lineValid = computed(
  () => !v$.value.$error && state.value.act_id != null && state.value.scene_id != null
);

function onStateChange(): void {
  v$.value.$touch();
  emit('update:modelValue', { ...state.value });
}

function onPartUpdate(index: number, part: ScriptLinePartType): void {
  state.value.line_parts[index] = part;
  onStateChange();
}

function removeLinePart(index: number): void {
  state.value.line_parts = state.value.line_parts
    .filter((_, i) => i !== index)
    .map((part, i) => ({ ...part, part_index: i }));
  onStateChange();
}

function addLinePart(): void {
  const blank = blankLinePart();
  blank.part_index = state.value.line_parts.length;
  if (lineType.value === LINE_TYPES.DIALOGUE && props.previousLine) {
    const newIdx = state.value.line_parts.length;
    const prevPart = props.previousLine.line_parts[newIdx];
    if (prevPart) {
      if (prevPart.character_id != null) blank.character_id = prevPart.character_id;
      else if (prevPart.character_group_id != null)
        blank.character_group_id = prevPart.character_group_id;
    }
  }
  state.value.line_parts.push(blank);
  onStateChange();
}

/** Only ever called on a line that has never been saved (LineTypeSegmented is
 * disabled otherwise) — rebuilds `line_parts` to match what the new type needs,
 * the same shape `blankLine()`/`addNewLine()` give a freshly added line of that
 * type, rather than trying to carry over parts that may no longer make sense. */
function onLineTypeChange(newType: number): void {
  state.value.line_type = newType;
  state.value.line_parts =
    newType === LINE_TYPES.DIALOGUE || newType === LINE_TYPES.STAGE_DIRECTION ? [] : [];
  onStateChange();
  if (newType === LINE_TYPES.DIALOGUE || newType === LINE_TYPES.STAGE_DIRECTION) addLinePart();
}

function onStageDirectionStyleChange(styleId: number | null): void {
  state.value.stage_direction_style_id = styleId;
  onStateChange();
}

function tryFinishLine(): void {
  v$.value.$touch();
  if (lineValid.value) emit('finishAndAddLine');
}

function onEsc(): void {
  if (lineValid.value) emit('doneEditing');
  else v$.value.$touch();
}

onMounted(() => {
  v$.value.$touch();
  if (
    state.value.line_parts.length === 0 &&
    (lineType.value === LINE_TYPES.DIALOGUE || lineType.value === LINE_TYPES.STAGE_DIRECTION)
  ) {
    addLinePart();
  }
});
</script>

<style scoped>
.line-editor-card {
  padding: 12px;
  margin: 6px 0;
  /* Darkly doesn't redefine --bs-tertiary-bg (a Bootstrap 5.3 dark-mode variable
     it predates), so it resolves to Bootstrap's light default — --bs-dark is this
     theme's own dark surface colour instead, matching the design's card background. */
  background: var(--bs-dark);
  border: 1px solid var(--bs-success);
  border-radius: var(--bs-border-radius);
}
</style>
