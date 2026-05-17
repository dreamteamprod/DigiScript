<template>
  <BContainer class="mx-0 px-0" fluid>
    <BRow align-h="between">
      <BCol cols="3">
        <BFormGroup v-show="editMode" label="Microphone" label-for="mic-input" :label-cols="true">
          <BFormSelect
            id="mic-input"
            v-model="selectedMic"
            :options="micOptions"
            :disabled="!editMode || !systemStore.isShowEditor"
          />
        </BFormGroup>
      </BCol>
      <BCol cols="6" class="text-end mb-3">
        <BButtonGroup v-if="systemStore.isShowEditor">
          <BDropdown v-if="editMode" end text="Options" variant="secondary">
            <BDropdownItemButton
              :disabled="needsSaving || saving"
              @click.stop="autoPopulateModalRef?.show()"
            >
              Auto-Allocate
            </BDropdownItemButton>
            <BDropdownDivider />
            <BDropdownItemButton
              :disabled="selectedMic == null || changes[selectedMic] == null || saving"
              @click.stop="resetSelectedToStoredAlloc"
            >
              Reset Current
            </BDropdownItemButton>
            <BDropdownItemButton
              :disabled="!needsSaving || saving"
              @click.stop="resetToStoredAlloc"
            >
              Reset All
            </BDropdownItemButton>
            <BDropdownDivider />
            <BDropdownItemButton :disabled="saving" @click.stop="clearSelectedMicAllocations">
              Clear Current
            </BDropdownItemButton>
            <BDropdownItemButton :disabled="saving" @click.stop="clearMicAllocations">
              Clear All
            </BDropdownItemButton>
          </BDropdown>
          <BButton
            v-if="editMode"
            :disabled="!needsSaving || saving"
            variant="success"
            @click.stop="saveAllocations"
          >
            Save
          </BButton>
          <BButton
            :disabled="needsSaving || saving"
            variant="primary"
            @click.stop="editMode = !editMode"
          >
            {{ editMode ? 'View' : 'Edit' }}
          </BButton>
        </BButtonGroup>
      </BCol>
    </BRow>
    <BRow>
      <BCol id="allocations-table">
        <template v-if="sortedScenes.length > 0">
          <BTable
            :items="tableData"
            :fields="tableFields"
            responsive
            show-empty
            sticky-header="65vh"
          >
            <template #thead-top>
              <BTr>
                <BTh colspan="1">
                  <span class="visually-hidden">Character</span>
                </BTh>
                <template v-for="act in sortedActs" :key="act.id">
                  <BTh
                    v-if="numScenesPerAct(act.id) > 0"
                    variant="primary"
                    :colspan="numScenesPerAct(act.id)"
                    class="act-header"
                  >
                    {{ act.name }}
                  </BTh>
                </template>
              </BTr>
            </template>
            <template v-for="scene in sortedScenes" :key="scene.id" #[getHeaderName(scene.id)]>
              {{ scene.name }}
            </template>
            <template #cell(Character)="data">
              <div style="display: flex; align-items: center; gap: 0.75rem">
                <span style="white-space: nowrap; flex: 1">
                  {{ showStore.characterById(data.item.Character)?.name }}
                </span>
                <BButton
                  v-if="editMode && systemStore.isShowEditor && selectedMic != null"
                  style="height: fit-content; flex-shrink: 0"
                  squared
                  :disabled="micSelectAllDisabledForCharacter(selectedMic, data.item.Character)"
                  @click.stop="toggleSelectAllAllocation(selectedMic, data.item.Character)"
                >
                  <span
                    v-if="micSelectedAllForCharacter(selectedMic, data.item.Character)"
                    class="text-success"
                    >✓</span
                  >
                  <span v-else class="text-danger">✗</span>
                </BButton>
              </div>
            </template>
            <template v-for="scene in sortedScenes" :key="scene.id" #[getCellName(scene.id)]="data">
              <template v-if="editMode && systemStore.isShowEditor">
                <span v-if="selectedMic == null">N/A</span>
                <BButton
                  v-else
                  squared
                  :disabled="micDisabledForCharacter(selectedMic, scene.id, data.item.Character)"
                  @click.stop="toggleAllocation(selectedMic, scene.id, data.item.Character)"
                >
                  <span
                    v-if="internalState[selectedMic]?.[scene.id] === data.item.Character"
                    class="text-success"
                    >✓</span
                  >
                  <span v-else class="text-danger">✗</span>
                </BButton>
              </template>
              <template v-else>
                <div
                  v-if="allocationByCharacter[data.item.Character]?.[scene.id] != null"
                  class="allocation-cell"
                  :class="getConflictClassForCell(data.item.Character, scene.id)"
                  :title="getTooltipText(data.item.Character, scene.id)"
                >
                  {{ allocationByCharacter[data.item.Character]?.[scene.id] }}
                  <span
                    v-if="getConflictsForCell(data.item.Character, scene.id).length > 0"
                    class="conflict-icon"
                    >⚠</span
                  >
                </div>
              </template>
            </template>
          </BTable>
        </template>
        <b v-else>Unable to get mic allocations. Ensure act and scene ordering is set.</b>
      </BCol>
    </BRow>
    <MicAutoPopulateModal ref="autoPopulateModalRef" @auto-populate-result="onAutoPopulateResult" />
  </BContainer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { diff } from 'deep-object-diff';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import { useStatsTable } from '@/composables/useStatsTable';
