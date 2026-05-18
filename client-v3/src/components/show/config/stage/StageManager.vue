<template>
  <BContainer class="mx-0 px-0 stage-manager-container" fluid>
    <template v-if="loaded && orderedScenes.length > 0">
      <div class="sticky-header" :style="{ top: navbarHeight + 'px' }">
        <BRow>
          <BCol cols="2">
            <BButton
              :disabled="orderedScenes.length === 0"
              variant="success"
              @click="goToSceneModal?.show()"
            >
              Go to Scene
            </BButton>
          </BCol>
          <BCol cols="2" style="text-align: right">
            <BButton variant="success" :disabled="currentSceneIndex === 0" @click="decrScene">
              Prev Scene
            </BButton>
          </BCol>
          <BCol cols="4" class="text-center">
            <b>{{ currentSceneLabel }}</b>
          </BCol>
          <BCol cols="2" style="text-align: left">
            <BButton
              variant="success"
              :disabled="
                orderedScenes.length === 0 || currentSceneIndex === orderedScenes.length - 1
              "
              @click="incrScene"
            >
              Next Scene
            </BButton>
          </BCol>
          <BCol cols="2" />
        </BRow>
      </div>

      <!-- Allocations card -->
      <BCard no-body class="section-card mt-2">
        <BCardHeader
          class="section-card-header"
          @click="allocationsExpanded = !allocationsExpanded"
        >
          <div class="d-flex justify-content-between align-items-center">
            <span>
              Allocations
              <BBadge variant="light" class="ml-1">
                {{ currentSceneSceneryAllocations.length + currentScenePropsAllocations.length }}
              </BBadge>
            </span>
            <span>{{ allocationsExpanded ? '▲' : '▼' }}</span>
          </div>
        </BCardHeader>
        <BCollapse v-model="allocationsExpanded">
          <BCardBody>
            <div class="d-flex justify-content-end mb-2">
              <BDropdown :disabled="orderedScenes.length === 0" right text="Add" variant="success">
                <BDropdownItem @click="addSceneryModal?.show()">Scenery</BDropdownItem>
                <BDropdownItem @click="addPropModal?.show()">Prop</BDropdownItem>
              </BDropdown>
            </div>
            <BRow>
              <BCol cols="6" style="border-right: 1px solid #dee2e6">
                <h5>Scenery</h5>
                <BTable
                  :items="currentSceneSceneryAllocations"
                  :fields="sceneryAllocFields"
                  :per-page="rowsPerPage"
                  :current-page="currentSceneryAllocPage"
                  show-empty
                  empty-text="No scenery allocated to this scene"
                >
                  <template #cell(scenery_name)="data">
                    {{ stageStore.sceneryById(data.item.scenery_id)?.name }}
                  </template>
                  <template #cell(scenery_type)="data">
                    {{
                      stageStore.sceneryTypeById(
                        stageStore.sceneryById(data.item.scenery_id)?.scenery_type_id ?? null
                      )?.name
                    }}
                  </template>
                  <template #cell(btn)="data">
                    <BButton variant="danger" size="sm" @click="deleteSceneryAllocation(data.item)">
                      Delete
                    </BButton>
                  </template>
                </BTable>
                <BPagination
                  v-if="currentSceneSceneryAllocations.length > rowsPerPage"
                  v-model="currentSceneryAllocPage"
                  :total-rows="currentSceneSceneryAllocations.length"
                  :per-page="rowsPerPage"
                />
              </BCol>
              <BCol cols="6">
                <h5>Props</h5>
                <BTable
                  :items="currentScenePropsAllocations"
                  :fields="propsAllocFields"
                  :per-page="rowsPerPage"
                  :current-page="currentPropsAllocPage"
                  show-empty
                  empty-text="No props allocated to this scene"
                >
                  <template #cell(prop_name)="data">
                    {{ stageStore.propById(data.item.props_id)?.name }}
                  </template>
                  <template #cell(prop_type)="data">
                    {{
                      stageStore.propTypeById(
                        stageStore.propById(data.item.props_id)?.prop_type_id ?? null
                      )?.name
                    }}
                  </template>
                  <template #cell(btn)="data">
                    <BButton variant="danger" size="sm" @click="deletePropAllocation(data.item)">
                      Delete
                    </BButton>
                  </template>
                </BTable>
                <BPagination
                  v-if="currentScenePropsAllocations.length > rowsPerPage"
                  v-model="currentPropsAllocPage"
                  :total-rows="currentScenePropsAllocations.length"
                  :per-page="rowsPerPage"
                />
              </BCol>
            </BRow>
          </BCardBody>
        </BCollapse>
      </BCard>

      <!-- SET card -->
      <BCard v-if="setItems.length > 0" no-body class="section-card mt-2">
        <BCardHeader class="section-card-header" @click="setExpanded = !setExpanded">
          <div class="d-flex justify-content-between align-items-center">
            <span>
              SET
              <BBadge variant="light" class="ml-1">{{ setItems.length }}</BBadge>
            </span>
            <span class="d-flex align-items-center gap-1">
              <BBadge v-if="unassignedSetCount > 0" variant="warning">
                {{ unassignedSetCount }} unassigned
              </BBadge>
              <span>{{ setExpanded ? '▲' : '▼' }}</span>
            </span>
          </div>
        </BCardHeader>
        <BCollapse v-model="setExpanded">
          <BCardBody class="crew-card-body">
            <div class="boundary-items-grid">
              <div
                v-for="item in setItems"
                :key="'set-' + item.itemType + '-' + item.itemId"
                class="boundary-item"
              >
                <div class="boundary-item-header">
                  <span class="item-name">{{ item.name }}</span>
                  <BBadge variant="secondary" pill class="ml-1">{{ item.itemType }}</BBadge>
                </div>
                <div class="assignment-list">
                  <span
                    v-for="assignment in getAssignmentsForItem(item.itemId, item.itemType, 'set')"
                    :key="assignment.id"
                    class="crew-badge"
                  >
                    {{ formatCrewName(stageStore.crewById(assignment.crew_id)) }}
                    <BButton
                      variant="link"
                      size="sm"
                      class="remove-btn text-danger p-0 ml-1"
                      :disabled="savingAssignment"
                      @click="removeCrewAssignment(assignment)"
                    >
                      &#215;
                    </BButton>
                  </span>
                  <span
                    v-if="getAssignmentsForItem(item.itemId, item.itemType, 'set').length === 0"
                    class="text-muted small"
                  >
                    No crew assigned
                  </span>
                </div>
                <div class="add-crew-container mt-1">
                  <BFormSelect
                    :model-value="
                      newCrewSelections[crewSelectionKey(item.itemId, item.itemType, 'set')]
                    "
                    :options="getAvailableCrewForItem(item.itemId, item.itemType, 'set')"
                    :disabled="savingAssignment"
                    size="sm"
                    class="add-crew-select"
                    @update:model-value="
                      newCrewSelections[crewSelectionKey(item.itemId, item.itemType, 'set')] =
                        $event
                    "
                  >
                    <template #first>
                      <BFormSelectOption :value="null" disabled>+ Add crew</BFormSelectOption>
                    </template>
                  </BFormSelect>
                  <BButton
                    v-show="newCrewSelections[crewSelectionKey(item.itemId, item.itemType, 'set')]"
                    variant="primary"
                    size="sm"
                    :disabled="savingAssignment"
                    @click="addCrewAssignment(item.itemId, item.itemType, 'set')"
                  >
                    Add
                  </BButton>
                </div>
              </div>
            </div>
          </BCardBody>
        </BCollapse>
      </BCard>

      <!-- STRIKE card -->
      <BCard v-if="strikeItems.length > 0" no-body class="section-card mt-2">
        <BCardHeader class="section-card-header" @click="strikeExpanded = !strikeExpanded">
          <div class="d-flex justify-content-between align-items-center">
            <span>
              STRIKE
              <BBadge variant="light" class="ml-1">{{ strikeItems.length }}</BBadge>
            </span>
            <span class="d-flex align-items-center gap-1">
              <BBadge v-if="unassignedStrikeCount > 0" variant="warning">
                {{ unassignedStrikeCount }} unassigned
              </BBadge>
              <span>{{ strikeExpanded ? '▲' : '▼' }}</span>
            </span>
          </div>
        </BCardHeader>
        <BCollapse v-model="strikeExpanded">
          <BCardBody class="crew-card-body">
            <div class="boundary-items-grid">
              <div
                v-for="item in strikeItems"
                :key="'strike-' + item.itemType + '-' + item.itemId"
                class="boundary-item"
              >
                <div class="boundary-item-header">
                  <span class="item-name">{{ item.name }}</span>
                  <BBadge variant="secondary" pill class="ml-1">{{ item.itemType }}</BBadge>
                </div>
                <div class="assignment-list">
                  <span
                    v-for="assignment in getAssignmentsForItem(
                      item.itemId,
                      item.itemType,
                      'strike'
                    )"
                    :key="assignment.id"
                    class="crew-badge"
                  >
                    {{ formatCrewName(stageStore.crewById(assignment.crew_id)) }}
                    <BButton
                      variant="link"
                      size="sm"
                      class="remove-btn text-danger p-0 ml-1"
                      :disabled="savingAssignment"
                      @click="removeCrewAssignment(assignment)"
                    >
                      &#215;
                    </BButton>
                  </span>
                  <span
                    v-if="getAssignmentsForItem(item.itemId, item.itemType, 'strike').length === 0"
                    class="text-muted small"
                  >
                    No crew assigned
                  </span>
                </div>
                <div class="add-crew-container mt-1">
                  <BFormSelect
                    :model-value="
                      newCrewSelections[crewSelectionKey(item.itemId, item.itemType, 'strike')]
                    "
                    :options="getAvailableCrewForItem(item.itemId, item.itemType, 'strike')"
                    :disabled="savingAssignment"
                    size="sm"
                    class="add-crew-select"
                    @update:model-value="
                      newCrewSelections[crewSelectionKey(item.itemId, item.itemType, 'strike')] =
                        $event
                    "
                  >
                    <template #first>
                      <BFormSelectOption :value="null" disabled>+ Add crew</BFormSelectOption>
                    </template>
                  </BFormSelect>
                  <BButton
                    v-show="
                      newCrewSelections[crewSelectionKey(item.itemId, item.itemType, 'strike')]
                    "
                    variant="primary"
                    size="sm"
                    :disabled="savingAssignment"
                    @click="addCrewAssignment(item.itemId, item.itemType, 'strike')"
                  >
                    Add
                  </BButton>
                </div>
              </div>
            </div>
          </BCardBody>
        </BCollapse>
      </BCard>

      <!-- Go to Scene modal -->
      <BModal
        ref="goToSceneModal"
        title="Go To Scene"
        @hidden="resetGoToSceneForm"
        @ok.prevent="onSubmitGoToScene"
      >
        <BForm>
          <BFormGroup label="Scene" label-for="goto-scene-select">
            <BFormSelect
              id="goto-scene-select"
              v-model="goToSceneForm.scene_index"
              :options="sceneFormOptions"
              :state="validationState(vGoTo$.scene_index)"
            />
            <BFormInvalidFeedback>
              {{ vGoTo$.scene_index.$errors[0]?.$message }}
            </BFormInvalidFeedback>
          </BFormGroup>
        </BForm>
      </BModal>

      <!-- Add Scenery modal -->
      <BModal
        ref="addSceneryModal"
        title="Add Scenery to Scene"
        @hidden="resetAddSceneryForm"
        @ok.prevent="onSubmitAddScenery"
      >
        <BForm>
          <BFormGroup label="Scenery" label-for="add-scenery-select">
            <BFormSelect
              id="add-scenery-select"
              v-model="addSceneryForm.scenery_id"
              :state="validationState(vAddScenery$.scenery_id)"
            >
              <template #first>
                <BFormSelectOption :value="null" disabled
                  >Please select scenery...</BFormSelectOption
                >
              </template>
              <BFormSelectOptionGroup
                v-for="group in sceneryOptionsByType"
                :key="group.label"
                :label="group.label"
              >
                <BFormSelectOption
                  v-for="option in group.options"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.text }}
                </BFormSelectOption>
              </BFormSelectOptionGroup>
            </BFormSelect>
            <BFormInvalidFeedback>
              {{ vAddScenery$.scenery_id.$errors[0]?.$message }}
            </BFormInvalidFeedback>
          </BFormGroup>
        </BForm>
      </BModal>

      <!-- Add Prop modal -->
      <BModal
        ref="addPropModal"
        title="Add Prop to Scene"
        @hidden="resetAddPropForm"
        @ok.prevent="onSubmitAddProp"
      >
        <BForm>
          <BFormGroup label="Prop" label-for="add-prop-select">
            <BFormSelect
              id="add-prop-select"
              v-model="addPropForm.props_id"
              :state="validationState(vAddProp$.props_id)"
            >
              <template #first>
                <BFormSelectOption :value="null" disabled
                  >Please select a prop...</BFormSelectOption
                >
              </template>
              <BFormSelectOptionGroup
                v-for="group in propOptionsByType"
                :key="group.label"
                :label="group.label"
              >
                <BFormSelectOption
                  v-for="option in group.options"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.text }}
                </BFormSelectOption>
              </BFormSelectOptionGroup>
            </BFormSelect>
            <BFormInvalidFeedback>
              {{ vAddProp$.props_id.$errors[0]?.$message }}
            </BFormInvalidFeedback>
          </BFormGroup>
        </BForm>
      </BModal>
    </template>

    <BRow v-else>
      <BCol>
        <BAlert v-if="loaded" variant="danger" show>
          There are no scenes configured for this show.
        </BAlert>
        <div v-else class="text-center py-5">
          <BSpinner label="Loading" />
        </div>
      </BCol>
    </BRow>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import { useVuelidate } from '@vuelidate/core';
