<template>
  <BRow class="line-editor-card" @keydown.esc="onEsc">
    <!-- No previous line to inherit an act/scene from (the very first line of an
         empty script/page), or the inherited values were themselves null (the
         previous line was never given one either) — the only cases this card
         still asks for them directly. Every other line already inherited a real
         act/scene from the line it was added next to (see ScriptEditor.vue's
         addNewLine/insertLineAt); structural moves happen via "Start New Scene
         Here" / "Move to Scene" instead. -->
    <BCol v-if="showActSceneSelectors" cols="2">
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

    <BCol :cols="showActSceneSelectors ? 10 : 12">
      <template v-if="lineType === LINE_TYPES.DIALOGUE || lineType === LINE_TYPES.STAGE_DIRECTION">
        <template v-if="state.line_parts.length > 0">
          <ScriptLinePart
            v-for="(part, index) in state.line_parts"
            :key="`line_${lineIndex}_part_${index}`"
            :model-value="state.line_parts[index]"
            :focus-input="index === 0"
            :characters="characters"
            :character-groups="characterGroups"
            :show-remove-button="state.line_parts.length > 1 && lineType === LINE_TYPES.DIALOGUE"
            :line-type="lineType"
            :line-parts="state.line_parts"
            :stage-direction-styles="
              lineType === LINE_TYPES.STAGE_DIRECTION ? stageDirectionStyles : []
            "
            :stage-direction-style-id="state.stage_direction_style_id"
            @update:model-value="onPartUpdate(index, $event)"
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
        <BCol v-if="lineType === LINE_TYPES.DIALOGUE && scriptMode === 1" cols="auto">
          <BButton
            variant="outline-light"
            :disabled="state.line_parts.length >= 4"
            @click="addLinePart"
          >
            Add Speaker <span class="text-muted">{{ state.line_parts.length }} of 4</span>
          </BButton>
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
      <BRow>
        <BCol class="keyboard-hint">
          <kbd>Enter</kbd> done, then add a line below &middot; <kbd>Tab</kbd> character to text
          &middot; <kbd>&uarr;</kbd> <kbd>&darr;</kbd> move between lines. Nothing is kept until you
          press Save.
        </BCol>
      </BRow>
    </BCol>
  </BRow>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
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
// Rows are keyed `page_N_line_index` (see ScriptEditor.vue's template), so an
// insert/delete/bulk-apply elsewhere on the page can reuse this exact component
// instance for a line at the same index but a different identity — modelValue
// then changes without this component re-mounting. lastEmittedSnapshot lets the
// watch below tell "the prop changed because of my own update:modelValue echoing
// back" (ignore, state is already current) apart from "something else changed
// it" (re-sync, so the next keystroke doesn't write stale content over it).
let lastEmittedSnapshot: string | null = null;

const scriptMode = computed(() => systemStore.currentShow?.script_mode ?? 0);
// `lineType` the parent passes is a stable prop (it's what decides which branch of
// ScriptEditor.vue's own v-if renders this component) but a brand-new, not-yet-saved
// line can still change its own type locally via LineTypeSegmented — `state.line_type`
// is the one actually read by this component's own template so that switch is live
// without the parent having to re-key/remount the editor.
const lineType = computed(() => state.value.line_type);

/** Whether to show the Act/Scene selectors — decided once for the line this
 * editor opened on (there's no previous line to inherit from, or the
 * inherited act/scene was itself null) and NOT recomputed from `state` as the
 * user edits it: picking an act then a scene would otherwise flip this false
 * mid-edit, unmounting the column the user is still picking in and jumping
 * the layout from 10 to 12 cols with no way back if the pick was wrong. */
function computeShowActSceneSelectors(line: ScriptLine): boolean {
  return !props.previousLine || line.act_id == null || line.scene_id == null;
}
const showActSceneSelectors = ref(computeShowActSceneSelectors(state.value));

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
  const snapshot = { ...state.value };
  lastEmittedSnapshot = JSON.stringify(snapshot);
  emit('update:modelValue', snapshot);
}

// See lastEmittedSnapshot's own comment above for why this distinguishes an echo
// of this component's own edit (ignored — state already reflects it) from an
// external change to the line now sitting at this reused row (re-synced, so a
// stale local copy doesn't silently overwrite whatever just changed it).
watch(
  () => props.modelValue,
  (newValue) => {
    const serialized = JSON.stringify(newValue);
    if (serialized === lastEmittedSnapshot) return;
    state.value = JSON.parse(JSON.stringify(newValue)); // NOSONAR
    lastEmittedSnapshot = serialized;
    v$.value.$reset();
    // A genuinely different line now sits at this row — re-decide for it, same
    // as a fresh mount would, rather than carrying over the previous line's
    // layout.
    showActSceneSelectors.value = computeShowActSceneSelectors(state.value);
  }
);

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
  state.value.line_parts = [];
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
/* Enter/Tab/Up/Down only do anything while focus is in the "What they say"
   field (where those keydown handlers are actually bound) — outside it the
   same keys just scroll the page or move focus normally, so the hint only
   makes sense to show then. :has() over a focus/blur-tracked ref: no JS
   needed, and it can't drift out of sync with where the handlers really are. */
.keyboard-hint {
  display: none;
  margin-top: 10px;
  font-size: 0.8125rem;
  color: var(--bs-secondary-color);
}
.line-editor-card:has(input[type='text']:focus) .keyboard-hint {
  display: block;
}
.keyboard-hint kbd {
  font-size: 0.75rem;
}
</style>
