<template>
  <div>
    <BTable
      id="session-tags-table"
      :items="showStore.sessionTags"
      :fields="tagFields"
      :per-page="rowsPerPage"
      :current-page="currentPage"
      show-empty
    >
      <template #head(btn)>
        <template v-if="systemStore.isShowEditor">
          <BButton v-b-modal.new-session-tag variant="outline-success">New Tag</BButton>
          <BButton variant="outline-info" class="ms-2" @click="openImportModal">
            Import Tag
          </BButton>
        </template>
      </template>
      <template #cell(tag)="data">
        <span
          class="tag-pill"
          :style="{
            backgroundColor: data.item.colour,
            color: contrastColor(data.item.colour ?? '#ffffff'),
          }"
        >
          {{ data.item.tag }}
        </span>
      </template>
      <template #cell(session_count)="data">
        {{ getSessionCountForTag(data.item.id) }}
      </template>
      <template #cell(btn)="data">
        <BButtonGroup v-if="systemStore.isShowEditor">
          <BButton variant="warning" @click="openEditTagForm(data.item)">Edit</BButton>
          <BButton variant="danger" :disabled="isSubmittingDeleteTag" @click="deleteTag(data.item)">
            Delete
          </BButton>
        </BButtonGroup>
      </template>
    </BTable>
    <BPagination
      v-show="showStore.sessionTags.length > rowsPerPage"
      v-model="currentPage"
      :total-rows="showStore.sessionTags.length"
      :per-page="rowsPerPage"
      aria-controls="session-tags-table"
      class="justify-content-center"
    />

    <BModal
      id="new-session-tag"
      ref="newTagModal"
      title="Add Session Tag"
      size="md"
      :ok-disabled="newV$.newFormState.$invalid || isSubmittingNewTag"
      @show="resetNewTagForm"
      @hide="resetNewTagForm"
      @ok="onSubmitNewTag"
    >
      <BForm @submit.stop.prevent="onSubmitNewTag">
        <BFormGroup label="Tag Name" label-for="new-tag-name" label-cols="4">
          <BFormInput id="new-tag-name" v-model="newFormState.tag" :state="newFieldState('tag')" />
          <BFormInvalidFeedback>
            This is a required field and must be unique (case-insensitive).
          </BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Colour" label-for="new-tag-colour" label-cols="4">
          <BFormInput
            id="new-tag-colour"
            v-model="newFormState.colour"
            type="color"
            style="width: 60px"
            :state="newFieldState('colour')"
          />
          <BFormInvalidFeedback>This is a required field.</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Preview" label-cols="4">
          <span
            class="tag-pill"
            :style="{
              backgroundColor: newFormState.colour,
              color: contrastColor(newFormState.colour),
            }"
          >
            {{ newFormState.tag || 'Tag Name' }}
          </span>
        </BFormGroup>
      </BForm>
    </BModal>

    <BModal
      id="edit-session-tag"
      ref="editTagModal"
      title="Edit Session Tag"
      size="md"
      :ok-disabled="editV$.editFormState.$invalid || isSubmittingEditTag"
      @hide="resetEditTagForm"
      @ok="onSubmitEditTag"
    >
      <BForm @submit.stop.prevent="onSubmitEditTag">
        <BFormGroup label="Tag Name" label-for="edit-tag-name" label-cols="4">
          <BFormInput
            id="edit-tag-name"
            v-model="editFormState.tag"
            :state="editFieldState('tag')"
          />
          <BFormInvalidFeedback>
            This is a required field and must be unique (case-insensitive).
          </BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Colour" label-for="edit-tag-colour" label-cols="4">
          <BFormInput
            id="edit-tag-colour"
            v-model="editFormState.colour"
            type="color"
            style="width: 60px"
            :state="editFieldState('colour')"
          />
          <BFormInvalidFeedback>This is a required field.</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Preview" label-cols="4">
          <span
            class="tag-pill"
            :style="{
              backgroundColor: editFormState.colour,
              color: contrastColor(editFormState.colour),
            }"
          >
            {{ editFormState.tag || 'Tag Name' }}
          </span>
        </BFormGroup>
      </BForm>
    </BModal>

    <BModal
      id="import-tag-modal"
      ref="importTagModal"
      title="Import Session Tag"
      size="xl"
      hide-footer
      @hide="resetImportState"
    >
      <div v-if="isLoadingImport" class="text-center">
        <BSpinner />
      </div>
      <div v-else-if="importGroups.length === 0">
        <p class="text-muted">No session tags available to import from other shows.</p>
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
            <BTable :items="show.tags" :fields="importTagFields" small>
              <template #cell(tag)="data">
                <span
                  class="tag-pill"
                  :style="{
                    backgroundColor: data.item.colour,
                    color: contrastColor(data.item.colour ?? '#ffffff'),
                  }"
                >
                  {{ data.item.tag }}
                </span>
              </template>
              <template #cell(action)="data">
                <BButton
                  variant="outline-success"
                  size="sm"
                  :disabled="!!isImporting[data.item.id] || tagAlreadyExists(data.item.tag)"
                  @click="importTag(data.item)"
                >
                  <BSpinner v-if="isImporting[data.item.id]" small />
                  <span v-else-if="tagAlreadyExists(data.item.tag)">Already exists</span>
                  <span v-else>Import</span>
                </BButton>
              </template>
            </BTable>
          </BCollapse>
        </BCard>
      </div>
    </BModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useVuelidate } from '@vuelidate/core';
