<template>
  <div v-if="!loading">
    <BTable
      id="acts-table"
      :items="actTableItems"
      :fields="actFields"
      :per-page="rowsPerPage"
      :current-page="currentPage"
      show-empty
    >
      <template #head(btn)>
        <BButton v-if="systemStore.isShowEditor" v-b-modal.new-act variant="outline-success">
          New Act
        </BButton>
      </template>
      <template #cell(interval_after)="data">
        <IMdiCheckboxMarked v-if="data.item.interval_after" style="color: #06bc8c" />
        <IMdiCloseBox v-else style="color: #e74c3c" />
      </template>
      <template #cell(next_act)="data">
        <span v-if="data.item.next_act">{{ showStore.actById(data.item.next_act)?.name }}</span>
        <span v-else>N/A</span>
      </template>
      <template #cell(previous_act)="data">
        <span v-if="data.item.previous_act">{{
          showStore.actById(data.item.previous_act)?.name
        }}</span>
        <span v-else>N/A</span>
      </template>
      <template #cell(btn)="data">
        <BButtonGroup v-if="systemStore.isShowEditor">
          <BButton
            variant="warning"
            :disabled="submittingEditAct || deletingAct"
            @click="openEditForm(data.item)"
          >
            Edit
          </BButton>
          <BButton
            variant="danger"
            :disabled="submittingEditAct || deletingAct"
            @click="deleteAct(data.item)"
          >
            Delete
          </BButton>
        </BButtonGroup>
      </template>
    </BTable>
    <BPagination
      v-show="actTableItems.length > rowsPerPage"
      v-model="currentPage"
      :total-rows="actTableItems.length"
      :per-page="rowsPerPage"
      aria-controls="acts-table"
      class="justify-content-center"
    />

    <BModal
      id="new-act"
      ref="newActModal"
      title="Add New Act"
      size="md"
      :ok-disabled="newV$.newFormState.$invalid || submittingNewAct"
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
        <BFormGroup label="Interval After" label-for="new-interval-input" label-cols="4">
          <BFormCheckbox id="new-interval-input" v-model="newFormState.interval_after" />
        </BFormGroup>
        <BFormGroup label="Previous Act" label-for="new-previous-act-input" label-cols="4">
          <BFormSelect
            id="new-previous-act-input"
            v-model="newFormState.previous_act_id"
            :options="previousActOptions"
          />
        </BFormGroup>
      </BForm>
    </BModal>

    <BModal
      id="edit-act"
      ref="editActModal"
      title="Edit Act"
      size="md"
      :ok-disabled="editV$.editFormState.$invalid || submittingEditAct"
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
        <BFormGroup label="Interval After" label-for="edit-interval-input" label-cols="4">
          <BFormCheckbox id="edit-interval-input" v-model="editFormState.interval_after" />
        </BFormGroup>
        <BFormGroup label="Previous Act" label-for="edit-previous-act-input" label-cols="4">
          <BFormSelect
            id="edit-previous-act-input"
            v-model="editFormState.previous_act_id"
            :options="editFormActOptions"
            :state="editFieldState('previous_act_id')"
          />
          <BFormInvalidFeedback
            >This cannot form a circular dependency between acts.</BFormInvalidFeedback
          >
        </BFormGroup>
      </BForm>
    </BModal>
  </div>
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
import type { Act } from '@/types/api/show';

const systemStore = useSystemStore();
const showStore = useShowStore();
const { confirm } = useConfirm();

const loading = ref(true);
const rowsPerPage = 15;
const currentPage = ref(1);
const submittingNewAct = ref(false);
const submittingEditAct = ref(false);
const deletingAct = ref(false);

const newActModal = ref<InstanceType<typeof BModal>>();
const editActModal = ref<InstanceType<typeof BModal>>();

const actFields = [
  'name',
  { key: 'interval_after', label: 'Interval After' },
  { key: 'previous_act', label: 'Previous Act' },
  { key: 'next_act', label: 'Next Act' },
  { key: 'btn', label: '' },
];

interface NewActForm {
  name: string;
  interval_after: boolean;
  previous_act_id: number | null;
}

interface EditActForm {
  id: number | null;
  showID: number | null;
  name: string;
  interval_after: boolean;
  previous_act_id: number | null;
}

const newFormState = ref<NewActForm>({ name: '', interval_after: false, previous_act_id: null });
const editFormState = ref<EditActForm>({
  id: null,
  showID: null,
  name: '',
  interval_after: false,
  previous_act_id: null,
});