import MicAutoPopulateModal from './MicAutoPopulateModal.vue';
import type { MicConflict } from '@/js/micConflictUtils';

const showStore = useShowStore();
const systemStore = useSystemStore();
const { sortedActs, sortedScenes, numScenesPerAct, getHeaderName, getCellName } = useStatsTable();

const selectedMic = ref<number | null>(null);
const internalState = ref<Record<string, Record<string, number | null>>>({});
const loaded = ref(false);
const saving = ref(false);
const editMode = ref(true);

const autoPopulateModalRef = ref<InstanceType<typeof MicAutoPopulateModal>>();

const micOptions = computed(() => [
  { value: null, text: 'N/A', disabled: true },
  ...showStore.microphones.map((mic) => ({ value: mic.id, text: mic.name })),
]);

const tableFields = computed(() => [
  'Character',
  ...sortedScenes.value.map((scene) => scene.id.toString()),
]);

const tableData = computed(() => {
  if (!loaded.value) return [];
  return showStore.characterList.map((character) => ({ Character: character.id }));
});

const allAllocations = computed((): Record<string, Record<string, number | null>> => {
  const micData: Record<string, Record<string, number | null>> = {};
  Object.keys(showStore.micAllocations).forEach((micId) => {
    const sceneData: Record<string, number | null> = {};
    showStore.micAllocations[micId].forEach((allocation) => {
      sceneData[allocation.scene_id] = allocation.character_id;
    });
    sortedScenes.value.forEach((scene) => {
      if (!(scene.id.toString() in sceneData)) {
        sceneData[scene.id] = null;
      }
    });
    micData[micId] = sceneData;
  });
  return micData;
});

const changes = computed(
  () =>
    diff(allAllocations.value, internalState.value) as Record<string, Record<string, number | null>>
);

const needsSaving = computed(() => Object.keys(changes.value).length > 0);

const allocationByCharacter = computed((): Record<number, Record<number, string | null>> => {
  const temp: Record<number, Record<number, string[]>> = {};
  showStore.characterList.forEach((character) => {
    temp[character.id] = {};
    sortedScenes.value.forEach((scene) => {
      temp[character.id][scene.id] = [];
    });
  });

  Object.keys(showStore.micAllocations).forEach((micId) => {
    const mic = showStore.microphoneById(parseInt(micId, 10));
    if (!mic) return;
    sortedScenes.value.forEach((scene) => {
      const charId = allAllocations.value[micId]?.[scene.id];
      if (charId != null && temp[charId]) {
        temp[charId][scene.id].push(mic.name ?? '');
      }
    });
  });

  const result: Record<number, Record<number, string | null>> = {};
  Object.keys(temp).forEach((charId) => {
    const charIdNum = parseInt(charId, 10);
    result[charIdNum] = {};
    Object.keys(temp[charIdNum]).forEach((sceneId) => {
      const sceneIdNum = parseInt(sceneId, 10);
      const mics = temp[charIdNum][sceneIdNum];
      result[charIdNum][sceneIdNum] = mics.length > 0 ? mics.join(', ') : null;
    });
  });
  return result;
});

async function resetToStoredAlloc(): Promise<void> {
  await showStore.getMicAllocations();
  const state: Record<string, Record<string, number | null>> = {};
  showStore.microphones.forEach((mic) => {
    const micData: Record<string, number | null> = {};
    sortedScenes.value.forEach((scene) => {
      micData[scene.id] = allAllocations.value[mic.id]?.[scene.id] ?? null;
    });
    state[mic.id] = micData;
  });
  internalState.value = state;
}

async function resetSelectedToStoredAlloc(): Promise<void> {
  if (selectedMic.value == null) return;
  await showStore.getMicAllocations();
  const micData: Record<string, number | null> = {};
  sortedScenes.value.forEach((scene) => {
    micData[scene.id] = allAllocations.value[selectedMic.value!]?.[scene.id] ?? null;
  });
  internalState.value[selectedMic.value] = micData;
}

