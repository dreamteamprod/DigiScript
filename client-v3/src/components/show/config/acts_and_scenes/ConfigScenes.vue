<template>
  <BContainer v-if="!loading" class="mx-0" fluid>
    <BRow>
      <BCol cols="8">
        <BTable
          id="scene-table"
          :items="sceneTableItems"
          :fields="sceneFields"
          :per-page="rowsPerPage"
          :current-page="currentPage"
          show-empty
        >
          <template #head(btn)>
            <BButton v-if="systemStore.isShowEditor" v-b-modal.new-scene variant="outline-success">
              New Scene
            </BButton>
          </template>
          <template #cell(act)="data">
            {{ showStore.actById(data.item.act)?.name }}
          </template>
          <template #cell(next_scene)="data">
            <span v-if="data.item.next_scene">{{
              showStore.sceneById(data.item.next_scene)?.name
            }}</span>
            <span v-else>N/A</span>
          </template>
          <template #cell(previous_scene)="data">
            <span v-if="data.item.previous_scene">{{
              showStore.sceneById(data.item.previous_scene)?.name
            }}</span>
            <span v-else>N/A</span>
          </template>
          <template #cell(btn)="data">
            <BButtonGroup v-if="systemStore.isShowEditor">
              <BButton
                variant="warning"
                :disabled="submittingEditScene || deletingScene"
                @click="openEditForm(data.item)"
              >
                Edit
              </BButton>
              <BButton
                variant="danger"
                :disabled="submittingEditScene || deletingScene"
                @click="deleteScene(data.item)"
              >
                Delete
              </BButton>
            </BButtonGroup>
          </template>
        </BTable>
        <BPagination
          v-show="sceneTableItems.length > rowsPerPage"
          v-model="currentPage"
          :total-rows="sceneTableItems.length"
          :per-page="rowsPerPage"
          aria-controls="scene-table"
          class="justify-content-center"
        />
      </BCol>
      <BCol cols="4">
        <BTable
          id="first-scenes-table"
          :items="showStore.actList"
          :fields="firstSceneFields"
          show-empty
        >
          <template #cell(first_scene)="data">
            <span v-if="data.item.first_scene">{{
              showStore.sceneById(data.item.first_scene)?.name
            }}</span>
            <span v-else>N/A</span>
          </template>
          <template #cell(btn)="data">
            <BButtonGroup v-if="systemStore.isShowEditor">
              <BButton
                variant="success"
                :disabled="submittingFirstScene"
                @click="openFirstSceneEdit(data.item)"
              >
                Set
              </BButton>
            </BButtonGroup>
          </template>
        </BTable>
      </BCol>
    </BRow>

    <BModal
      id="new-scene"
      ref="newSceneModal"
      title="Add New Scene"
      size="md"
      :ok-disabled="newV$.newFormState.$invalid || submittingNewScene"
      @show="resetNewForm"
      @hide="resetNewForm"
      @ok="onSubmitNew"
    >
      <BForm @submit.stop.prevent="onSubmitNew">
        <BFormGroup label="Name" label-for="new-name-input" label-cols="4">
          <BFormInput
            id="new-name-input"
            v-model="newFormState.name"
            :state="newFieldState('name')"
          />
          <BFormInvalidFeedback>This is a required field.</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Act" label-for="new-act-input" label-cols="4">
          <BFormSelect
            id="new-act-input"
            v-model="newFormState.act_id"
            :options="actOptions"
            :state="newFieldState('act_id')"
          />
          <BFormInvalidFeedback>This is a required field.</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Previous Scene" label-for="new-previous-scene-input" label-cols="4">
          <BFormSelect
            id="new-previous-scene-input"
            v-model="newFormState.previous_scene_id"
            :options="previousSceneOptions[newFormState.act_id ?? 'null']"
          />
        </BFormGroup>
      </BForm>
    </BModal>

    <BModal
      id="edit-scene"
      ref="editSceneModal"
      title="Edit Scene"
      size="md"
      :ok-disabled="editV$.editFormState.$invalid || submittingEditScene"
      @hide="resetEditForm"
      @ok="onSubmitEdit"
    >
      <BForm @submit.stop.prevent="onSubmitEdit">
        <BFormGroup label="Name" label-for="edit-name-input" label-cols="4">
          <BFormInput
            id="edit-name-input"
            v-model="editFormState.name"
            :state="editFieldState('name')"
          />
          <BFormInvalidFeedback>This is a required field.</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Act" label-for="edit-act-input" label-cols="4">
          <BFormSelect
            id="edit-act-input"
            v-model="editFormState.act_id"
            :options="actOptions"
            :state="editFieldState('act_id')"
            @update:model-value="editActChanged"
          />
          <BFormInvalidFeedback>This is a required field.</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Previous Scene" label-for="edit-previous-scene-input" label-cols="4">
          <BFormSelect
            id="edit-previous-scene-input"
            v-model="editFormState.previous_scene_id"
            :options="editFormPrevScenes"
            :state="editFieldState('previous_scene_id')"
          />
          <BFormInvalidFeedback
            >This cannot form a circular dependency between scenes.</BFormInvalidFeedback
          >
        </BFormGroup>
      </BForm>
    </BModal>

    <BModal
      id="set-first-scene"
      ref="firstSceneModal"
      title="Set First Scene"
      size="md"
      :ok-disabled="submittingFirstScene"
      @hide="resetFirstSceneForm"
      @ok="onSubmitFirstScene"
    >
      <BForm @submit.stop.prevent="onSubmitFirstScene">
        <BFormGroup :label="firstSceneModalLabel" label-for="first-scene-input" label-cols="4">
          <BFormSelect
            id="first-scene-input"
            v-model="firstSceneFormState.scene_id"
            :options="firstSceneOptions[firstSceneFormState.act_id ?? -1]"
          />
        </BFormGroup>
      </BForm>
    </BModal>
  </BContainer>
  <div v-else class="text-center py-5">
    <BSpinner label="Loading" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useVuelidate } from '@vuelidate/core';
