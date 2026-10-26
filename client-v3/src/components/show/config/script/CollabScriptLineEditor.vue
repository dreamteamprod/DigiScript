<template>
  <BRow>
    <BCol cols="2">
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
      <BRow>
        <BCol style="align-content: center">
          <BButtonGroup>
            <BButton variant="success" :disabled="!lineValid" @click="$emit('doneEditing')">
              Done
            </BButton>
            <BButton variant="danger" @click.stop.prevent="$emit('deleteLine')">Delete</BButton>
          </BButtonGroup>
        </BCol>
      </BRow>
    </BCol>

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
          :show-add-button="
            index === line.line_parts.length - 1 &&
            lineType === LINE_TYPES.DIALOGUE &&
            scriptMode === 1
          "
          :enable-add-button="line.line_parts.length < 4 && lineType === LINE_TYPES.DIALOGUE"
          :show-remove-button="line.line_parts.length > 1 && lineType === LINE_TYPES.DIALOGUE"
          :line-type="lineType"
          :line-parts="line.line_parts"
          :stage-direction-styles="
            lineType === LINE_TYPES.STAGE_DIRECTION ? stageDirectionStyles : []
          "
          :stage-direction-style-id="line.stage_direction_style_id"
          @add-line-part="addLinePart"
          @remove-line-part="removeLinePart(part._uid)"
          @try-finish-line="tryFinishLine"
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
import { toast } from '@/js/toast';
import { fieldState } from '@/js/vuelidateFieldState';
import CollabScriptLinePart from './CollabScriptLinePart.vue';
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
  lineType: number;
  acts: Act[];
  scenes: Scene[];
  characters: Character[];
  characterGroups: CharacterGroup[];
  previousLine: DraftScriptLine | null;
  nextLine: DraftScriptLine | null;
  stageDirectionStyles: StageDirectionStyle[];
}>();

const emit = defineEmits<{
  doneEditing: [];
  deleteLine: [];
}>();

const systemStore = useSystemStore();
const writer = useDraftWriter();

const scriptMode = computed(() => systemStore.currentShow?.script_mode ?? 0);

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
  if (props.lineType === LINE_TYPES.DIALOGUE && props.previousLine) {
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
  if (lineValid.value) emit('doneEditing');
}

onMounted(() => {
  v$.value.$touch();
  if (
    props.line.line_parts.length === 0 &&
    (props.lineType === LINE_TYPES.DIALOGUE || props.lineType === LINE_TYPES.STAGE_DIRECTION)
  ) {
    addLinePart();
  }
});
</script>