import { required, helpers } from '@vuelidate/validators';
import { useStageStore } from '@/stores/stage';
import { useShowStore } from '@/stores/show';
import { useConfirm } from '@/composables/useConfirm';
import { useFormValidation } from '@/composables/useFormValidation';
import { findOrphanedAssignments } from '@/js/blockOrphanUtils';
import type { SceneryAllocation, PropsAllocation, CrewAssignment, Crew } from '@/types/api/stage';
import log from 'loglevel';

const stageStore = useStageStore();
const showStore = useShowStore();
const { confirm } = useConfirm();
const { validationState } = useFormValidation();

const loaded = ref(false);
const navbarHeight = ref(56);
const currentSceneIndex = ref(0);
const allocationsExpanded = ref(true);
const setExpanded = ref(false);
const strikeExpanded = ref(false);
const savingAssignment = ref(false);
const newCrewSelections = ref<Record<string, number | null>>({});
const rowsPerPage = 10;
const currentSceneryAllocPage = ref(1);
const currentPropsAllocPage = ref(1);

const goToSceneModal = ref<InstanceType<typeof BModal>>();
const addSceneryModal = ref<InstanceType<typeof BModal>>();
const addPropModal = ref<InstanceType<typeof BModal>>();

const goToSceneForm = ref<{ scene_index: number | null }>({ scene_index: null });
const addSceneryForm = ref<{ scenery_id: number | null }>({ scenery_id: null });
const addPropForm = ref<{ props_id: number | null }>({ props_id: null });

