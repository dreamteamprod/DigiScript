<template>
  <BRow
    class="collab-line-editor-row line-editor-card"
    :class="{ 'remote-editing-row': (remoteEditors?.length ?? 0) > 0 }"
    @keydown.esc="onEsc"
  >
    <RemoteEditorsBadge :names="remoteEditors ?? []" variant="editor" />

    <!-- See ScriptLineEditor.vue's own comment: this falls back to asking for
         act/scene directly whenever the line doesn't already have a real one of
         its own — no previous line to inherit from, or the inherited value was
         itself null. -->
    <BCol v-if="showActSceneSelectors" cols="2">
      <BRow>
        <BCol cols="6">
          <BFormGroup label-size="sm" label=" ">
            <BFormSelect
              data-testid="line-act-select"
              :model-value="line.act_id"
              :options="actOptions"
              :state="actState"
              @update:model-value="onActSceneChange($event as number | null, line.scene_id)"
            />
          </BFormGroup>
        </BCol>
        <BCol cols="6">
          <BFormGroup label-size="sm" label=" ">
            <BFormSelect
              data-testid="line-scene-select"
              :model-value="line.scene_id"
              :options="sceneOptions"
              :state="sceneState"
              @update:model-value="onActSceneChange(line.act_id, $event as number | null)"
            />
          </BFormGroup>
        </BCol>
      </BRow>
    </BCol>

    <BCol :cols="showActSceneSelectors ? 10 : 12">
      <template v-if="lineType === LINE_TYPES.DIALOGUE || lineType === LINE_TYPES.STAGE_DIRECTION">
        <template v-if="line.line_parts.length > 0">
          <CollabScriptLinePart
            v-for="(part, index) in line.line_parts"
            :key="part._uid"
            :page="page"
            :line-uid="line._uid"
            :part="part"
            :focus-input="index === 0"
            :characters="characters"
            :character-groups="characterGroups"
            :show-remove-button="line.line_parts.length > 1 && lineType === LINE_TYPES.DIALOGUE"
            :line-type="lineType"
            :line-parts="line.line_parts"
            :stage-direction-styles="
              lineType === LINE_TYPES.STAGE_DIRECTION ? stageDirectionStyles : []
            "
            :stage-direction-style-id="line.stage_direction_style_id"
            @remove-line-part="removeLinePart(part._uid)"
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
            :model-value="lineType"
            :disabled="!isUnsaved"
            @update:model-value="$emit('retypeLine', $event)"
          />
        </BCol>
        <BCol v-if="lineType === LINE_TYPES.DIALOGUE && scriptMode === 1" cols="auto">
          <BButton
            variant="outline-light"
            :disabled="line.line_parts.length >= 4"
            @click="addLinePart"
          >
            Add Speaker <span class="text-muted">{{ line.line_parts.length }} of 4</span>
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
          &middot; <kbd>&uarr;</kbd> <kbd>&darr;</kbd> move between lines. Changes are already
          shared — Done just closes the editor.
        </BCol>
      </BRow>
    </BCol>
  </BRow>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useVuelidate } from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import { LINE_TYPES } from '@/constants/lineTypes';
import { useSystemStore } from '@/stores/system';
import { useDraftWriter } from '@/composables/useDraftWriter';
import { computeValidActs, computeValidScenes } from '@/js/scriptLineActScene';
import { parseDbId } from '@/js/yjs/yjsSnapshot';
import { toast } from '@/js/toast';
import { fieldState } from '@/js/vuelidateFieldState';
import CollabScriptLinePart from './CollabScriptLinePart.vue';
import LineTypeSegmented from './LineTypeSegmented.vue';
import RemoteEditorsBadge from './RemoteEditorsBadge.vue';
import type { DraftScriptLine } from '@/js/yjs/draftAdapter';
import type { StageDirectionStyle } from '@/types/api/script';
import type { Act, Scene, Character, CharacterGroup } from '@/types/api/show';

/**
 * Draft-aware sibling of the classic `ScriptLineEditor.vue`. There is no local
 * `state`/`update:modelValue` round trip here: `line` is the live snapshot of the
 * draft's own `Y.Doc`, and every change (act/scene, add/remove part, style) writes
 * straight through `useDraftWriter` so another editor sees it immediately — matching
 * how `CollabScriptLinePart` already treats its own text and character fields.
 */