import { required, helpers } from '@vuelidate/validators';
import { BModal } from 'bootstrap-vue-next';
import log from 'loglevel';
import { useSystemStore } from '@/stores/system';
import { useShowStore } from '@/stores/show';
import { useConfirm } from '@/composables/useConfirm';
import type { Scene } from '@/types/api/show';

const systemStore = useSystemStore();
const showStore = useShowStore();
const { confirm } = useConfirm();

const loading = ref(true);
const rowsPerPage = 15;
const currentPage = ref(1);
const submittingNewScene = ref(false);
const submittingEditScene = ref(false);
const submittingFirstScene = ref(false);
const deletingScene = ref(false);
const editSceneOriginalId = ref<number | null>(null);

const newSceneModal = ref<InstanceType<typeof BModal>>();
const editSceneModal = ref<InstanceType<typeof BModal>>();
const firstSceneModal = ref<InstanceType<typeof BModal>>();

const sceneFields = [
  'name',
  'act',
  { key: 'previous_scene', label: 'Previous Scene' },
  { key: 'next_scene', label: 'Next Scene' },
  { key: 'btn', label: '' },
];
const firstSceneFields = [
  { key: 'name', label: 'Act' },
  { key: 'first_scene', label: 'First Scene' },
  { key: 'btn', label: '' },
];

interface NewSceneForm {
  name: string;
  act_id: number | null;
  previous_scene_id: number | null;
}

interface EditSceneForm {
  scene_id: number | null;
  name: string;
  act_id: number | null;
  previous_scene_id: number | null;
}

interface FirstSceneForm {
  act_id: number | null;
  scene_id: number | null;
}

const newFormState = ref<NewSceneForm>({ name: '', act_id: null, previous_scene_id: null });
const editFormState = ref<EditSceneForm>({
  scene_id: null,
  name: '',
  act_id: null,
  previous_scene_id: null,
});
const firstSceneFormState = ref<FirstSceneForm>({ act_id: null, scene_id: null });

const notNullAndGreaterThanZero = helpers.withMessage(
  'This is a required field',
  (val: number | null) => val != null && val > 0
);