const noActLoops = helpers.withMessage(
  'This cannot form a circular dependency between acts',
  (value: number | null) => {
    if (value == null) return true;
    const visited = new Set<number>();
    visited.add(editFormState.value.id ?? -1);
    let current = showStore.actById(value);
    while (current != null && current.previous_act != null) {
      if (visited.has(current.previous_act)) return false;
      current = showStore.actById(current.previous_act);
    }
    return true;
  }
);

const newRules = { newFormState: { name: { required } } };
const editRules = {
  editFormState: {
    name: { required },
    previous_act_id: { noActLoops },
  },
};

const newV$ = useVuelidate(newRules, { newFormState });
const editV$ = useVuelidate(editRules, { editFormState });

const actTableItems = computed((): Act[] => {
  const ret: Act[] = [];
  const show = systemStore.currentShow;
  if (show?.first_act_id != null && showStore.actList.length > 0) {
    let act = showStore.actById(show.first_act_id);
    while (act != null) {
      ret.push(act);
      act = showStore.actById(act.next_act);
    }
  }
  const linkedIds = new Set(ret.map((a) => a.id));
  for (const act of showStore.actList) {
    if (!linkedIds.has(act.id)) ret.push(act);
  }
  return ret;
});

const previousActOptions = computed(() => [
  { value: null, text: 'None', disabled: false },
  ...showStore.actList
    .filter((act) => act.next_act == null)
    .map((act) => ({ value: act.id, text: act.name })),
]);

const editFormActOptions = computed(() => {
  const base = previousActOptions.value.filter((opt) => opt.value !== editFormState.value.id);
  if (
    editFormState.value.previous_act_id != null &&
    !base.some((o) => o.value === editFormState.value.previous_act_id)
  ) {
    const act = showStore.actById(editFormState.value.previous_act_id);
    if (act) base.push({ value: act.id, text: act.name, disabled: false } as (typeof base)[0]);
  }
  return base;
});

function newFieldState(key: keyof NewActForm): boolean | null {
  const field = newV$.value.newFormState[key];
  if (!field) return null;
  return field.$dirty ? !field.$error : null;
}

function editFieldState(key: keyof EditActForm): boolean | null {
  const field = editV$.value.editFormState[key];
  if (!field) return null;
  return field.$dirty ? !field.$error : null;
}

function resetNewForm(): void {
  newFormState.value = { name: '', interval_after: false, previous_act_id: null };
  submittingNewAct.value = false;
  newV$.value.$reset();
}

function resetEditForm(): void {
  editFormState.value = {
    id: null,
    showID: null,
    name: '',
    interval_after: false,
    previous_act_id: null,
  };
  submittingEditAct.value = false;
  deletingAct.value = false;
  editV$.value.$reset();
}

function openEditForm(act: Act): void {
  editFormState.value.id = act.id;
  editFormState.value.showID = act.show_id;
  editFormState.value.name = act.name ?? '';
  editFormState.value.interval_after = act.interval_after ?? false;
  editFormState.value.previous_act_id = act.previous_act ?? null;
  editActModal.value?.show();
}

async function onSubmitNew(event: Event): Promise<void> {
  newV$.value.newFormState.$touch();
  if (newV$.value.newFormState.$invalid || submittingNewAct.value) {
    event.preventDefault();
    return;
  }
  submittingNewAct.value = true;
  try {
    await showStore.addAct(newFormState.value);
    newActModal.value?.hide();
    resetNewForm();
  } catch (error) {
    log.error('Error submitting new act:', error);
    event.preventDefault();
  } finally {
    submittingNewAct.value = false;
  }
}

async function onSubmitEdit(event: Event): Promise<void> {
  editV$.value.editFormState.$touch();
  if (editV$.value.editFormState.$invalid || submittingEditAct.value) {
    event.preventDefault();
    return;
  }
  submittingEditAct.value = true;
  try {
    await showStore.updateAct(editFormState.value);
    editActModal.value?.hide();
    resetEditForm();
  } catch (error) {
    log.error('Error submitting edit act:', error);
    event.preventDefault();
  } finally {
    submittingEditAct.value = false;
  }
}

async function deleteAct(act: Act): Promise<void> {
  if (deletingAct.value) return;
  const ok = await confirm(`Are you sure you want to delete ${act.name}?`);
  if (ok) {
    deletingAct.value = true;
    try {
      await showStore.deleteAct(act.id);
    } catch (error) {
      log.error('Error deleting act:', error);
    } finally {
      deletingAct.value = false;
    }
  }
}

onMounted(async () => {
  await showStore.getActList();
  loading.value = false;
});
</script>
