<template>
  <div>
    <BAlert
      v-if="systemStore.isCollabScriptEditing && currentRevisionLocked"
      variant="warning"
      class="mb-3"
      :model-value="true"
    >
      <div class="d-flex justify-content-between align-items-center">
        <span>
          The current revision has an unsaved collaborative draft<template
            v-if="draftEditorUsernames.length > 0"
          >
            &mdash; {{ draftEditorUsernames.join(', ') }}
            {{ draftEditorUsernames.length > 1 ? 'are' : 'is' }} editing it</template
          >. Loading, creating and deleting revisions is blocked until it is saved or discarded.
        </span>
        <BButton size="sm" variant="danger" :disabled="discardingDraft" @click="discardDraft">
          Discard Draft
        </BButton>
      </div>
    </BAlert>

    <BCard class="mb-3" :class="{ 'collapsed-card': !graphCollapsed }" header-tag="header">
      <template #header>
        <div class="d-flex justify-content-between align-items-center">
          <h6 class="mb-0">Revision Branch Graph</h6>
          <BButton size="sm" variant="secondary" @click="graphCollapsed = !graphCollapsed">
            <IMdiChevronUp v-if="!graphCollapsed" />
            <IMdiChevronDown v-else />
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
        <IMdiCheckboxMarked
          v-if="data.item.id === showStore.currentRevision"
          style="color: #06bc8c"
        />
        <BButton
          v-else-if="systemStore.isScriptEditor"
          variant="warning"
          :disabled="
            !canChangeRevisions ||
            submittingLoadRevision ||
            submittingNewRevision ||
            deletingRevision
          "
          :title="!canChangeRevisions ? (changeRevisionsDisabledReason ?? undefined) : undefined"
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
              Boolean(data.item.has_draft) ||
              submittingLoadRevision ||
              submittingNewRevision ||
              deletingRevision
            "
            :title="rowLockedReason(data.item) ?? undefined"
            @click="handleModalCreateFrom(data.item)"
          >
            Edit
          </BButton>
          <BButton
            variant="danger"
            :disabled="
              !canChangeRevisions ||
              Boolean(data.item.has_draft) ||
              submittingLoadRevision ||
              submittingNewRevision ||
              deletingRevision
            "
            :title="rowLockedReason(data.item) ?? undefined"
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
              :title="
                !canChangeRevisions ? (changeRevisionsDisabledReason ?? undefined) : undefined
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
import { makeURL } from '@/js/utils';
import { toast } from '@/js/toast';
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
const discardingDraft = ref(false);

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

// `has_draft` on each revision row mirrors the server's own `_revision_is_locked`
// exactly (a persisted ScriptDraft row, or a non-empty active room, for that
// revision) — only `showStore.currentRevision` can ever carry one, since a room can
// only ever be built against the show's current revision.
const currentRevisionLocked = computed(
  () =>
    showStore.scriptRevisions.find((r) => r.id === showStore.currentRevision)?.has_draft ?? false
);
const draftEditorUsernames = computed(() =>
  scriptConfigStore.editors.map((e) => e.username).filter((name): name is string => name != null)
);

// D11: in collab mode, Load/New Revision (both implicitly target the current
// revision) are blocked exactly when the current revision has an active
// draft/room, regardless of who holds it — matching `_revision_is_locked`'s own
// unconditional 409, not an identity check. Legacy mode keeps its existing rule
// (the current single editor may still act while they hold the lock).
const canChangeRevisions = computed(() => {
  if (systemStore.isCollabScriptEditing) return !currentRevisionLocked.value;
  return (
    !wsStore.internalUUID ||
    scriptConfigStore.editStatus.currentEditor == null ||
    scriptConfigStore.editStatus.currentEditor === wsStore.internalUUID
  );
});

const changeRevisionsDisabledReason = computed<string | null>(() => {
  if (canChangeRevisions.value) return null;
  return systemStore.isCollabScriptEditing
    ? 'The current revision has an unsaved collaborative draft'
    : 'Another user is currently editing the script';
});

function rowLockedReason(item: ScriptRevision): string | null {
  if (item.has_draft) return 'This revision has an unsaved collaborative draft';
  return changeRevisionsDisabledReason.value;
}

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

// D9-consistent warning (same phrasing as the in-editor Discard in CollabScriptEditor.vue):
// discard is room-wide, so it names who else is editing, not just a plain confirm.
async function discardDraft(): Promise<void> {
  if (discardingDraft.value) return;
  let msg = 'This will discard the unsaved collaborative draft. This cannot be undone.';
  if (draftEditorUsernames.value.length > 0) {
    const names = draftEditorUsernames.value.join(', ');
    const verb = draftEditorUsernames.value.length > 1 ? 'are' : 'is';
    msg += ` ${names} ${verb} also editing — discarding will clear their unsaved work too, not just yours.`;
  }
  const ok = await confirm(msg, {
    title: 'Discard Draft',
    okVariant: 'danger',
    okTitle: 'Discard',
  });
  if (!ok) return;
  discardingDraft.value = true;
  try {
    const response = await fetch(makeURL('/api/v1/show/script/draft'), { method: 'DELETE' });
    if (response.ok) {
      toast.success('Draft discarded');
    } else {
      toast.error('Unable to discard draft');
    }
  } catch (e) {
    log.error('Error discarding draft:', e);
    toast.error('Unable to discard draft');
  } finally {
    discardingDraft.value = false;
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
