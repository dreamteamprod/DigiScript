<template>
  <div>
    <BCard class="mb-3" :class="{ 'collapsed-card': !graphCollapsed }" header-tag="header">
      <template #header>
        <div class="d-flex justify-content-between align-items-center">
          <h6 class="mb-0">Revision Branch Graph</h6>
          <BButton size="sm" variant="secondary" @click="graphCollapsed = !graphCollapsed">
            <svg
              v-if="!graphCollapsed"
              xmlns="http://www.w3.org/2000/svg"
              width="1em"
              height="1em"
              fill="currentColor"
              viewBox="0 0 16 16"
            >
              <path
                fill-rule="evenodd"
                d="M7.646 4.646a.5.5 0 0 1 .708 0l6 6a.5.5 0 0 1-.708.708L8 5.707l-5.646 5.647a.5.5 0 0 1-.708-.708l6-6z"
              />
            </svg>
            <svg
              v-else
              xmlns="http://www.w3.org/2000/svg"
              width="1em"
              height="1em"
              fill="currentColor"
              viewBox="0 0 16 16"
            >
              <path
                fill-rule="evenodd"
                d="M1.646 4.646a.5.5 0 0 1 .708 0L8 10.293l5.646-5.647a.5.5 0 0 1 .708.708l-6 6a.5.5 0 0 1-.708 0l-6-6a.5.5 0 0 1 0-.708z"
              />
            </svg>
          </BButton>
        </div>
      </template>
      <BCollapse v-model="graphCollapsed">
        <RevisionGraph
          :revisions="showStore.scriptRevisions"
          :current-revision-id="showStore.currentRevision"
          :selected-revision-id="selectedRevisionId"
          @node-click="handleNodeClick"
        />
      </BCollapse>
    </BCard>

    <BTable :items="showStore.scriptRevisions" :fields="revisionColumns" show-empty>
      <template #cell(current)="data">
        <svg
          v-if="data.item.id === showStore.currentRevision"
          xmlns="http://www.w3.org/2000/svg"
          width="1em"
          height="1em"
          fill="#06BC8C"
          viewBox="0 0 16 16"
        >
          <path
            d="M2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2zm10.03 4.97a.75.75 0 0 1 .011 1.05l-3.992 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425a.75.75 0 0 1 1.079-.022z"
          />
        </svg>
        <BButton
          v-else-if="systemStore.isScriptEditor"
          variant="warning"
          :disabled="
            !canChangeRevisions ||
            submittingLoadRevision ||
            submittingNewRevision ||
            deletingRevision
          "
          @click="loadRevision(data.item)"
        >
          Load
        </BButton>
      </template>
      <template #cell(previous_revision_id)="data">
        <span v-if="data.item.previous_revision_id != null">
          {{
            showStore.scriptRevisions.find((r) => r.id === data.item.previous_revision_id)
              ?.revision ?? 'N/A'
          }}
        </span>
        <span v-else>N/A</span>
      </template>
      <template #cell(btn)="data">
        <BButtonGroup v-if="systemStore.isScriptEditor && data.item.revision !== 1">
          <BButton
            variant="warning"
            :disabled="
              !canChangeRevisions ||
              submittingLoadRevision ||
              submittingNewRevision ||
              deletingRevision
            "
            @click="handleModalCreateFrom(data.item)"
          >
            Edit
          </BButton>
          <BButton
            variant="danger"
            :disabled="
              !canChangeRevisions ||
              submittingLoadRevision ||
              submittingNewRevision ||
              deletingRevision
            "
            @click="deleteRevision(data.item)"
          >
            Delete
          </BButton>
        </BButtonGroup>
      </template>
      <template #custom-foot>
        <BTr>
          <BTd>
            <BButton
              v-if="systemStore.isScriptEditor"
              variant="outline-success"
              :disabled="
                !canChangeRevisions ||
                submittingLoadRevision ||
                submittingNewRevision ||
                deletingRevision
              "
              @click="newRevisionModal?.show()"
            >
              New Revision
            </BButton>
          </BTd>
          <BTd /><BTd /><BTd /><BTd /><BTd /><BTd />
        </BTr>
      </template>
    </BTable>

    <BModal
      ref="newRevisionModal"
      title="Add New Revision"
      :ok-disabled="vNew$.description.$invalid || submittingNewRevision"
      @show="resetNewRevForm"
      @hidden="resetNewRevForm"
      @ok.prevent="onSubmitNewRev"
    >
      <BAlert variant="info" :model-value="true">
        This will create a new revision of the script based on the current revision, and set it as
        the new current revision.
      </BAlert>
      <BForm @submit.stop.prevent="onSubmitNewRev">
        <BFormGroup label="Description" label-for="new-rev-description">
          <BFormInput
            id="new-rev-description"
            v-model="newRevForm.description"
            :state="validationState(vNew$.description)"
          />
          <BFormInvalidFeedback>{{ vNew$.description.$errors[0]?.$message }}</BFormInvalidFeedback>
        </BFormGroup>
      </BForm>
    </BModal>

    <RevisionDetailModal
      ref="revisionDetailModal"
      :revision="selectedRevision"
      :revisions="showStore.scriptRevisions"
      :current-revision-id="showStore.currentRevision"
      :can-edit="systemStore.isScriptEditor && canChangeRevisions"
      :submitting="modalSubmitting"
      @load-revision="handleModalLoadRevision"
      @create-from="handleModalCreateFrom"
      @close="revisionDetailModal?.hide()"
      @hidden="handleModalHidden"
    />

    <BModal
      ref="branchModal"
      title="Create Revision Branch"
      :ok-disabled="vBranch$.description.$invalid || submittingBranch"
      @show="setupBranchForm"
      @hidden="resetBranchForm"
      @ok.prevent="onSubmitBranch"
    >
      <BAlert :variant="branchForm.isCurrentRevision ? 'info' : 'warning'" :model-value="true">
        <span v-if="branchForm.isCurrentRevision">
          This will create a new revision based on revision {{ branchForm.sourceRevision }}
          (current revision) and set it as the new current revision.
        </span>
        <span v-else>
          This will create a new branch from revision {{ branchForm.sourceRevision }}. The new
          revision will NOT be set as current.
        </span>
      </BAlert>
      <BForm @submit.stop.prevent="onSubmitBranch">
        <BFormGroup label="Description" label-for="branch-description">
          <BFormInput
            id="branch-description"
            v-model="branchForm.description"
            :state="validationState(vBranch$.description)"
          />
          <BFormInvalidFeedback>{{
            vBranch$.description.$errors[0]?.$message
          }}</BFormInvalidFeedback>
        </BFormGroup>
      </BForm>
    </BModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import { useVuelidate } from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import log from 'loglevel';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import { useWebSocketStore } from '@/stores/websocket';