import { required, helpers } from '@vuelidate/validators';
import { BModal } from 'bootstrap-vue-next';
import { contrastColor } from '@/js/utils';
import log from 'loglevel';
import { useSystemStore } from '@/stores/system';
import { useShowStore } from '@/stores/show';
import { useConfirm } from '@/composables/useConfirm';
import type { SessionTag } from '@/types/api/session';

const systemStore = useSystemStore();
const showStore = useShowStore();
const { confirm } = useConfirm();

const rowsPerPage = 15;
const currentPage = ref(1);
const isSubmittingNewTag = ref(false);
const isSubmittingEditTag = ref(false);
const isSubmittingDeleteTag = ref(false);

const newTagModal = ref<InstanceType<typeof BModal>>();
const editTagModal = ref<InstanceType<typeof BModal>>();
const importTagModal = ref<InstanceType<typeof BModal>>();

const tagFields = [
  { key: 'tag', label: 'Tag' },
  { key: 'session_count', label: 'Sessions' },
  { key: 'btn', label: '' },
];
const importTagFields = [
  { key: 'tag', label: 'Tag' },
  { key: 'action', label: '' },
];

interface TagForm {
  tag: string;
  colour: string;
}

interface EditTagForm extends TagForm {
  id: number | null;
}

const newFormState = ref<TagForm>({ tag: '', colour: '#3498DB' });
const editFormState = ref<EditTagForm>({ id: null, tag: '', colour: '#3498DB' });

const uniqueNewTag = helpers.withMessage(
  'This tag already exists',
  (value: string) => !showStore.sessionTags.some((t) => t.tag.toLowerCase() === value.toLowerCase())
);

const uniqueEditTag = helpers.withMessage(
  'This tag already exists',
  (value: string) =>
    !showStore.sessionTags.some(
      (t) => t.tag.toLowerCase() === value.toLowerCase() && t.id !== editFormState.value.id
    )
);

const newRules = { newFormState: { tag: { required, uniqueNewTag }, colour: { required } } };
const editRules = { editFormState: { tag: { required, uniqueEditTag }, colour: { required } } };

const newV$ = useVuelidate(newRules, { newFormState });
const editV$ = useVuelidate(editRules, { editFormState });

const importGroups = ref<{ id: number; name: string; tags: SessionTag[] }[]>([]);
const isExpanded = ref<Record<number, boolean>>({});
const isImporting = ref<Record<number, boolean>>({});
const isLoadingImport = ref(false);

const existingTagNames = computed(
  () => new Set(showStore.sessionTags.map((t) => t.tag.toLowerCase()))
);

function newFieldState(key: keyof TagForm): boolean | null {
  const field = newV$.value.newFormState[key];
  if (!field) return null;
  return field.$dirty ? !field.$error : null;
}

