<template>
  <BModal
    ref="modal"
    title="Bulk Edit Act/Scene"
    size="md"
    ok-title="Apply"
    :ok-disabled="!canApply"
    @ok.prevent="handleOk"
    @hidden="reset"
  >
    <p class="text-muted small mb-3">
      Applies the selected act and scene to all lines from the chosen start line to end line
      (inclusive).
    </p>
    <BFormGroup label="Act" label-for="bulk-act-input">
      <BFormSelect
        id="bulk-act-input"
        v-model="selectedActId"
        :options="actOptions"
        @update:model-value="selectedSceneId = null"
      />
    </BFormGroup>
    <BFormGroup label="Scene" label-for="bulk-scene-input">
      <BFormSelect
        id="bulk-scene-input"
        v-model="selectedSceneId"
        :options="sceneOptions"
        :disabled="selectedActId == null"
      />
    </BFormGroup>
  </BModal>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import type { ScriptLine } from '@/types/api/script';
import type { Act, Scene } from '@/types/api/show';

const props = defineProps<{
  previousLineOfStart: ScriptLine | null;
  nextLineOfEnd: ScriptLine | null;
  acts: Act[];
  scenes: Scene[];
}>();

const emit = defineEmits<{
  apply: [payload: { actId: number; sceneId: number }];
}>();

const modal = ref<InstanceType<typeof BModal>>();
const selectedActId = ref<number | null>(null);
const selectedSceneId = ref<number | null>(null);

const validActs = computed<Act[]>(() => {
  let startAct = props.acts.find((a) => a.previous_act == null) ?? null;
  if (props.previousLineOfStart?.act_id != null) {
    startAct = props.acts.find((a) => a.id === props.previousLineOfStart!.act_id) ?? startAct;
  }
  const result: Act[] = [];
  let cur = startAct;
  while (cur) {
    result.push(cur);
    if (props.nextLineOfEnd && props.nextLineOfEnd.act_id === cur.id) break;
    cur = cur.next_act != null ? (props.acts.find((a) => a.id === cur!.next_act) ?? null) : null;
  }
  return result;
});

const validScenes = computed<Scene[]>(() => {
  if (selectedActId.value == null) return [];
  const actScenes = props.scenes.filter((s) => s.act === selectedActId.value);
  let startScene = actScenes.find((s) => s.previous_scene == null) ?? null;
  if (
    props.previousLineOfStart?.act_id === selectedActId.value &&
    props.previousLineOfStart?.scene_id != null
  ) {
    startScene = actScenes.find((s) => s.id === props.previousLineOfStart!.scene_id) ?? startScene;
  }
  const result: Scene[] = [];
  let cur = startScene;
  while (cur) {
    result.push(cur);
    if (props.nextLineOfEnd && props.nextLineOfEnd.scene_id === cur.id) break;
    cur = cur.next_scene != null ? (actScenes.find((s) => s.id === cur!.next_scene) ?? null) : null;
  }
  return result;
});

const actOptions = computed(() => [
  { value: null, text: 'Select an act', disabled: true },
  ...validActs.value.map((a) => ({ value: a.id, text: a.name })),
]);

const sceneOptions = computed(() => [
  { value: null, text: 'Select a scene', disabled: true },
  ...validScenes.value.map((s) => ({ value: s.id, text: s.name })),
]);

const canApply = computed(() => selectedActId.value != null && selectedSceneId.value != null);

function handleOk(): void {
  if (canApply.value) {
    emit('apply', { actId: selectedActId.value!, sceneId: selectedSceneId.value! });
  }
}

function reset(): void {
  selectedActId.value = null;
  selectedSceneId.value = null;
}

defineExpose({ show: () => modal.value?.show(), hide: () => modal.value?.hide() });
</script>
