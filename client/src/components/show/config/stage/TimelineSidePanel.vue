<template>
  <div class="side-panel" :class="{ open: isOpen }">
    <div v-if="selectedItem" class="panel-content">
      <div class="panel-header">
        <h5>{{ itemName }}</h5>
        <BButton variant="link" size="sm" class="close-btn" @click="$emit('close')">
          <IMdiClose />
        </BButton>
      </div>
      <div class="panel-body">
        <div class="block-info text-muted mb-3">Block: {{ blockRange }}</div>

        <div class="assignment-section mb-4">
          <h6 class="section-header">SET ({{ setSceneName }})</h6>
          <div v-if="setAssignments.length === 0" class="text-muted small">No crew assigned</div>
          <div v-else class="assignment-list">
            <div v-for="assignment in setAssignments" :key="assignment.id" class="assignment-item">
              <span class="crew-name">{{ getCrewDisplayName(assignment.crew_id) }}</span>
              <BButton
                variant="link"
                size="sm"
                class="remove-btn text-danger"
                :disabled="saving"
                @click="removeAssignment(assignment)"
              >
                <IMdiClose />
              </BButton>
            </div>
          </div>
          <div class="add-crew-container mt-2">
            <BFormSelect
              v-model="newSetCrewId"
              :options="availableCrewForSet"
              :disabled="saving"
              size="sm"
              class="add-crew-select"
            >
              <template #first>
                <BFormSelectOption :value="null" disabled>+ Add crew member</BFormSelectOption>
              </template>
            </BFormSelect>
            <BButton
              v-show="newSetCrewId"
              variant="primary"
              size="sm"
              :disabled="saving"
              @click="addSetAssignment"
            >
              Add
            </BButton>
          </div>
        </div>

        <div class="assignment-section mb-4">
          <h6 class="section-header">STRIKE ({{ strikeSceneName }})</h6>
          <div v-if="strikeAssignments.length === 0" class="text-muted small">No crew assigned</div>
          <div v-else class="assignment-list">
            <div
              v-for="assignment in strikeAssignments"
              :key="assignment.id"
              class="assignment-item"
            >
              <span class="crew-name">{{ getCrewDisplayName(assignment.crew_id) }}</span>
              <BButton
                variant="link"
                size="sm"
                class="remove-btn text-danger"
                :disabled="saving"
                @click="removeAssignment(assignment)"
              >
                <IMdiClose />
              </BButton>
            </div>
          </div>
          <div class="add-crew-container mt-2">
            <BFormSelect
              v-model="newStrikeCrewId"
              :options="availableCrewForStrike"
              :disabled="saving"
              size="sm"
              class="add-crew-select"
            >
              <template #first>
                <BFormSelectOption :value="null" disabled>+ Add crew member</BFormSelectOption>
              </template>
            </BFormSelect>
            <BButton
              v-show="newStrikeCrewId"
              variant="primary"
              size="sm"
              :disabled="saving"
              @click="addStrikeAssignment"
            >
              Add
            </BButton>
          </div>
        </div>

        <div v-if="conflicts.length > 0" class="conflicts-section">
          <h6 class="section-header text-warning"><IMdiAlert /> Conflicts</h6>
          <div v-for="conflict in conflicts" :key="conflict.key" class="conflict-item small">
            <strong>{{ conflict.crewName }}</strong> has conflict in {{ conflict.sceneName }} ({{
              conflict.itemName
            }}
            {{ conflict.type }})
          </div>
        </div>
      </div>
    </div>
    <div v-else class="panel-placeholder text-muted">Click an allocation bar to view details</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useStageStore } from '@/stores/stage';
import { useShowStore } from '@/stores/show';
import { useConfirm } from '@/composables/useConfirm';
import type { Crew, CrewAssignment } from '@/types/api/stage';
import log from 'loglevel';

interface SelectedItem {
  type: 'prop' | 'scenery';
  itemId: number;
  startScene: number;
  endScene: number;
}

const props = defineProps<{
  selectedItem: SelectedItem | null;
  isOpen: boolean;
}>();

const emit = defineEmits<{
  close: [];
}>();