const sceneryAllocFields = [
  { key: 'scenery_name', label: 'Name' },
  { key: 'scenery_type', label: 'Type' },
  { key: 'btn', label: '' },
];
const propsAllocFields = [
  { key: 'prop_name', label: 'Name' },
  { key: 'prop_type', label: 'Type' },
  { key: 'btn', label: '' },
];

const notNull = helpers.withMessage('This is a required field.', (v: unknown) => v !== null);
const vGoTo$ = useVuelidate({ scene_index: { required, notNull } }, goToSceneForm);
const vAddScenery$ = useVuelidate({ scenery_id: { required, notNull } }, addSceneryForm);
const vAddProp$ = useVuelidate({ props_id: { required, notNull } }, addPropForm);

const orderedScenes = computed(() => showStore.orderedScenes);
const currentScene = computed(() => orderedScenes.value[currentSceneIndex.value] ?? null);

const currentSceneLabel = computed(() => {
  if (!currentScene.value) return 'N/A';
  const act = showStore.actById(currentScene.value.act);
  return `${act?.name ?? 'Act'}: ${currentScene.value.name}`;
});

const sceneFormOptions = computed(() => [
  { value: null, text: 'Please select an option', disabled: true },
  ...orderedScenes.value.map((scene, index) => ({
    value: index,
    text: `${showStore.actById(scene.act)?.name ?? 'Act'}: ${scene.name}`,
  })),
]);