function editFieldState(key: keyof EditTagForm): boolean | null {
  const field = editV$.value.editFormState[key];
  if (!field) return null;
  return field.$dirty ? !field.$error : null;
}

function getSessionCountForTag(tagId: number): number {
  return showStore.sessions.filter((s) => s.tags?.some((t) => t.id === tagId)).length;
}

function tagAlreadyExists(tagName: string): boolean {
  return existingTagNames.value.has(tagName.toLowerCase());
}

function resetNewTagForm(): void {
  newFormState.value = { tag: '', colour: '#3498DB' };
  isSubmittingNewTag.value = false;
  newV$.value.$reset();
}

function resetEditTagForm(): void {
  editFormState.value = { id: null, tag: '', colour: '#3498DB' };
  isSubmittingEditTag.value = false;
  editV$.value.$reset();
}

function openEditTagForm(tag: SessionTag): void {
  editFormState.value.id = tag.id;
  editFormState.value.tag = tag.tag;
  editFormState.value.colour = tag.colour;
  editTagModal.value?.show();
}

async function onSubmitNewTag(event: Event): Promise<void> {
  newV$.value.newFormState.$touch();
  if (newV$.value.newFormState.$invalid || isSubmittingNewTag.value) {
    event.preventDefault();
    return;
  }
  isSubmittingNewTag.value = true;
  try {
    await showStore.addSessionTag(newFormState.value);
    newTagModal.value?.hide();
    resetNewTagForm();
  } catch (error) {
    log.error('Error adding session tag:', error);
    event.preventDefault();
  } finally {
    isSubmittingNewTag.value = false;
  }
}

async function onSubmitEditTag(event: Event): Promise<void> {
  editV$.value.editFormState.$touch();
  if (editV$.value.editFormState.$invalid || isSubmittingEditTag.value) {
    event.preventDefault();
    return;
  }
  isSubmittingEditTag.value = true;
  try {
    await showStore.updateSessionTag(editFormState.value);
    editTagModal.value?.hide();
    resetEditTagForm();
  } catch (error) {
    log.error('Error updating session tag:', error);
    event.preventDefault();
  } finally {
    isSubmittingEditTag.value = false;
  }
}

async function deleteTag(tag: SessionTag): Promise<void> {
  if (isSubmittingDeleteTag.value) return;
  const sessionCount = getSessionCountForTag(tag.id);
  let msg = `Are you sure you want to delete the tag "${tag.tag}"?`;
  if (sessionCount > 0) {
    msg += ` This tag is currently applied to ${sessionCount} session(s).`;
  }
  const ok = await confirm(msg);
  if (ok) {
    isSubmittingDeleteTag.value = true;
    try {
      await showStore.deleteSessionTag(tag.id);
    } catch (error) {
      log.error('Error deleting session tag:', error);
    } finally {
      isSubmittingDeleteTag.value = false;
    }
  }
}

async function openImportModal(): Promise<void> {
  importTagModal.value?.show();
  isLoadingImport.value = true;
  try {
    const data = (await showStore.getImportableSessionTags()) as {
      tag_groups: { id: number; name: string; tags: SessionTag[] }[];
    };
    importGroups.value = data.tag_groups;
    data.tag_groups.forEach((show) => {
      isExpanded.value[show.id] = true;
    });
  } catch (e) {
    log.error('Error loading importable session tags:', e);
  } finally {
    isLoadingImport.value = false;
  }
}

function toggleImportShow(showId: number): void {
  isExpanded.value[showId] = !isExpanded.value[showId];
}

async function importTag(tag: SessionTag): Promise<void> {
  isImporting.value[tag.id] = true;
  try {
    await showStore.addSessionTag({ tag: tag.tag, colour: tag.colour });
  } catch (error) {
    log.error('Error importing session tag:', error);
  } finally {
    isImporting.value[tag.id] = false;
  }
}

function resetImportState(): void {
  importGroups.value = [];
  isExpanded.value = {};
  isLoadingImport.value = false;
  isImporting.value = {};
}
</script>

<style scoped>
.tag-pill {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 12px;
  white-space: nowrap;
  border: 1px solid rgba(0, 0, 0, 0.1);
}
</style>
