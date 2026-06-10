<template>
  <div>
    <template v-if="systemStore.currentShow != null">
      <BTable
        id="cue-colour-table"
        :items="tableData"
        :fields="columns"
        :per-page="perPage"
        :current-page="currentPage"
        show-empty
      >
        <template #head(btn)>
          <BButton
            variant="outline-success"
            :disabled="overrideChoices.length <= 1"
            @click="selectModal?.show()"
          >
            New Override
          </BButton>
        </template>

        <template #cell(description)="data">
          {{ cueTypes.find((t) => t.id === data.item.settings.id)?.description }}
        </template>

        <template #cell(example)="data">
          <button
            class="cue-button-example"
            :style="{
              'background-color': data.item.settings.colour,
              color: contrastColor(data.item.settings.colour ?? '#ffffff'),
            }"
          >
            {{ cueTypes.find((t) => t.id === data.item.settings.id)?.prefix }}
          </button>
        </template>

        <template #cell(btn)="data">
          <BButtonGroup>
            <BButton
              variant="warning"
              :disabled="isSubmittingEdit || isDeleting"
              @click="openEditForm(data)"
            >
              Edit
            </BButton>
            <BButton
              variant="danger"
              :disabled="isSubmittingEdit || isDeleting"
              @click="openDeleteConfirm(data.item.id)"
            >
              Delete
            </BButton>
          </BButtonGroup>
        </template>
      </BTable>
      <PaginationControls
        v-model:per-page="perPage"
        v-model:current-page="currentPage"
        :total-rows="tableData.length"
        aria-controls="cue-colour-table"
      />
    </template>
    <BAlert v-else :model-value="true" variant="danger">No show loaded.</BAlert>

    <!-- Select cue type modal -->
    <BModal
      ref="selectModal"
      title="Add New Cue Colour Override"
      :ok-disabled="newFormState.cueTypeId == null || isSubmittingNew"
      @show="newFormState.cueTypeId = null"
      @ok="openNewOverrideModal"
    >
      <BForm>
        <BFormSelect v-model="newFormState.cueTypeId" :options="overrideChoices" />
      </BForm>
    </BModal>

    <!-- New override config modal -->
    <BModal
      ref="newModal"
      title="Add New Cue Colour Override"
      size="lg"
      :ok-disabled="isSubmittingNew"
      @hidden="resetNewFormState"
      @ok.prevent="onSubmitNewOverride"
    >
      <div>
        <h4>Example Cue Button</h4>
        <button
          class="cue-button-example"
          :style="{
            'background-color': newFormState.colour,
            color: contrastColor(newFormState.colour),
          }"
        >
          {{ newFormCueTypePrefix }}
        </button>
      </div>
      <div>
        <h4>Configuration Options</h4>
        <BFormGroup label="Cue Button Colour" label-for="new-colour-input">
          <BFormInput
            id="new-colour-input"
            v-model="newFormState.colour"
            type="color"
            :state="validationState(vNew$.colour)"
            aria-describedby="new-colour-feedback"
          />
          <BFormInvalidFeedback id="new-colour-feedback">
            This is a required field.
          </BFormInvalidFeedback>
        </BFormGroup>
      </div>
    </BModal>

    <!-- Edit override config modal -->
    <BModal
      ref="editModal"
      title="Edit Cue Colour Override"
      size="lg"
      :ok-disabled="isSubmittingEdit"
      @hidden="resetEditFormState"
      @ok.prevent="onSubmitEditOverride"
    >
      <div>
        <h4>Example Cue Button</h4>
        <button
          class="cue-button-example"
          :style="{
            'background-color': editFormState.colour,
            color: contrastColor(editFormState.colour),
          }"
        >
          {{ editFormCueTypePrefix }}
        </button>
      </div>
      <div>
        <h4>Configuration Options</h4>
        <BFormGroup label="Cue Button Colour" label-for="edit-colour-input">
          <BFormInput
            id="edit-colour-input"
            v-model="editFormState.colour"
            type="color"
            :state="validationState(vEdit$.colour)"
            aria-describedby="edit-colour-feedback"
          />
          <BFormInvalidFeedback id="edit-colour-feedback">
            This is a required field.
          </BFormInvalidFeedback>
        </BFormGroup>
      </div>
    </BModal>

    <!-- Delete confirmation modal -->
    <BModal
      ref="deleteModal"
      title="Delete Override"
      ok-variant="danger"
      ok-title="Delete"
      @ok="confirmDelete"
    >
      <p>Are you sure you want to delete this override?</p>
    </BModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import { useVuelidate } from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import { contrastColor, makeURL } from '@/js/utils';
import log from 'loglevel';
import { useUserStore } from '@/stores/user';
import { useSystemStore } from '@/stores/system';
import { useFormValidation } from '@/composables/useFormValidation';
import { usePagination } from '@/composables/usePagination';
import type { CueType } from '@/types/api/cues';

const userStore = useUserStore();
const systemStore = useSystemStore();
const { validationState } = useFormValidation();

const columns = [
  'description',
  { key: 'example', label: 'Example Cue Button' },
  { key: 'btn', label: '' },
];
const { perPage, currentPage } = usePagination(15, 'user_cue_colour_prefs');