const previousSceneInAct = computed(() => {
  if (currentSceneIndex.value <= 0 || !currentScene.value) return null;
  const prev = orderedScenes.value[currentSceneIndex.value - 1];
  return prev?.act === currentScene.value.act ? prev : null;
});

const nextSceneInAct = computed(() => {
  if (!currentScene.value || currentSceneIndex.value >= orderedScenes.value.length - 1) return null;
  const next = orderedScenes.value[currentSceneIndex.value + 1];
  return next?.act === currentScene.value.act ? next : null;
});

const currentSceneSceneryAllocations = computed((): SceneryAllocation[] => {
  if (!currentScene.value) return [];
  return stageStore.sceneryAllocations.filter((a) => a.scene_id === currentScene.value!.id);
});

const currentScenePropsAllocations = computed((): PropsAllocation[] => {
  if (!currentScene.value) return [];
  return stageStore.propsAllocations.filter((a) => a.scene_id === currentScene.value!.id);
});

const setItems = computed(() => {
  if (!currentScene.value) return [];
  const sceneId = currentScene.value.id;
  const prevSceneId = previousSceneInAct.value?.id;
  const items: Array<{ itemId: number; itemType: string; name: string }> = [];

  for (const scenery of stageStore.sceneryList) {
    const allocs = stageStore.sceneryAllocationsByItem[scenery.id] ?? [];
    if (!allocs.some((a) => a.scene_id === sceneId)) continue;
    if (!prevSceneId || !allocs.some((a) => a.scene_id === prevSceneId)) {
      items.push({ itemId: scenery.id, itemType: 'scenery', name: scenery.name });
    }
  }
  for (const prop of stageStore.propsList) {
    const allocs = stageStore.propsAllocationsByItem[prop.id] ?? [];
    if (!allocs.some((a) => a.scene_id === sceneId)) continue;
    if (!prevSceneId || !allocs.some((a) => a.scene_id === prevSceneId)) {
      items.push({ itemId: prop.id, itemType: 'prop', name: prop.name });
    }
  }
  return items;
});