const noSceneLoops = helpers.withMessage(
  'This cannot form a circular dependency between scenes',
  (value: number | null) => {
    if (value == null) return true;
    const visited = new Set<number>();
    visited.add(editFormState.value.scene_id ?? -1);
    let current = showStore.sceneById(value);
    while (current != null && current.previous_scene != null) {
      if (visited.has(current.previous_scene)) return false;
      current = showStore.sceneById(current.previous_scene);
    }
    return true;
  }
);

const newRules = {
  newFormState: {
    name: { required },
    act_id: { notNullAndGreaterThanZero },
  },
};
const editRules = {
  editFormState: {
    name: { required },
    act_id: { notNullAndGreaterThanZero },
    previous_scene_id: { noSceneLoops },
  },
};

const newV$ = useVuelidate(newRules, { newFormState });
const editV$ = useVuelidate(editRules, { editFormState });

function getActOrder(): number[] {
  const show = systemStore.currentShow;
  const actOrder: number[] = [];
  if (show?.first_act_id != null && showStore.actList.length > 0) {
    let act = showStore.actById(show.first_act_id);
    while (act != null) {
      actOrder.push(act.id);
      act = showStore.actById(act.next_act);
    }
  }
  for (const act of showStore.actList) {
    if (!actOrder.includes(act.id)) actOrder.push(act.id);
  }
  return actOrder;
}

function getScenesForAct(actId: number, alreadyLinked: Set<number>): Scene[] {
  const scenes: Scene[] = [];
  const act = showStore.actById(actId);
  if (act?.first_scene != null) {
    let scene = showStore.sceneById(act.first_scene);
    while (scene != null) {
      scenes.push(scene);
      scene = showStore.sceneById(scene.next_scene);
    }
  }
  for (const scene of showStore.sceneList.filter((s) => s.act === actId)) {
    if (!alreadyLinked.has(scene.id)) scenes.push(scene);
  }
  return scenes;
}

const sceneTableItems = computed((): Scene[] => {
  const ret: Scene[] = [];
  for (const actId of getActOrder()) {
    const linked = new Set(ret.map((s) => s.id));
    ret.push(...getScenesForAct(actId, linked));
  }
  return ret;
});

const actOptions = computed(() => [
  { value: null, text: 'Please select an option', disabled: true },
  ...showStore.actList.map((act) => ({ value: act.id, text: act.name })),
]);

const previousSceneOptions = computed(
  (): Record<string | number, { value: number | null; text: string }[]> => {
    const ret: Record<string | number, { value: number | null; text: string }[]> = {
      null: [{ value: null, text: 'None' }],
    };
    for (const act of showStore.actList) {
      ret[act.id] = [
        { value: null, text: 'None' },
        ...showStore.sceneList
          .filter((scene) => scene.act === act.id && scene.next_scene == null)
          .map((scene) => ({
            value: scene.id,
            text: `${showStore.actById(scene.act)?.name ?? ''}: ${scene.name ?? ''}`,
          })),
      ];
    }
    return ret;
  }
);

const editFormPrevScenes = computed(() => {
  const actId = editFormState.value.act_id;
  const base = (
    previousSceneOptions.value[actId ?? 'null'] ?? [{ value: null, text: 'None' }]
  ).filter((opt) => opt.value !== editFormState.value.scene_id);
  if (
    editFormState.value.previous_scene_id != null &&
    !base.find((o) => o.value === editFormState.value.previous_scene_id)
  ) {
    const scene = showStore.sceneById(editFormState.value.previous_scene_id);
    if (scene) {
      base.push({
        value: scene.id,
        text: `${showStore.actById(scene.act)?.name ?? ''}: ${scene.name ?? ''}`,
      });
    }
  }
  return base;
});

const firstSceneOptions = computed((): Record<number, { value: number | null; text: string }[]> => {
  const ret: Record<number, { value: number | null; text: string }[]> = {};
  for (const act of showStore.actList) {
    ret[act.id] = [
      { value: null, text: 'None' },
      ...showStore.sceneList
        .filter((scene) => scene.act === act.id && scene.previous_scene == null)
        .map((scene) => ({
          value: scene.id,
          text: `${act.name ?? ''}: ${scene.name ?? ''}`,
        })),
    ];
  }
  return ret;
});