const stageStore = useStageStore();
const showStore = useShowStore();
const { confirm } = useConfirm();

const newSetCrewId = ref<number | null>(null);
const newStrikeCrewId = ref<number | null>(null);
const saving = ref(false);

watch(
  () => props.selectedItem,
  () => {
    newSetCrewId.value = null;
    newStrikeCrewId.value = null;
  }
);

const item = computed(() => {
  if (!props.selectedItem) return null;
  return props.selectedItem.type === 'prop'
    ? stageStore.propById(props.selectedItem.itemId)
    : stageStore.sceneryById(props.selectedItem.itemId);
});

const itemName = computed(() => item.value?.name ?? 'Unknown');

const setScene = computed(() =>
  props.selectedItem ? (showStore.orderedScenes[props.selectedItem.startScene] ?? null) : null
);
const strikeScene = computed(() =>
  props.selectedItem ? (showStore.orderedScenes[props.selectedItem.endScene] ?? null) : null
);

const setSceneId = computed(() => setScene.value?.id ?? null);
const strikeSceneId = computed(() => strikeScene.value?.id ?? null);

const setSceneName = computed(() => {
  if (!setScene.value) return '';
  const act = showStore.actById(setScene.value.act);
  return `${act?.name ?? 'Act'}: ${setScene.value.name}`;
});

const strikeSceneName = computed(() => {
  if (!strikeScene.value) return '';
  const act = showStore.actById(strikeScene.value.act);
  return `${act?.name ?? 'Act'}: ${strikeScene.value.name}`;
});

const isSingleSceneBlock = computed(() => setSceneId.value === strikeSceneId.value);

const blockRange = computed(() => {
  if (isSingleSceneBlock.value) return setSceneName.value;
  return `${setSceneName.value} - ${strikeSceneName.value}`;
});

const itemAssignments = computed((): CrewAssignment[] => {
  if (!props.selectedItem) return [];
  return props.selectedItem.type === 'prop'
    ? (stageStore.crewAssignmentsByProp[props.selectedItem.itemId] ?? [])
    : (stageStore.crewAssignmentsByScenery[props.selectedItem.itemId] ?? []);
});

const setAssignments = computed(() =>
  itemAssignments.value.filter(
    (a) => a.assignment_type === 'set' && a.scene_id === setSceneId.value
  )
);

const strikeAssignments = computed(() =>
  itemAssignments.value.filter(
    (a) => a.assignment_type === 'strike' && a.scene_id === strikeSceneId.value
  )
);

const assignedSetCrewIds = computed(() => new Set(setAssignments.value.map((a) => a.crew_id)));
const assignedStrikeCrewIds = computed(
  () => new Set(strikeAssignments.value.map((a) => a.crew_id))
);

function formatCrewName(crew: Crew | null): string {
  if (!crew) return 'Unknown';
  return [crew.first_name, crew.last_name].filter(Boolean).join(' ');
}

function getCrewDisplayName(crewId: number): string {
  return formatCrewName(stageStore.crewById(crewId));
}

const availableCrewForSet = computed(() =>
  stageStore.crewList
    .filter((c) => !assignedSetCrewIds.value.has(c.id))
    .map((c) => ({ value: c.id, text: formatCrewName(c) }))
);

const availableCrewForStrike = computed(() =>
  stageStore.crewList
    .filter((c) => !assignedStrikeCrewIds.value.has(c.id))
    .map((c) => ({ value: c.id, text: formatCrewName(c) }))
);

const conflicts = computed(() => {
  const result: Array<{
    key: string;
    crewName: string;
    sceneName: string;
    itemName: string;
    type: string;
  }> = [];

  for (const assignment of [...setAssignments.value, ...strikeAssignments.value]) {
    const sceneAssignments = stageStore.crewAssignmentsByScene[assignment.scene_id] ?? [];
    const otherAssignments = sceneAssignments.filter(
      (a) =>
        a.crew_id === assignment.crew_id &&
        a.id !== assignment.id &&
        !(a.prop_id === props.selectedItem?.itemId && props.selectedItem?.type === 'prop') &&
        !(a.scenery_id === props.selectedItem?.itemId && props.selectedItem?.type === 'scenery')
    );

    for (const other of otherAssignments) {
      const otherItem =
        other.prop_id == null
          ? stageStore.sceneryById(other.scenery_id)
          : stageStore.propById(other.prop_id);
      const crew = stageStore.crewById(assignment.crew_id);
      const scene = showStore.orderedScenes.find((s) => s.id === assignment.scene_id);
      result.push({
        key: `${assignment.id}-${other.id}`,
        crewName: formatCrewName(crew),
        sceneName: scene?.name ?? 'Unknown',
        itemName: otherItem?.name ?? 'Unknown',
        type: other.assignment_type.toUpperCase(),
      });
    }
  }

  return result;
});