const strikeItems = computed(() => {
  if (!currentScene.value) return [];
  const sceneId = currentScene.value.id;
  const nextSceneId = nextSceneInAct.value?.id;
  const items: Array<{ itemId: number; itemType: string; name: string }> = [];

  for (const scenery of stageStore.sceneryList) {
    const allocs = stageStore.sceneryAllocationsByItem[scenery.id] ?? [];
    if (!allocs.some((a) => a.scene_id === sceneId)) continue;
    if (!nextSceneId || !allocs.some((a) => a.scene_id === nextSceneId)) {
      items.push({ itemId: scenery.id, itemType: 'scenery', name: scenery.name });
    }
  }
  for (const prop of stageStore.propsList) {
    const allocs = stageStore.propsAllocationsByItem[prop.id] ?? [];
    if (!allocs.some((a) => a.scene_id === sceneId)) continue;
    if (!nextSceneId || !allocs.some((a) => a.scene_id === nextSceneId)) {
      items.push({ itemId: prop.id, itemType: 'prop', name: prop.name });
    }
  }
  return items;
});

const unassignedSetCount = computed(
  () =>
    setItems.value.filter(
      (item) => getAssignmentsForItem(item.itemId, item.itemType, 'set').length === 0
    ).length
);

const unassignedStrikeCount = computed(
  () =>
    strikeItems.value.filter(
      (item) => getAssignmentsForItem(item.itemId, item.itemType, 'strike').length === 0
    ).length
);

