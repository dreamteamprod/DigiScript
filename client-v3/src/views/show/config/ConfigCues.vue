<template>
  <BContainer class="mx-0" fluid>
    <BRow>
      <BCol>
        <BTabs content-class="mt-3">
          <BTab title="Cue Types" active>
            <BTable
              id="cue-types-table"
              :items="showStore.cueTypes"
              :fields="cueTypeFields"
              :per-page="rowsPerPage"
              :current-page="currentPage"
              show-empty
            >
              <template #head(btn)>
                <template v-if="systemStore.isCueEditor">
                  <BButton v-b-modal.new-cue-type variant="outline-success"> New Cue Type </BButton>
                  <BButton variant="outline-info" class="ms-2" @click="openImportModal">
                    Import Cue Type
                  </BButton>
                </template>
              </template>
              <template #cell(colour)="data">
                <span
                  :style="{
                    background: data.item.colour,
                    width: '20px',
                    height: '20px',
                    display: 'inline-block',
                    borderRadius: '2px',
                  }"
                />
              </template>
              <template #cell(btn)="data">
                <BButtonGroup v-if="systemStore.isCueEditor">
                  <BButton
                    variant="warning"
                    :disabled="submittingNewCueType || submittingEditCueType || deletingCueType"
                    @click="openEditForm(data.item)"
                  >
                    Edit
                  </BButton>
                  <BButton
                    variant="danger"
                    :disabled="submittingNewCueType || submittingEditCueType || deletingCueType"
                    @click="deleteCueType(data.item)"
                  >
                    Delete
                  </BButton>
                </BButtonGroup>
              </template>
            </BTable>
            <BPagination
              v-show="showStore.cueTypes.length > rowsPerPage"
              v-model="currentPage"
              :total-rows="showStore.cueTypes.length"
              :per-page="rowsPerPage"
              aria-controls="cue-types-table"
              class="justify-content-center"
            />
          </BTab>
          <BTab title="Cue Configuration">
            <CueEditor />
          </BTab>
          <BTab title="Cue Counts">
            <CueCountStats />
          </BTab>
        </BTabs>
      </BCol>
    </BRow>

    <BModal
      id="new-cue-type"
      ref="newCueTypeModal"
      title="Add Cue Type"
      size="md"
      :ok-disabled="newV$.newFormState.$invalid || submittingNewCueType"
      @show="resetNewForm"
      @hide="resetNewForm"
      @ok="onSubmitNew"
    >
      <BForm @submit.stop.prevent="onSubmitNew">
        <BFormGroup label="Prefix" label-for="new-prefix-input" label-cols="4">
          <BFormInput
            id="new-prefix-input"
            v-model="newFormState.prefix"
            :state="newFieldState('prefix')"
          />
          <BFormInvalidFeedback>
            This is a required field and must be 5 characters or less.
          </BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Description" label-for="new-description-input" label-cols="4">
          <BFormInput id="new-description-input" v-model="newFormState.description" />
        </BFormGroup>
        <BFormGroup label="Colour" label-for="new-colour-input" label-cols="4">
          <div class="d-flex align-items-center gap-2">
            <BFormInput
              id="new-colour-input"
              v-model="newFormState.colour"
              type="color"
              style="width: 60px"
              :state="newFieldState('colour')"
            />
            <span
              class="ms-2 px-2 py-1 rounded"
              :style="{ background: newFormState.colour, color: '#fff', fontSize: '0.85em' }"
            >
              Preview
            </span>
          </div>
          <BFormInvalidFeedback>This is a required field.</BFormInvalidFeedback>
        </BFormGroup>
      </BForm>
    </BModal>

    <BModal
      id="edit-cue-type"
      ref="editCueTypeModal"
      title="Edit Cue Type"
      size="md"
      :ok-disabled="editV$.editFormState.$invalid || submittingEditCueType"
      @hide="resetEditForm"
      @ok="onSubmitEdit"
    >
      <BForm @submit.stop.prevent="onSubmitEdit">
        <BFormGroup label="Prefix" label-for="edit-prefix-input" label-cols="4">
          <BFormInput
            id="edit-prefix-input"
            v-model="editFormState.prefix"
            :state="editFieldState('prefix')"
          />
          <BFormInvalidFeedback>
            This is a required field and must be 5 characters or less.
          </BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Description" label-for="edit-description-input" label-cols="4">
          <BFormInput id="edit-description-input" v-model="editFormState.description" />
        </BFormGroup>
        <BFormGroup label="Colour" label-for="edit-colour-input" label-cols="4">
          <div class="d-flex align-items-center gap-2">
            <BFormInput
              id="edit-colour-input"
              v-model="editFormState.colour"
              type="color"
              style="width: 60px"
              :state="editFieldState('colour')"
            />
            <span
              class="ms-2 px-2 py-1 rounded"
              :style="{ background: editFormState.colour, color: '#fff', fontSize: '0.85em' }"
            >
              Preview
            </span>
          </div>
          <BFormInvalidFeedback>This is a required field.</BFormInvalidFeedback>
        </BFormGroup>
      </BForm>
    </BModal>

    <BModal
      id="import-cue-type-modal"
      ref="importCueTypeModal"
      title="Import Cue Type"
      size="xl"
      hide-footer
      @hide="resetImportState"
    >
      <div v-if="isLoadingImport" class="text-center">
        <BSpinner />
      </div>
      <div v-else-if="importGroups.length === 0">
        <p class="text-muted">No cue types available to import from other shows.</p>
      </div>
      <div v-else>
        <BCard v-for="show in importGroups" :key="show.id" no-body class="mb-2">
          <BCardHeader style="cursor: pointer" @click="toggleImportShow(show.id)">
            <div class="d-flex justify-content-between align-items-center">
              <span>{{ show.name }}</span>
              <IMdiChevronUp v-if="isExpanded[show.id]" /><IMdiChevronDown v-else />
            </div>
          </BCardHeader>
          <BCollapse :model-value="isExpanded[show.id]">
            <BTable :items="show.cue_types" :fields="importCueTypeFields" small>
              <template #cell(colour)="data">
                <span
                  :style="{
                    background: data.item.colour,
                    width: '20px',
                    height: '20px',
                    display: 'inline-block',
                    borderRadius: '2px',
                  }"
                />
              </template>
              <template #cell(action)="data">
                <BButton
                  variant="outline-success"
                  size="sm"
                  :disabled="!!isImporting[data.item.id]"
                  @click="importCueType(data.item)"
                >
                  <BSpinner v-if="isImporting[data.item.id]" small />
                  <span v-else>Import</span>
                </BButton>
              </template>
            </BTable>
          </BCollapse>
        </BCard>
      </div>
    </BModal>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useVuelidate } from '@vuelidate/core';