function clearMicAllocations(): void {
  Object.keys(internalState.value).forEach((micId) => {
    const micData: Record<string, null> = {};
    sortedScenes.value.forEach((scene) => {
      micData[scene.id] = null;
    });
    internalState.value[micId] = micData;
  });
}

function clearSelectedMicAllocations(): void {
  if (selectedMic.value == null) return;
  const micData: Record<string, null> = {};
  sortedScenes.value.forEach((scene) => {
    micData[scene.id] = null;
  });
  internalState.value[selectedMic.value] = micData;
}

function micDisabledForCharacter(micId: number, sceneId: number, characterId: number): boolean {
  if (saving.value) return true;
  const current = internalState.value[micId]?.[sceneId];
  return current != null && current !== characterId;
}

function micSelectAllDisabledForCharacter(micId: number, characterId: number): boolean {
  if (saving.value) return true;
  for (const scene of sortedScenes.value) {
    const current = internalState.value[micId]?.[scene.id];
    if (current != null && current !== characterId) return true;
  }
  for (const mic of showStore.microphones) {
    if (mic.id === micId) continue;
    for (const scene of sortedScenes.value) {
      if (internalState.value[mic.id]?.[scene.id] === characterId) return true;
    }
  }
  return false;
}

function micSelectedAllForCharacter(micId: number, characterId: number): boolean {
  return sortedScenes.value.every(
    (scene) => internalState.value[micId]?.[scene.id] === characterId
  );
}

function toggleSelectAllAllocation(micId: number, characterId: number): void {
  const allAssigned = micSelectedAllForCharacter(micId, characterId);
  sortedScenes.value.forEach((scene) => {
    if (internalState.value[micId]) {
      internalState.value[micId][scene.id] = allAssigned ? null : characterId;
    }
  });
}

function toggleAllocation(micId: number, sceneId: number, characterId: number): void {
  if (!internalState.value[micId]) return;
  if (internalState.value[micId][sceneId] === characterId) {
    internalState.value[micId][sceneId] = null;
  } else if (internalState.value[micId][sceneId] === null) {
    internalState.value[micId][sceneId] = characterId;
  }
}

async function saveAllocations(): Promise<void> {
  saving.value = true;
  await showStore.updateMicAllocations(changes.value);
  await resetToStoredAlloc();
  saving.value = false;
}

function getConflictsForCell(characterId: number, sceneId: number): MicConflict[] {
  return Object.values(showStore.conflictsByScene)
    .flat()
    .filter((c) => c.adjacentSceneId === sceneId && c.adjacentCharacterId === characterId);
}

function getConflictClassForCell(characterId: number, sceneId: number): string {
  const conflicts = getConflictsForCell(characterId, sceneId);
  if (conflicts.length === 0) return '';
  return conflicts.some((c) => c.severity === 'WARNING') ? 'conflict-warning' : 'conflict-info';
}

function getTooltipText(characterId: number, sceneId: number): string {
  const micNames: string[] = [];
  Object.keys(showStore.micAllocations).forEach((micId) => {
    if (allAllocations.value[micId]?.[sceneId] === characterId) {
      const name = showStore.microphoneById(parseInt(micId, 10))?.name;
      if (name) micNames.push(name);
    }
  });
  const conflicts = getConflictsForCell(characterId, sceneId);
  let text = `Assigned mics: ${micNames.join(', ')}`;
  if (conflicts.length > 0) {
    text += '\n\nConflicts:';
    conflicts.forEach((c) => {
      const micName = showStore.microphoneById(c.micId)?.name ?? '';
      text += `\n• ${micName}: ${c.message}`;
    });
  }
  return text;
}

function onAutoPopulateResult(data: Record<string, unknown>): void {
  internalState.value = data as Record<string, Record<string, number | null>>;
}

onMounted(async () => {
  await resetToStoredAlloc();
  if (micOptions.value.length > 1) {
    selectedMic.value = micOptions.value[1].value as number;
  }
  loaded.value = true;
});
</script>

<style scoped>
.act-header {
  border-left: 0.1rem solid;
  border-right: 0.1rem solid;
  border-color: inherit;
}

.allocation-cell {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  min-width: 3rem;
  max-width: 15rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conflict-warning {
  background-color: #ff9800;
  color: #000;
  font-weight: 500;
}

.conflict-info {
  background-color: #2196f3;
  color: #fff;
  font-weight: 500;
}

.conflict-icon {
  margin-left: 0.25rem;
  font-size: 0.875rem;
}
</style>