const availableSceneryForScene = computed(() => {
  if (!currentScene.value) return [];
  const allocatedIds = new Set(
    stageStore.sceneryAllocations
      .filter((a) => a.scene_id === currentScene.value!.id)
      .map((a) => a.scenery_id)
  );
  return stageStore.sceneryList.filter((s) => !allocatedIds.has(s.id));
});

const availablePropsForScene = computed(() => {
  if (!currentScene.value) return [];
  const allocatedIds = new Set(
    stageStore.propsAllocations
      .filter((a) => a.scene_id === currentScene.value!.id)
      .map((a) => a.props_id)
  );
  return stageStore.propsList.filter((p) => !allocatedIds.has(p.id));
});

const sceneryOptionsByType = computed(() =>
  stageStore.sceneryTypes
    .map((type) => ({
      label: type.name,
      options: availableSceneryForScene.value
        .filter((s) => s.scenery_type_id === type.id)
        .map((s) => ({ value: s.id, text: s.name })),
    }))
    .filter((group) => group.options.length > 0)
);

const propOptionsByType = computed(() =>
  stageStore.propTypes
    .map((type) => ({
      label: type.name,
      options: availablePropsForScene.value
        .filter((p) => p.prop_type_id === type.id)
        .map((p) => ({ value: p.id, text: p.name })),
    }))
    .filter((group) => group.options.length > 0)
);

function calculateNavbarHeight(): void {
  const navbar = document.querySelector('.navbar') as HTMLElement | null;
  navbarHeight.value = navbar?.offsetHeight ?? 56;
}

function incrScene(): void {
  if (currentSceneIndex.value < orderedScenes.value.length - 1) {
    currentSceneIndex.value += 1;
  }
}

function decrScene(): void {
  if (currentSceneIndex.value > 0) {
    currentSceneIndex.value -= 1;
  }
}

function formatCrewName(crew: Crew | null): string {
  if (!crew) return 'Unknown';
  return [crew.first_name, crew.last_name].filter(Boolean).join(' ');
}

function crewSelectionKey(itemId: number, itemType: string, assignmentType: string): string {
  return `${itemType}-${itemId}-${assignmentType}`;
}

function getAssignmentsForItem(
  itemId: number,
  itemType: string,
  assignmentType: string
): CrewAssignment[] {
  const assignments: CrewAssignment[] =
    itemType === 'prop'
      ? (stageStore.crewAssignmentsByProp[itemId] ?? [])
      : (stageStore.crewAssignmentsByScenery[itemId] ?? []);
  return assignments.filter(
    (a) => a.assignment_type === assignmentType && a.scene_id === currentScene.value?.id
  );
}

function getAvailableCrewForItem(
  itemId: number,
  itemType: string,
  assignmentType: string
): Array<{ value: number; text: string }> {
  const assigned = new Set(
    getAssignmentsForItem(itemId, itemType, assignmentType).map((a) => a.crew_id)
  );
  return stageStore.crewList
    .filter((c) => !assigned.has(c.id))
    .map((c) => ({ value: c.id, text: formatCrewName(c) }));
}

function buildOrphanMessage(orphans: CrewAssignment[]): string {
  const lines = orphans.map((o) => {
    const crew = stageStore.crewById(o.crew_id);
    return `• ${formatCrewName(crew)} (${o.assignment_type.toUpperCase()})`;
  });
  return `This action will remove the following crew assignments:\n${lines.join('\n')}\n\nYou can reassign crew after the change.`;
}