const props = defineProps<{
  page: number;
  line: DraftScriptLine;
  acts: Act[];
  scenes: Scene[];
  characters: Character[];
  characterGroups: CharacterGroup[];
  previousLine: DraftScriptLine | null;
  nextLine: DraftScriptLine | null;
  stageDirectionStyles: StageDirectionStyle[];
  /** Phase 4 Step C: usernames of other room members also editing this exact line. */
  remoteEditors?: string[];
}>();

const emit = defineEmits<{
  doneEditing: [];
  finishAndAddLine: [];
  deleteLine: [];
  navigateUp: [];
  navigateDown: [];
  /** LineTypeSegmented changed type on an as-yet-unsaved line — see `isUnsaved`
   * below and CollabScriptEditor.vue's `retypeLine()`, which is the only thing
   * allowed to actually act on this (it owns `editingLines`, which a type
   * change's delete-and-re-add must also update). */
  retypeLine: [newType: number];
}>();

const systemStore = useSystemStore();
const writer = useDraftWriter();

const scriptMode = computed(() => systemStore.currentShow?.script_mode ?? 0);
const lineType = computed(() => props.line.line_type);

/** See ScriptLineEditor.vue's own copy of this. */
const showActSceneSelectors = computed(
  () => !props.previousLine || props.line.act_id == null || props.line.scene_id == null
);
const isUnsaved = computed(() => parseDbId(props.line._id) == null);

function warnIfGone(ok: boolean): void {
  if (!ok) toast.warning('This line was changed or removed by another editor.');
}

const validActs = computed<Act[]>(() =>
  computeValidActs(props.acts, props.previousLine, props.nextLine)
);

const actOptions = computed(() => [
  { value: null, text: 'N/A', disabled: true },
  ...validActs.value.map((a) => ({ value: a.id, text: a.name })),
]);

const validScenes = computed<Scene[]>(() =>
  computeValidScenes(props.scenes, props.line.act_id, props.previousLine, props.nextLine)
);

const sceneOptions = computed(() => [
  { value: null, text: 'N/A', disabled: true },
  ...validScenes.value.map((s) => ({ value: s.id, text: s.name })),
]);

const rules = computed(() => ({
  act_id: { required },
  scene_id: { required },
}));

const v$ = useVuelidate(
  rules,
  computed(() => props.line)
);

const actState = computed(() => fieldState(v$.value.act_id));
const sceneState = computed(() => fieldState(v$.value.scene_id));

const lineValid = computed(
  () => !v$.value.$error && props.line.act_id != null && props.line.scene_id != null
);

function onActSceneChange(actId: number | null, sceneId: number | null): void {
  v$.value.$touch();
  warnIfGone(writer.setLineActScene(props.page, props.line._uid, actId, sceneId));
}

function removeLinePart(partUid: string): void {
  warnIfGone(writer.removePart(props.page, props.line._uid, partUid));
}

function addLinePart(): void {
  let characterId: number | null = null;
  let characterGroupId: number | null = null;
  if (lineType.value === LINE_TYPES.DIALOGUE && props.previousLine) {
    const newIdx = props.line.line_parts.length;
    const prevPart = props.previousLine.line_parts[newIdx];
    if (prevPart) {
      characterId = prevPart.character_id;
      characterGroupId = prevPart.character_id == null ? prevPart.character_group_id : null;
    }
  }
  warnIfGone(
    writer.addPart(props.page, props.line._uid, { characterId, characterGroupId }) !== null
  );
}

function onStageDirectionStyleChange(styleId: number | null): void {
  warnIfGone(writer.setLineField(props.page, props.line._uid, 'stage_direction_style_id', styleId));
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
    props.line.line_parts.length === 0 &&
    (lineType.value === LINE_TYPES.DIALOGUE || lineType.value === LINE_TYPES.STAGE_DIRECTION)
  ) {
    addLinePart();
  }
});
</script>

<style scoped>
/* Vue's scoped styles don't cross components — ScriptLineEditor.vue's own
   .line-editor-card rule (same class, used in this component's template) never
   reaches here, so this needs its own copy. See that file's comment for why
   --bs-dark, not --bs-tertiary-bg. */
.line-editor-card {
  padding: 12px;
  margin: 6px 0;
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
/* Someone else also has this line open while you're editing it — same visual
   language as ScriptLineViewer's read-only highlight, so the two read as one
   status rather than two different designs for the same thing. Takes over the
   card's own border/background for that state. */
.remote-editing-row {
  border: 1.5px solid rgba(var(--bs-warning-rgb), 0.65);
  border-radius: 4px;
  background-color: rgba(var(--bs-warning-rgb), 0.1);
  padding: 0.75rem 0.5rem;
  margin: 0.25rem 0;
}
</style>