async function addSetAssignment(): Promise<void> {
  if (!newSetCrewId.value || !setSceneId.value || saving.value) return;
  saving.value = true;
  try {
    const assignment: Record<string, unknown> = {
      crew_id: newSetCrewId.value,
      scene_id: setSceneId.value,
      assignment_type: 'set',
    };
    if (props.selectedItem?.type === 'prop') {
      assignment.prop_id = props.selectedItem.itemId;
    } else {
      assignment.scenery_id = props.selectedItem?.itemId;
    }
    const success = await stageStore.addCrewAssignment(assignment);
    if (success) newSetCrewId.value = null;
  } catch (e) {
    log.error('Error adding set assignment:', e);
  } finally {
    saving.value = false;
  }
}

async function addStrikeAssignment(): Promise<void> {
  if (!newStrikeCrewId.value || !strikeSceneId.value || saving.value) return;
  saving.value = true;
  try {
    const assignment: Record<string, unknown> = {
      crew_id: newStrikeCrewId.value,
      scene_id: strikeSceneId.value,
      assignment_type: 'strike',
    };
    if (props.selectedItem?.type === 'prop') {
      assignment.prop_id = props.selectedItem.itemId;
    } else {
      assignment.scenery_id = props.selectedItem?.itemId;
    }
    const success = await stageStore.addCrewAssignment(assignment);
    if (success) newStrikeCrewId.value = null;
  } catch (e) {
    log.error('Error adding strike assignment:', e);
  } finally {
    saving.value = false;
  }
}

async function removeAssignment(assignment: CrewAssignment): Promise<void> {
  if (saving.value) return;
  const crewName = getCrewDisplayName(assignment.crew_id);
  const ok = await confirm(
    `Remove ${crewName} from this ${assignment.assignment_type.toUpperCase()} assignment?`,
    { okTitle: 'Remove', okVariant: 'danger' }
  );
  if (!ok) return;
  saving.value = true;
  try {
    await stageStore.deleteCrewAssignment(assignment.id);
  } catch (e) {
    log.error('Error removing assignment:', e);
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped lang="scss">
.side-panel {
  width: 0;
  min-width: 0;
  overflow: hidden;
  transition:
    width 0.3s ease,
    min-width 0.3s ease;
  border-left: 1px solid rgba(255, 255, 255, 0.1);
  background: var(--body-background);

  &.open {
    width: 300px;
    min-width: 300px;
  }
}

.panel-content {
  width: 300px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);

  h5 {
    margin: 0;
    font-size: 1rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .close-btn {
    padding: 0;
    line-height: 1;
  }
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.block-info {
  font-size: 0.85rem;
}

.assignment-section {
  .section-header {
    font-size: 0.9rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
    padding-bottom: 0.25rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }
}

.assignment-list {
  margin-bottom: 0.5rem;
}

.assignment-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.05);
  margin-bottom: 0.25rem;

  .crew-name {
    font-size: 0.9rem;
  }

  .remove-btn {
    padding: 0;
    line-height: 1;
  }
}

.add-crew-container {
  display: flex;
  gap: 0.5rem;
  align-items: center;

  .add-crew-select {
    flex: 1;
  }
}

.conflicts-section {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 1rem;

  .section-header {
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
  }

  .conflict-item {
    padding: 0.5rem;
    background: rgba(255, 193, 7, 0.2);
    border-radius: 4px;
    margin-bottom: 0.25rem;
  }
}

.panel-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 1rem;
  text-align: center;
}
</style>