function findOrphansForItem(
  itemId: number,
  itemType: string,
  changeType: 'add' | 'remove',
  sceneId: number
): CrewAssignment[] {
  const allocations =
    itemType === 'scenery'
      ? stageStore.sceneryAllocations.filter((a) => a.scenery_id === itemId)
      : stageStore.propsAllocations.filter((a) => a.props_id === itemId);
  const crewAssignments: CrewAssignment[] =
    itemType === 'scenery'
      ? (stageStore.crewAssignmentsByScenery[itemId] ?? [])
      : (stageStore.crewAssignmentsByProp[itemId] ?? []);
  return findOrphanedAssignments({
    orderedScenes: orderedScenes.value,
    currentAllocations: allocations,
    crewAssignments,
    changeType,
    changeSceneId: sceneId,
  }) as unknown as CrewAssignment[];
}

function resetGoToSceneForm(): void {
  goToSceneForm.value = { scene_index: null };
  vGoTo$.value.$reset();
}

function resetAddSceneryForm(): void {
  addSceneryForm.value = { scenery_id: null };
  vAddScenery$.value.$reset();
}

function resetAddPropForm(): void {
  addPropForm.value = { props_id: null };
  vAddProp$.value.$reset();
}

async function onSubmitGoToScene(): Promise<void> {
  const valid = await vGoTo$.value.$validate();
  if (!valid) return;
  currentSceneIndex.value = goToSceneForm.value.scene_index!;
  goToSceneModal.value?.hide();
}

async function onSubmitAddScenery(): Promise<void> {
  const valid = await vAddScenery$.value.$validate();
  if (!valid || !currentScene.value) return;
  const sceneryId = addSceneryForm.value.scenery_id!;
  const orphans = findOrphansForItem(sceneryId, 'scenery', 'add', currentScene.value.id);
  if (orphans.length > 0) {
    const ok = await confirm(buildOrphanMessage(orphans), {
      title: 'Crew assignments will be removed',
      okTitle: 'Continue',
      okVariant: 'warning',
    });
    if (!ok) return;
  }
  try {
    await stageStore.addSceneryAllocation({
      scenery_id: sceneryId,
      scene_id: currentScene.value.id,
    });
    addSceneryModal.value?.hide();
  } catch (e) {
    log.error('Error adding scenery allocation:', e);
  }
}

async function onSubmitAddProp(): Promise<void> {
  const valid = await vAddProp$.value.$validate();
  if (!valid || !currentScene.value) return;
  const propsId = addPropForm.value.props_id!;
  const orphans = findOrphansForItem(propsId, 'prop', 'add', currentScene.value.id);
  if (orphans.length > 0) {
    const ok = await confirm(buildOrphanMessage(orphans), {
      title: 'Crew assignments will be removed',
      okTitle: 'Continue',
      okVariant: 'warning',
    });
    if (!ok) return;
  }
  try {
    await stageStore.addPropsAllocation({ props_id: propsId, scene_id: currentScene.value.id });
    addPropModal.value?.hide();
  } catch (e) {
    log.error('Error adding prop allocation:', e);
  }
}

async function deleteSceneryAllocation(allocation: SceneryAllocation): Promise<void> {
  const orphans = findOrphansForItem(
    allocation.scenery_id,
    'scenery',
    'remove',
    currentScene.value!.id
  );
  const sceneryName = stageStore.sceneryById(allocation.scenery_id)?.name ?? 'Unknown';
  if (orphans.length > 0) {
    const ok = await confirm(buildOrphanMessage(orphans), {
      title: 'Crew assignments will be removed',
      okTitle: 'Continue',
      okVariant: 'danger',
    });
    if (!ok) return;
  } else {
    const ok = await confirm(`Remove "${sceneryName}" from this scene?`, {
      okVariant: 'danger',
      okTitle: 'Remove',
    });
    if (!ok) return;
  }
  try {
    await stageStore.deleteSceneryAllocation(allocation.id);
  } catch (e) {
    log.error('Error deleting scenery allocation:', e);
  }
}

