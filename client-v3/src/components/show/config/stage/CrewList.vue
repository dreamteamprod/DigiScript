<template>
  <BContainer class="mx-0" fluid>
    <BRow>
      <BCol>
        <BTable
          :items="stageStore.crewList"
          :fields="fields"
          :per-page="rowsPerPage"
          :current-page="currentPage"
          show-empty
        >
          <template #head(btn)>
            <BButton
              v-if="systemStore.isShowEditor"
              variant="outline-success"
              @click="newModal?.show()"
            >
              Add Crew Member
            </BButton>
          </template>
          <template #cell(btn)="data">
            <BButtonGroup v-if="systemStore.isShowEditor">
              <BButton variant="warning" :disabled="isSubmitting" @click="openEdit(data.item)">
                Edit
              </BButton>
              <BButton variant="danger" :disabled="isSubmitting" @click="confirmDelete(data.item)">
                Delete
              </BButton>
            </BButtonGroup>
          </template>
        </BTable>
        <BPagination
          v-if="stageStore.crewList.length > rowsPerPage"
          v-model="currentPage"
          :total-rows="stageStore.crewList.length"
          :per-page="rowsPerPage"
        />
      </BCol>
    </BRow>

    <BModal
      ref="newModal"
      title="Add Crew Member"
      :ok-disabled="isSubmitting"
      @hidden="resetNew"
      @ok.prevent="submitNew"
    >
      <BForm>
        <BFormGroup label="First Name" label-for="new-first-name">
          <BFormInput
            id="new-first-name"
            v-model="newForm.first_name"
            :state="validationState(vNew$.first_name)"
          />
          <BFormInvalidFeedback>{{ vNew$.first_name.$errors[0]?.$message }}</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Last Name" label-for="new-last-name">
          <BFormInput
            id="new-last-name"
            v-model="newForm.last_name"
            :state="validationState(vNew$.last_name)"
          />
          <BFormInvalidFeedback>{{ vNew$.last_name.$errors[0]?.$message }}</BFormInvalidFeedback>
        </BFormGroup>
      </BForm>
    </BModal>

    <BModal
      ref="editModal"
      title="Edit Crew Member"
      :ok-disabled="isSubmitting"
      @hidden="resetEdit"
      @ok.prevent="submitEdit"
    >
      <BForm>
        <BFormGroup label="First Name" label-for="edit-first-name">
          <BFormInput
            id="edit-first-name"
            v-model="editForm.first_name"
            :state="validationState(vEdit$.first_name)"
          />
          <BFormInvalidFeedback>{{ vEdit$.first_name.$errors[0]?.$message }}</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Last Name" label-for="edit-last-name">
          <BFormInput
            id="edit-last-name"
            v-model="editForm.last_name"
            :state="validationState(vEdit$.last_name)"
          />
          <BFormInvalidFeedback>{{ vEdit$.last_name.$errors[0]?.$message }}</BFormInvalidFeedback>
        </BFormGroup>
      </BForm>
    </BModal>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import { useVuelidate } from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import { useStageStore } from '@/stores/stage';
import { useSystemStore } from '@/stores/system';
import { useConfirm } from '@/composables/useConfirm';
import { useFormValidation } from '@/composables/useFormValidation';
import type { Crew } from '@/types/api/stage';
import log from 'loglevel';

const stageStore = useStageStore();
const systemStore = useSystemStore();
const { confirm } = useConfirm();
const { validationState } = useFormValidation();

const rowsPerPage = 15;
const currentPage = ref(1);
const isSubmitting = ref(false);

const newModal = ref<InstanceType<typeof BModal>>();
const editModal = ref<InstanceType<typeof BModal>>();

const newForm = ref({ first_name: '', last_name: '' });
const editForm = ref({ id: null as number | null, first_name: '', last_name: '' });

const fields = [
  { key: 'first_name', label: 'First Name' },
  { key: 'last_name', label: 'Last Name' },
  { key: 'btn', label: '' },
];

const vNew$ = useVuelidate({ first_name: { required }, last_name: { required } }, newForm);
const vEdit$ = useVuelidate({ first_name: { required }, last_name: { required } }, editForm);

function openEdit(crew: Crew): void {
  editForm.value = { id: crew.id, first_name: crew.first_name, last_name: crew.last_name ?? '' };
  editModal.value?.show();
}

function resetNew(): void {
  newForm.value = { first_name: '', last_name: '' };
  isSubmitting.value = false;
  vNew$.value.$reset();
}

function resetEdit(): void {
  editForm.value = { id: null, first_name: '', last_name: '' };
  isSubmitting.value = false;
  vEdit$.value.$reset();
}

async function submitNew(): Promise<void> {
  const valid = await vNew$.value.$validate();
  if (!valid || isSubmitting.value) return;
  isSubmitting.value = true;
  try {
    await stageStore.addCrewMember({
      first_name: newForm.value.first_name,
      last_name: newForm.value.last_name || null,
    });
    newModal.value?.hide();
  } catch (e) {
    log.error('Error adding crew member:', e);
  } finally {
    isSubmitting.value = false;
  }
}

async function submitEdit(): Promise<void> {
  const valid = await vEdit$.value.$validate();
  if (!valid || isSubmitting.value) return;
  isSubmitting.value = true;
  try {
    await stageStore.updateCrewMember({
      id: editForm.value.id!,
      first_name: editForm.value.first_name,
      last_name: editForm.value.last_name || null,
    });
    editModal.value?.hide();
  } catch (e) {
    log.error('Error updating crew member:', e);
  } finally {
    isSubmitting.value = false;
  }
}

async function confirmDelete(crew: Crew): Promise<void> {
  const name = [crew.first_name, crew.last_name].filter(Boolean).join(' ');
  const ok = await confirm(`Are you sure you want to delete ${name}?`, {
    title: 'Delete Crew Member',
    okVariant: 'danger',
    okTitle: 'Delete',
  });
  if (!ok) return;
  try {
    await stageStore.deleteCrewMember(crew.id);
  } catch (e) {
    log.error('Error deleting crew member:', e);
  }
}

onMounted(async () => {
  await stageStore.getCrewList();
});
</script>