import { useScriptConfigStore } from '@/stores/scriptConfig';
import { useConfirm } from '@/composables/useConfirm';
import { useFormValidation } from '@/composables/useFormValidation';
import type { ScriptRevision } from '@/types/api/script';
import RevisionGraph from './RevisionGraph.vue';
import RevisionDetailModal from './RevisionDetailModal.vue';

const showStore = useShowStore();
const systemStore = useSystemStore();
const wsStore = useWebSocketStore();
const scriptConfigStore = useScriptConfigStore();
const { confirm } = useConfirm();
const { validationState } = useFormValidation();

const revisionColumns = [
  { key: 'current', label: 'Current' },
  { key: 'revision', label: 'Revision' },
  { key: 'created_at', label: 'Created At' },
  { key: 'edited_at', label: 'Edited At' },
  { key: 'description', label: 'Description' },
  { key: 'previous_revision_id', label: 'Previous Revision' },
  { key: 'btn', label: '' },
];

const graphCollapsed = ref<boolean>(localStorage.getItem('revisionGraphCollapsed') === 'true');
watch(graphCollapsed, (val) => {
  localStorage.setItem('revisionGraphCollapsed', String(val));
});

const selectedRevisionId = ref<number | null>(null);
const selectedRevision = ref<ScriptRevision | null>(null);
const modalSubmitting = ref<boolean | string>(false);

const submittingNewRevision = ref(false);
const submittingBranch = ref(false);
const submittingLoadRevision = ref(false);
const deletingRevision = ref(false);

const newRevisionModal = ref<InstanceType<typeof BModal>>();
const revisionDetailModal = ref<InstanceType<typeof RevisionDetailModal>>();
const branchModal = ref<InstanceType<typeof BModal>>();

const newRevForm = ref({ description: '' });
const branchForm = ref({
  description: '',
  sourceRevisionId: null as number | null,
  sourceRevision: null as number | null,
  isCurrentRevision: false,
});