async function deletePropAllocation(allocation: PropsAllocation): Promise<void> {
  const orphans = findOrphansForItem(allocation.props_id, 'prop', 'remove', currentScene.value!.id);
  const propName = stageStore.propById(allocation.props_id)?.name ?? 'Unknown';
  if (orphans.length > 0) {
    const ok = await confirm(buildOrphanMessage(orphans), {
      title: 'Crew assignments will be removed',
      okTitle: 'Continue',
      okVariant: 'danger',
    });
    if (!ok) return;
  } else {
    const ok = await confirm(`Remove "${propName}" from this scene?`, {
      okVariant: 'danger',
      okTitle: 'Remove',
    });
    if (!ok) return;
  }
  try {
    await stageStore.deletePropsAllocation(allocation.id);
  } catch (e) {
    log.error('Error deleting prop allocation:', e);
  }
}

async function addCrewAssignment(
  itemId: number,
  itemType: string,
  assignmentType: string
): Promise<void> {
  const key = crewSelectionKey(itemId, itemType, assignmentType);
  const crewId = newCrewSelections.value[key];
  if (!crewId || !currentScene.value || savingAssignment.value) return;
  savingAssignment.value = true;
  try {
    const assignment: Record<string, unknown> = {
      crew_id: crewId,
      scene_id: currentScene.value.id,
      assignment_type: assignmentType,
    };
    if (itemType === 'prop') {
      assignment.prop_id = itemId;
    } else {
      assignment.scenery_id = itemId;
    }
    const success = await stageStore.addCrewAssignment(assignment);
    if (success) newCrewSelections.value[key] = null;
  } finally {
    savingAssignment.value = false;
  }
}

async function removeCrewAssignment(assignment: CrewAssignment): Promise<void> {
  if (savingAssignment.value) return;
  const crewName = formatCrewName(stageStore.crewById(assignment.crew_id));
  const ok = await confirm(
    `Remove ${crewName} from this ${assignment.assignment_type.toUpperCase()} assignment?`,
    { okTitle: 'Remove', okVariant: 'danger' }
  );
  if (!ok) return;
  savingAssignment.value = true;
  try {
    await stageStore.deleteCrewAssignment(assignment.id);
  } catch (e) {
    log.error('Error removing crew assignment:', e);
  } finally {
    savingAssignment.value = false;
  }
}

onMounted(async () => {
  window.addEventListener('resize', calculateNavbarHeight);
  await Promise.all([
    showStore.getActList(),
    showStore.getSceneList(),
    stageStore.getSceneryTypes(),
    stageStore.getSceneryList(),
    stageStore.getSceneryAllocations(),
    stageStore.getPropTypes(),
    stageStore.getPropsList(),
    stageStore.getPropsAllocations(),
    stageStore.getCrewList(),
    stageStore.getCrewAssignments(),
  ]);
  loaded.value = true;
  calculateNavbarHeight();
});

onUnmounted(() => {
  window.removeEventListener('resize', calculateNavbarHeight);
});
</script>

<style scoped>
.stage-manager-container {
  position: relative;
}

.sticky-header {
  position: sticky;
  z-index: 100;
  padding: 10px 0;
  border-bottom: 1px solid #dee2e6;
  background: var(--body-background);
}

.section-card-header {
  cursor: pointer;
  padding: 0.5rem 0.75rem;
  font-size: 0.9rem;
  font-weight: 600;
}

.crew-card-body {
  padding: 0.75rem;
}

.boundary-items-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 0.5rem;
}

.boundary-item {
  padding: 0.5rem 0.65rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

.boundary-item-header {
  margin-bottom: 0.25rem;
  font-weight: 600;
  font-size: 0.85rem;
}

.assignment-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-bottom: 0.25rem;
}

.crew-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.05);
  font-size: 0.8rem;
}

.add-crew-container {
  display: flex;
  gap: 0.4rem;
  align-items: center;
}

.add-crew-select {
  flex: 1;
}
</style>
