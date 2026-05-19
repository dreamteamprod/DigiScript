<template>
  <BRow>
    <BCol cols="2">
      <BRow>
        <BCol cols="6">
          <BFormGroup label-size="sm" label=" ">
            <BFormSelect
              v-model="state.act_id"
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
              :options="sceneOptions"
              :state="sceneState"
              @update:model-value="onStateChange"
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
          :line-type="lineType"
          :line-parts="state.line_parts"
          :stage-direction-styles="
            lineType === LINE_TYPES.STAGE_DIRECTION ? stageDirectionStyles : []
          "
          :stage-direction-style-id="state.stage_direction_style_id"
          @update:model-value="onPartUpdate(index, $event)"
          @add-line-part="addLinePart"
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
import { ref, computed, onMounted } from 'vue';
import { useVuelidate } from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import { LINE_TYPES } from '@/constants/lineTypes';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import ScriptLinePart from './ScriptLinePart.vue';
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
  lineType: number;
  stageDirectionStyles: StageDirectionStyle[];
  modelValue: ScriptLine;
}>();

const emit = defineEmits<{
  'update:modelValue': [line: ScriptLine];
  doneEditing: [];
  deleteLine: [];
}>();

const showStore = useShowStore();
const systemStore = useSystemStore();

const state = ref<ScriptLine>(JSON.parse(JSON.stringify(props.modelValue)));

const scriptMode = computed(() => systemStore.currentShow?.script_mode ?? 0);

const blankLinePart = (): ScriptLinePartType => ({
  id: null,
  line_id: state.value.id,
  part_index: state.value.line_parts.length,
  character_id: null,
  character_group_id: null,
  line_text: '',
});

const validActs = computed<Act[]>(() => {
  let startAct = props.acts.find((a) => a.previous_act == null) ?? null;
  if (props.previousLine) {
    startAct = props.acts.find((a) => a.id === props.previousLine!.act_id) ?? startAct;
  }
  const result: Act[] = [];
  let cur = startAct;
  while (cur) {
    result.push(cur);
    if (props.nextLine && props.nextLine.act_id === cur.id) break;
    cur = cur.next_act != null ? (props.acts.find((a) => a.id === cur!.next_act) ?? null) : null;
  }
  return result;
});

const actOptions = computed(() => [
  { value: null, text: 'N/A', disabled: true },
  ...validActs.value.map((a) => ({ value: a.id, text: a.name })),
]);

const validScenes = computed<Scene[]>(() => {
  if (state.value.act_id == null) return [];
  const actScenes = props.scenes.filter((s) => s.act === state.value.act_id);
  let startScene = actScenes.find((s) => s.previous_scene == null) ?? null;
  if (props.previousLine && props.previousLine.act_id === state.value.act_id) {
    startScene = actScenes.find((s) => s.id === props.previousLine!.scene_id) ?? startScene;
  }
  const result: Scene[] = [];
  let cur = startScene;
  while (cur) {
    result.push(cur);
    if (props.nextLine && props.nextLine.scene_id === cur.id) break;
    cur = cur.next_scene != null ? (actScenes.find((s) => s.id === cur!.next_scene) ?? null) : null;
  }
  return result;
});

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

function addLinePart(): void {
  const blank = blankLinePart();
  blank.part_index = state.value.line_parts.length;
  if (props.lineType === LINE_TYPES.DIALOGUE && props.previousLine) {
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

function onStageDirectionStyleChange(styleId: number | null): void {
  state.value.stage_direction_style_id = styleId;
  onStateChange();
}

function tryFinishLine(): void {
  v$.value.$touch();
  if (lineValid.value) emit('doneEditing');
}

onMounted(() => {
  v$.value.$touch();
  if (
    state.value.line_parts.length === 0 &&
    (props.lineType === LINE_TYPES.DIALOGUE || props.lineType === LINE_TYPES.STAGE_DIRECTION)
  ) {
    addLinePart();
  }
});
</script>