const firstSceneModalLabel = computed(() => {
  if (firstSceneFormState.value.act_id == null) return '';
  const act = showStore.actById(firstSceneFormState.value.act_id);
  return `${act?.name ?? ''} First Scene`;
});

function newFieldState(key: keyof NewSceneForm): boolean | null {
  const field = newV$.value.newFormState[key];
  if (!field) return null;
  return field.$dirty ? !field.$error : null;
}

function editFieldState(key: keyof EditSceneForm): boolean | null {
  const field = editV$.value.editFormState[key];
  if (!field) return null;
  return field.$dirty ? !field.$error : null;
}

function resetNewForm(): void {
  newFormState.value = { name: '', act_id: null, previous_scene_id: null };
  submittingNewScene.value = false;
  newV$.value.$reset();
}

function resetEditForm(): void {
  editSceneOriginalId.value = null;
  editFormState.value = { scene_id: null, name: '', act_id: null, previous_scene_id: null };
  submittingEditScene.value = false;
  deletingScene.value = false;
  editV$.value.$reset();
}

function resetFirstSceneForm(): void {
  firstSceneFormState.value = { act_id: null, scene_id: null };
  submittingFirstScene.value = false;
}

function openEditForm(scene: Scene): void {
  editSceneOriginalId.value = scene.id;
  editFormState.value.scene_id = scene.id;
  editFormState.value.name = scene.name ?? '';
  editFormState.value.act_id = scene.act;
  editFormState.value.previous_scene_id = scene.previous_scene ?? null;
  editSceneModal.value?.show();
}

function openFirstSceneEdit(act: { id: number; first_scene: number | null }): void {
  firstSceneFormState.value.act_id = act.id;
  firstSceneFormState.value.scene_id = act.first_scene ?? null;
  firstSceneModal.value?.show();
}

function editActChanged(newActId: number | null): void {
  const originalScene =
    editSceneOriginalId.value != null ? showStore.sceneById(editSceneOriginalId.value) : null;
  if (newActId !== originalScene?.act) {
    editFormState.value.previous_scene_id = null;
  } else {
    editFormState.value.previous_scene_id = originalScene?.previous_scene ?? null;
  }
}

async function onSubmitNew(event: Event): Promise<void> {
  newV$.value.newFormState.$touch();
  if (newV$.value.newFormState.$invalid || submittingNewScene.value) {
    event.preventDefault();
    return;
  }
  submittingNewScene.value = true;
  try {
    await showStore.addScene(newFormState.value);
    newSceneModal.value?.hide();
    resetNewForm();
  } catch (error) {
    log.error('Error submitting new scene:', error);
    event.preventDefault();
  } finally {
    submittingNewScene.value = false;
  }
}

async function onSubmitEdit(event: Event): Promise<void> {
  editV$.value.editFormState.$touch();
  if (editV$.value.editFormState.$invalid || submittingEditScene.value) {
    event.preventDefault();
    return;
  }
  submittingEditScene.value = true;
  try {
    await showStore.updateScene(editFormState.value);
    editSceneModal.value?.hide();
    resetEditForm();
  } catch (error) {
    log.error('Error submitting edit scene:', error);
    event.preventDefault();
  } finally {
    submittingEditScene.value = false;
  }
}

async function onSubmitFirstScene(event: Event): Promise<void> {
  if (submittingFirstScene.value) {
    event.preventDefault();
    return;
  }
  submittingFirstScene.value = true;
  try {
    await showStore.setActFirstScene(firstSceneFormState.value);
    firstSceneModal.value?.hide();
    resetFirstSceneForm();
  } catch (error) {
    log.error('Error submitting first scene:', error);
    event.preventDefault();
  } finally {
    submittingFirstScene.value = false;
  }
}

async function deleteScene(scene: Scene): Promise<void> {
  if (deletingScene.value) return;
  const ok = await confirm(`Are you sure you want to delete ${scene.name}?`);
  if (ok) {
    deletingScene.value = true;
    try {
      await showStore.deleteScene(scene.id);
    } catch (error) {
      log.error('Error deleting scene:', error);
    } finally {
      deletingScene.value = false;
    }
  }
}

onMounted(async () => {
  await showStore.getSceneList();
  await showStore.getActList();
  loading.value = false;
});
</script>