import { required, maxLength } from '@vuelidate/validators';
import { BModal } from 'bootstrap-vue-next';
import log from 'loglevel';
import { useSystemStore } from '@/stores/system';
import { useShowStore } from '@/stores/show';
import { useConfirm } from '@/composables/useConfirm';
import CueCountStats from '@/components/show/config/cues/CueCountStats.vue';
import CueEditor from '@/components/show/config/cues/CueEditor.vue';
import type { CueType } from '@/types/api/cues';

const systemStore = useSystemStore();
const showStore = useShowStore();
const { confirm } = useConfirm();

const rowsPerPage = 15;
const currentPage = ref(1);
const submittingNewCueType = ref(false);
const submittingEditCueType = ref(false);
const deletingCueType = ref(false);

const newCueTypeModal = ref<InstanceType<typeof BModal>>();
const editCueTypeModal = ref<InstanceType<typeof BModal>>();
const importCueTypeModal = ref<InstanceType<typeof BModal>>();

const cueTypeFields = ['prefix', 'description', 'colour', { key: 'btn', label: '' }];
const importCueTypeFields = [
  { key: 'prefix', label: 'Prefix' },
  { key: 'description', label: 'Description' },
  { key: 'colour', label: 'Colour' },
  { key: 'action', label: '' },
];

interface CueTypeForm {
  prefix: string;
  description: string;
  colour: string;
}

interface EditCueTypeForm extends CueTypeForm {
  id: number | null;
}

const newFormState = ref<CueTypeForm>({ prefix: '', description: '', colour: '#000000' });
const editFormState = ref<EditCueTypeForm>({
  id: null,
  prefix: '',
  description: '',
  colour: '#000000',
});

const newRules = {
  newFormState: { prefix: { required, maxLength: maxLength(5) }, colour: { required } },
};
const editRules = {
  editFormState: { prefix: { required, maxLength: maxLength(5) }, colour: { required } },
};