const vNew$ = useVuelidate({ description: { required } }, newRevForm);
const vBranch$ = useVuelidate({ description: { required } }, branchForm);

const canChangeRevisions = computed(
  () =>
    !wsStore.internalUUID ||
    scriptConfigStore.editStatus.currentEditor == null ||
    scriptConfigStore.editStatus.currentEditor === wsStore.internalUUID
);

function resetNewRevForm(): void {
  newRevForm.value = { description: '' };
  submittingNewRevision.value = false;
  vNew$.value.$reset();
}

async function onSubmitNewRev(): Promise<void> {
  const valid = await vNew$.value.$validate();
  if (!valid || submittingNewRevision.value) return;
  submittingNewRevision.value = true;
  try {
    await showStore.addScriptRevision({ description: newRevForm.value.description });
    newRevisionModal.value?.hide();
  } catch (e) {
    log.error('Error submitting new revision:', e);
  } finally {
    submittingNewRevision.value = false;
  }
}

async function loadRevision(item: ScriptRevision): Promise<void> {
  if (submittingLoadRevision.value) return;
  const ok = await confirm(`Are you sure you want to load revision ${item.revision}?`);
  if (!ok) return;
  submittingLoadRevision.value = true;
  try {
    await showStore.loadScriptRevision(item.id);
  } catch (e) {
    log.error('Error loading revision:', e);
  } finally {
    submittingLoadRevision.value = false;
  }
}

async function deleteRevision(item: ScriptRevision): Promise<void> {
  if (deletingRevision.value) return;
  let msg = `Are you sure you want to delete revision ${item.revision}?`;
  if (showStore.currentRevision === item.id) {
    msg += ' This will load the previous revision, or first revision if this is not available.';
  }
  const ok = await confirm(msg, {
    title: 'Delete Revision',
    okVariant: 'danger',
    okTitle: 'Delete',
  });
  if (!ok) return;
  deletingRevision.value = true;
  try {
    await showStore.deleteScriptRevision(item.id);
  } catch (e) {
    log.error('Error deleting revision:', e);
  } finally {
    deletingRevision.value = false;
  }
}

function handleNodeClick(revision: ScriptRevision): void {
  selectedRevisionId.value = revision.id;
  selectedRevision.value = revision;
  revisionDetailModal.value?.show();
}

async function handleModalLoadRevision(revision: ScriptRevision): Promise<void> {
  const ok = await confirm(`Are you sure you want to load revision ${revision.revision}?`);
  if (!ok) return;
  modalSubmitting.value = 'load';
  try {
    await showStore.loadScriptRevision(revision.id);
    revisionDetailModal.value?.hide();
  } catch (e) {
    log.error('Error loading revision from modal:', e);
  } finally {
    modalSubmitting.value = false;
  }
}

function handleModalCreateFrom(revision: ScriptRevision): void {
  branchForm.value.sourceRevisionId = revision.id;
  branchForm.value.sourceRevision = revision.revision;
  branchForm.value.isCurrentRevision = revision.id === showStore.currentRevision;
  branchModal.value?.show();
}

function setupBranchForm(): void {
  branchForm.value.description = '';
  submittingBranch.value = false;
  vBranch$.value.$reset();
}

function resetBranchForm(): void {
  branchForm.value = {
    description: '',
    sourceRevisionId: null,
    sourceRevision: null,
    isCurrentRevision: false,
  };
  submittingBranch.value = false;
  vBranch$.value.$reset();
}

async function onSubmitBranch(): Promise<void> {
  const valid = await vBranch$.value.$validate();
  if (!valid || submittingBranch.value) return;
  submittingBranch.value = true;
  try {
    await showStore.addScriptRevision({
      description: branchForm.value.description,
      parent_revision_id: branchForm.value.sourceRevisionId,
      set_as_current: branchForm.value.isCurrentRevision,
    });
    branchModal.value?.hide();
    revisionDetailModal.value?.hide();
    resetBranchForm();
  } catch (e) {
    log.error('Error creating branch:', e);
  } finally {
    submittingBranch.value = false;
  }
}

function handleModalHidden(): void {
  selectedRevisionId.value = null;
  selectedRevision.value = null;
  modalSubmitting.value = false;
}

onMounted(async () => {
  await scriptConfigStore.getScriptConfigStatus();
});
</script>

<style scoped>
.collapsed-card :deep(.card-body) {
  padding: 0;
}
</style>
