<template>
  <BContainer class="mx-0" fluid>
    <BRow>
      <BCol>
        <BTabs content-class="mt-3">
          <BTab title="Cast List" active>
            <BTable
              id="cast-table"
              :items="showStore.castList"
              :fields="castFields"
              :per-page="rowsPerPage"
              :current-page="currentPage"
              show-empty
            >
              <template #head(btn)>
                <BButton
                  v-if="systemStore.isShowEditor"
                  v-b-modal.new-cast
                  variant="outline-success"
                >
                  New Cast Member
                </BButton>
              </template>
              <template #cell(btn)="data">
                <BButtonGroup v-if="systemStore.isShowEditor">
                  <BButton
                    variant="warning"
                    :disabled="submittingEditCast || deletingCast"
                    @click="openEditForm(data.item)"
                  >
                    Edit
                  </BButton>
                  <BButton
                    variant="danger"
                    :disabled="submittingEditCast || deletingCast"
                    @click="deleteCastMember(data.item)"
                  >
                    Delete
                  </BButton>
                </BButtonGroup>
              </template>
            </BTable>
            <BPagination
              v-show="showStore.castList.length > rowsPerPage"
              v-model="currentPage"
              :total-rows="showStore.castList.length"
              :per-page="rowsPerPage"
              aria-controls="cast-table"
              class="justify-content-center"
            />
          </BTab>
          <BTab title="Line Counts">
            <CastLineStats />
          </BTab>
        </BTabs>
      </BCol>
    </BRow>

    <BModal
      id="new-cast"
      ref="newCastModal"
      title="Add New Cast Member"
      size="sm"
      :ok-disabled="newV$.newFormState.$invalid || submittingNewCast"
      @show="resetNewForm"
      @hide="resetNewForm"
      @ok="onSubmitNew"
    >
      <BForm @submit.stop.prevent="onSubmitNew">
        <BFormGroup label="First Name" label-for="new-first-name-input" label-cols="4">
          <BFormInput
            id="new-first-name-input"
            v-model="newFormState.firstName"
            :state="newFieldState('firstName')"
          />
          <BFormInvalidFeedback>This is a required field.</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Last Name" label-for="new-last-name-input" label-cols="4">
          <BFormInput
            id="new-last-name-input"
            v-model="newFormState.lastName"
            :state="newFieldState('lastName')"
          />
          <BFormInvalidFeedback>This is a required field.</BFormInvalidFeedback>
        </BFormGroup>
      </BForm>
    </BModal>

    <BModal
      id="edit-cast"
      ref="editCastModal"
      title="Edit Cast Member"
      size="sm"
      :ok-disabled="editV$.editFormState.$invalid || submittingEditCast"
      @hide="resetEditForm"
      @ok="onSubmitEdit"
    >
      <BForm @submit.stop.prevent="onSubmitEdit">
        <BFormGroup label="First Name" label-for="edit-first-name-input" label-cols="4">
          <BFormInput
            id="edit-first-name-input"
            v-model="editFormState.firstName"
            :state="editFieldState('firstName')"
          />
          <BFormInvalidFeedback>This is a required field.</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Last Name" label-for="edit-last-name-input" label-cols="4">
          <BFormInput
            id="edit-last-name-input"
            v-model="editFormState.lastName"
            :state="editFieldState('lastName')"
          />
          <BFormInvalidFeedback>This is a required field.</BFormInvalidFeedback>
        </BFormGroup>
      </BForm>
    </BModal>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useVuelidate } from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import { BModal } from 'bootstrap-vue-next';
import log from 'loglevel';
import { useSystemStore } from '@/stores/system';
import { useShowStore } from '@/stores/show';
import { useConfirm } from '@/composables/useConfirm';
import CastLineStats from '@/components/show/config/cast/CastLineStats.vue';
import type { Cast } from '@/types/api/show';

const systemStore = useSystemStore();
const showStore = useShowStore();
const { confirm } = useConfirm();

const rowsPerPage = 15;
const currentPage = ref(1);
const submittingNewCast = ref(false);
const submittingEditCast = ref(false);
const deletingCast = ref(false);

const newCastModal = ref<InstanceType<typeof BModal>>();
const editCastModal = ref<InstanceType<typeof BModal>>();

const castFields = [
  { key: 'first_name', label: 'First Name' },
  { key: 'last_name', label: 'Last Name' },
  { key: 'btn', label: '' },
];

interface NewCastForm {
  firstName: string;
  lastName: string;
}

interface EditCastForm {
  id: number | null;
  showID: number | null;
  firstName: string;
  lastName: string;
}

const newFormState = ref<NewCastForm>({ firstName: '', lastName: '' });
const editFormState = ref<EditCastForm>({ id: null, showID: null, firstName: '', lastName: '' });

const newRules = { newFormState: { firstName: { required }, lastName: { required } } };
const editRules = { editFormState: { firstName: { required }, lastName: { required } } };

const newV$ = useVuelidate(newRules, { newFormState });
const editV$ = useVuelidate(editRules, { editFormState });

function newFieldState(key: keyof NewCastForm): boolean | null {
  const field = newV$.value.newFormState[key];
  if (!field) return null;
  return field.$dirty ? !field.$error : null;
}

function editFieldState(key: keyof EditCastForm): boolean | null {
  const field = editV$.value.editFormState[key];
  if (!field) return null;
  return field.$dirty ? !field.$error : null;
}

function resetNewForm(): void {
  newFormState.value = { firstName: '', lastName: '' };
  submittingNewCast.value = false;
  newV$.value.$reset();
}

function resetEditForm(): void {
  editFormState.value = { id: null, showID: null, firstName: '', lastName: '' };
  submittingEditCast.value = false;
  deletingCast.value = false;
  editV$.value.$reset();
}

function openEditForm(cast: Cast): void {
  editFormState.value.id = cast.id;
  editFormState.value.showID = cast.show_id;
  editFormState.value.firstName = cast.first_name ?? '';
  editFormState.value.lastName = cast.last_name ?? '';
  editCastModal.value?.show();
}

async function onSubmitNew(event: Event): Promise<void> {
  newV$.value.newFormState.$touch();
  if (newV$.value.newFormState.$invalid || submittingNewCast.value) {
    event.preventDefault();
    return;
  }
  submittingNewCast.value = true;
  try {
    await showStore.addCastMember(newFormState.value);
    newCastModal.value?.hide();
    resetNewForm();
  } catch (error) {
    log.error('Error submitting new cast member:', error);
    event.preventDefault();
  } finally {
    submittingNewCast.value = false;
  }
}

async function onSubmitEdit(event: Event): Promise<void> {
  editV$.value.editFormState.$touch();
  if (editV$.value.editFormState.$invalid || submittingEditCast.value) {
    event.preventDefault();
    return;
  }
  submittingEditCast.value = true;
  try {
    await showStore.updateCastMember(editFormState.value);
    editCastModal.value?.hide();
    resetEditForm();
  } catch (error) {
    log.error('Error submitting edit cast member:', error);
    event.preventDefault();
  } finally {
    submittingEditCast.value = false;
  }
}

async function deleteCastMember(cast: Cast): Promise<void> {
  if (deletingCast.value) return;
  const ok = await confirm(`Are you sure you want to delete ${cast.first_name} ${cast.last_name}?`);
  if (ok) {
    deletingCast.value = true;
    try {
      await showStore.deleteCastMember(cast.id);
    } catch (error) {
      log.error('Error deleting cast member:', error);
    } finally {
      deletingCast.value = false;
    }
  }
}

onMounted(async () => {
  await showStore.getCastList();
});
</script>