const newV$ = useVuelidate(newRules, { newFormState });
const editV$ = useVuelidate(editRules, { editFormState });

const importGroups = ref<{ id: number; name: string; cue_types: CueType[] }[]>([]);
const isExpanded = ref<Record<number, boolean>>({});
const isImporting = ref<Record<number, boolean>>({});
const isLoadingImport = ref(false);

function newFieldState(key: keyof CueTypeForm): boolean | null {
  const field = newV$.value.newFormState[key];
  if (!field) return null;
  return field.$dirty ? !field.$error : null;
}

function editFieldState(key: keyof EditCueTypeForm): boolean | null {
  const field = editV$.value.editFormState[key];
  if (!field) return null;
  return field.$dirty ? !field.$error : null;
}

function resetNewForm(): void {
  newFormState.value = { prefix: '', description: '', colour: '#000000' };
  submittingNewCueType.value = false;
  newV$.value.$reset();
}

function resetEditForm(): void {
  editFormState.value = { id: null, prefix: '', description: '', colour: '#000000' };
  submittingEditCueType.value = false;
  editV$.value.$reset();
}

function openEditForm(cueType: CueType): void {
  editFormState.value.id = cueType.id;
  editFormState.value.prefix = cueType.prefix ?? '';
  editFormState.value.description = cueType.description ?? '';
  editFormState.value.colour = cueType.colour ?? '#000000';
  editCueTypeModal.value?.show();
}

async function onSubmitNew(event: Event): Promise<void> {
  newV$.value.newFormState.$touch();
  if (newV$.value.newFormState.$invalid || submittingNewCueType.value) {
    event.preventDefault();
    return;
  }
  submittingNewCueType.value = true;
  try {
    await showStore.addCueType(newFormState.value);
    newCueTypeModal.value?.hide();
    resetNewForm();
  } catch (error) {
    log.error('Error submitting new cue type:', error);
    event.preventDefault();
  } finally {
    submittingNewCueType.value = false;
  }
}

async function onSubmitEdit(event: Event): Promise<void> {
  editV$.value.editFormState.$touch();
  if (editV$.value.editFormState.$invalid || submittingEditCueType.value) {
    event.preventDefault();
    return;
  }
  submittingEditCueType.value = true;
  try {
    await showStore.updateCueType(editFormState.value);
    editCueTypeModal.value?.hide();
    resetEditForm();
  } catch (error) {
    log.error('Error submitting edit cue type:', error);
    event.preventDefault();
  } finally {
    submittingEditCueType.value = false;
  }
}

async function deleteCueType(cueType: CueType): Promise<void> {
  if (deletingCueType.value) return;
  const ok = await confirm(`Are you sure you want to delete ${cueType.prefix}?`);
  if (ok) {
    deletingCueType.value = true;
    try {
      await showStore.deleteCueType(cueType.id);
    } catch (error) {
      log.error('Error deleting cue type:', error);
    } finally {
      deletingCueType.value = false;
    }
  }
}

async function openImportModal(): Promise<void> {
  importCueTypeModal.value?.show();
  isLoadingImport.value = true;
  try {
    const data = (await showStore.getImportableCueTypes()) as {
      cue_type_groups: { id: number; name: string; cue_types: CueType[] }[];
    };
    importGroups.value = data.cue_type_groups;
    data.cue_type_groups.forEach((show) => {
      isExpanded.value[show.id] = true;
    });
  } catch (e) {
    log.error('Error loading importable cue types:', e);
  } finally {
    isLoadingImport.value = false;
  }
}

function toggleImportShow(showId: number): void {
  isExpanded.value[showId] = !isExpanded.value[showId];
}

async function importCueType(cueType: CueType): Promise<void> {
  isImporting.value[cueType.id] = true;
  try {
    await showStore.addCueType({
      prefix: cueType.prefix,
      description: cueType.description,
      colour: cueType.colour,
    });
  } catch (error) {
    log.error('Error importing cue type:', error);
  } finally {
    isImporting.value[cueType.id] = false;
  }
}

function resetImportState(): void {
  importGroups.value = [];
  isExpanded.value = {};
  isLoadingImport.value = false;
  isImporting.value = {};
}

onMounted(async () => {
  await showStore.getCueTypes();
});
</script>
