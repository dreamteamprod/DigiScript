<template>
  <BModal
    ref="modal"
    title="Bulk Edit"
    size="md"
    ok-title="Apply"
    :ok-disabled="!canApply"
    @ok.prevent="handleOk"
    @hidden="reset"
  >
    <p class="text-muted small mb-3">
      Applies the selected changes to all lines from the chosen start line to end line (inclusive).
      Fill in a section to apply those changes; leave it empty to skip it.
    </p>

    <h6 class="mb-2">Act / Scene</h6>
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

    <hr />

    <h6 class="mb-2">Character Assignment</h6>
    <p class="text-muted small mb-2">Lines without the selected part will be skipped.</p>
    <BFormGroup label="Part" label-for="bulk-part-input">
      <BFormSelect id="bulk-part-input" v-model="selectedPartIndex" :options="partOptions" />
    </BFormGroup>
    <template v-if="combinedDropdown">
      <BFormGroup label="Character / Character Group" label-for="bulk-char-combined-input">
        <BFormSelect
          id="bulk-char-combined-input"
          v-model="combinedValue"
          :options="combinedOptions"
          :disabled="selectedPartIndex == null"
        />
      </BFormGroup>
    </template>
    <template v-else>
      <BFormGroup
        v-show="selectedCharacterGroupId == null"
        label="Character"
        label-for="bulk-char-input"
      >
        <BFormSelect
          id="bulk-char-input"
          v-model="selectedCharacterId"
          :options="characterOptions"
          :disabled="selectedPartIndex == null"
        />
      </BFormGroup>
      <BFormGroup
        v-show="selectedCharacterId == null"
        label="Character Group"
        label-for="bulk-char-group-input"
      >
        <BFormSelect
          id="bulk-char-group-input"
          v-model="selectedCharacterGroupId"
          :options="characterGroupOptions"
          :disabled="selectedPartIndex == null"
        />
      </BFormGroup>
    </template>
  </BModal>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import type { ScriptLine } from '@/types/api/script';
import type { Act, Scene, Character, CharacterGroup } from '@/types/api/show';
import { useUserStore } from '@/stores/user';

const props = defineProps<{
  previousLineOfStart: ScriptLine | null;
  nextLineOfEnd: ScriptLine | null;
  acts: Act[];
  scenes: Scene[];
  characters: Character[];
  characterGroups: CharacterGroup[];
}>();

const emit = defineEmits<{
  apply: [
    payload: {
      actId: number | null;
      sceneId: number | null;
      partIndex: number | null;
      characterId: number | null;
      characterGroupId: number | null;
    },
  ];
}>();

const userStore = useUserStore();
const modal = ref<InstanceType<typeof BModal>>();

const selectedActId = ref<number | null>(null);
const selectedSceneId = ref<number | null>(null);
const selectedPartIndex = ref<number | null>(null);
const selectedCharacterId = ref<number | null>(null);
const selectedCharacterGroupId = ref<number | null>(null);

const combinedDropdown = computed(
  () =>
    !!(userStore.userSettings as { character_combined_dropdown?: boolean })
      .character_combined_dropdown
);

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
    cur = cur.next_act == null ? null : (props.acts.find((a) => a.id === cur!.next_act) ?? null);
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
    cur = cur.next_scene == null ? null : (actScenes.find((s) => s.id === cur!.next_scene) ?? null);
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

const partOptions = computed(() => [
  { value: null, text: 'Select a part', disabled: true },
  { value: 1, text: 'Part 1' },
  { value: 2, text: 'Part 2' },
  { value: 3, text: 'Part 3' },
  { value: 4, text: 'Part 4' },
]);

const characterOptions = computed(() => [
  { value: null, text: 'N/A' },
  ...props.characters.map((c) => ({ value: c.id, text: c.name })),
]);

const characterGroupOptions = computed(() => [
  { value: null, text: 'N/A' },
  ...props.characterGroups.map((g) => ({ value: g.id, text: g.name })),
]);

const combinedOptions = computed<{ value: string | null; text: string; disabled?: boolean }[]>(
  () => [
    { value: null, text: 'Select character / group', disabled: true },
    ...props.characters.map((c) => ({ value: `c:${c.id}`, text: c.name ?? '' })),
    ...props.characterGroups.map((g) => ({ value: `g:${g.id}`, text: g.name ?? '' })),
  ]
);

const combinedValue = computed<string | null>({
  get() {
    if (selectedCharacterId.value != null) return `c:${selectedCharacterId.value}`;
    if (selectedCharacterGroupId.value != null) return `g:${selectedCharacterGroupId.value}`;
    return null;
  },
  set(val: string | null) {
    if (val == null) {
      selectedCharacterId.value = null;
      selectedCharacterGroupId.value = null;
    } else if (val.startsWith('c:')) {
      selectedCharacterId.value = Number.parseInt(val.slice(2), 10);
      selectedCharacterGroupId.value = null;
    } else if (val.startsWith('g:')) {
      selectedCharacterId.value = null;
      selectedCharacterGroupId.value = Number.parseInt(val.slice(2), 10);
    }
  },
});

const actSceneComplete = computed(
  () => selectedActId.value != null && selectedSceneId.value != null
);

const characterComplete = computed(
  () =>
    selectedPartIndex.value != null &&
    (selectedCharacterId.value != null || selectedCharacterGroupId.value != null)
);

const canApply = computed(() => actSceneComplete.value || characterComplete.value);

function handleOk(): void {
  if (canApply.value) {
    emit('apply', {
      actId: actSceneComplete.value ? selectedActId.value : null,
      sceneId: actSceneComplete.value ? selectedSceneId.value : null,
      partIndex: characterComplete.value ? selectedPartIndex.value : null,
      characterId: characterComplete.value ? selectedCharacterId.value : null,
      characterGroupId: characterComplete.value ? selectedCharacterGroupId.value : null,
    });
  }
}

function reset(): void {
  selectedActId.value = null;
  selectedSceneId.value = null;
  selectedPartIndex.value = null;
  selectedCharacterId.value = null;
  selectedCharacterGroupId.value = null;
}

defineExpose({ show: () => modal.value?.show(), hide: () => modal.value?.hide() });
</script>