const cueTypes = ref<CueType[]>([]);
const isSubmittingNew = ref(false);
const isSubmittingEdit = ref(false);
const isDeleting = ref(false);
const pendingDeleteId = ref<number | null>(null);

const selectModal = ref<InstanceType<typeof BModal>>();
const newModal = ref<InstanceType<typeof BModal>>();
const editModal = ref<InstanceType<typeof BModal>>();
const deleteModal = ref<InstanceType<typeof BModal>>();

const newFormState = ref({ cueTypeId: null as number | null, colour: '#FF0000' });
const editFormState = ref({
  id: null as number | null,
  cueTypeId: null as number | null,
  colour: '#FF0000',
});

const vNewRules = { colour: { required } };
const vEditRules = { colour: { required } };
const vNew$ = useVuelidate(vNewRules, newFormState);
const vEdit$ = useVuelidate(vEditRules, editFormState);

const tableData = computed(() =>
  userStore.cueColourOverrides.filter((item) =>
    cueTypes.value.map((t) => t.id).includes(item.cue_type_id ?? -1)
  )
);

const overrideChoices = computed(() => [
  { value: null, text: 'Please select a cue type', disabled: true },
  ...cueTypes.value
    .filter((t) => !userStore.cueColourOverrides.map((o) => o.cue_type_id).includes(t.id))
    .map((t) => ({ value: t.id, text: `${t.prefix} - ${t.description}` })),
]);

const newFormCueTypePrefix = computed(() => {
  if (!newFormState.value.cueTypeId) return '';
  return cueTypes.value.find((t) => t.id === newFormState.value.cueTypeId)?.prefix ?? '';
});

const editFormCueTypePrefix = computed(() => {
  if (!editFormState.value.cueTypeId) return '';
  return cueTypes.value.find((t) => t.id === editFormState.value.cueTypeId)?.prefix ?? '';
});

onMounted(async () => {
  if (systemStore.currentShow) {
    try {
      const response = await fetch(makeURL('/api/v1/show/cues/types'));
      if (response.ok) cueTypes.value = ((await response.json()).cue_types as CueType[]) ?? [];
    } catch (e) {
      log.error('Failed to load cue types:', e);
    }
    await userStore.getCueColourOverrides();
  }
});

function openNewOverrideModal(): void {
  const cueType = cueTypes.value.find((t) => t.id === newFormState.value.cueTypeId);
  if (!cueType) {
    log.error('Could not find cue type to override!');
    return;
  }
  newFormState.value.colour = cueType.colour ?? '#FF0000';
  selectModal.value?.hide();
  newModal.value?.show();
}

function resetNewFormState(): void {
  newFormState.value = { cueTypeId: null, colour: '#FF0000' };
  isSubmittingNew.value = false;
  vNew$.value.$reset();
}

function resetEditFormState(): void {
  editFormState.value = { id: null, cueTypeId: null, colour: '#FF0000' };
  isSubmittingEdit.value = false;
  vEdit$.value.$reset();
}

async function onSubmitNewOverride(): Promise<void> {
  const valid = await vNew$.value.$validate();
  if (!valid || isSubmittingNew.value) return;

  isSubmittingNew.value = true;
  try {
    await userStore.addCueColourOverride({
      cueTypeId: newFormState.value.cueTypeId,
      colour: newFormState.value.colour,
    });
    newModal.value?.hide();
    resetNewFormState();
  } catch (e) {
    log.error('Error adding cue colour override:', e);
  } finally {
    isSubmittingNew.value = false;
  }
}

async function onSubmitEditOverride(): Promise<void> {
  const valid = await vEdit$.value.$validate();
  if (!valid || isSubmittingEdit.value) return;

  isSubmittingEdit.value = true;
  try {
    await userStore.updateCueColourOverride({
      id: editFormState.value.id,
      colour: editFormState.value.colour,
    });
    editModal.value?.hide();
    resetEditFormState();
  } catch (e) {
    log.error('Error updating cue colour override:', e);
  } finally {
    isSubmittingEdit.value = false;
  }
}

function openEditForm(data: {
  item: {
    id: number;
    cue_type_id: number | null;
    colour: string | null;
    settings: { id: number; colour: string };
  };
}): void {
  const { settings, id } = data.item;
  editFormState.value = { id, cueTypeId: settings.id, colour: settings.colour };
  editModal.value?.show();
}

function openDeleteConfirm(id: number): void {
  pendingDeleteId.value = id;
  deleteModal.value?.show();
}

async function confirmDelete(): Promise<void> {
  if (pendingDeleteId.value == null || isDeleting.value) return;
  isDeleting.value = true;
  try {
    await userStore.deleteCueColourOverride(pendingDeleteId.value);
  } catch (e) {
    log.error('Error deleting cue colour override:', e);
  } finally {
    isDeleting.value = false;
    pendingDeleteId.value = null;
  }
}
</script>

<style scoped>
.cue-button-example {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  font-weight: bold;
  font-size: 14px;
  cursor: default;
  min-width: 60px;
}
</style>
