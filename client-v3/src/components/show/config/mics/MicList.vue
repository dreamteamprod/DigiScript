<template>
  <BContainer class="mx-0" fluid>
    <BRow>
      <BCol>
        <BTable
          :items="showStore.microphones"
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
              Add Microphone
            </BButton>
          </template>
          <template #cell(btn)="data">
            <BButtonGroup v-if="systemStore.isShowEditor">
              <BButton variant="warning" :disabled="isSubmitting" @click="openEdit(data.item)">
                Edit
              </BButton>
              <BButton
                variant="danger"
                :disabled="isSubmitting"
                @click="confirmDelete(data.item.id)"
              >
                Delete
              </BButton>
            </BButtonGroup>
          </template>
        </BTable>
        <BPagination
          v-if="showStore.microphones.length > rowsPerPage"
          v-model="currentPage"
          :total-rows="showStore.microphones.length"
          :per-page="rowsPerPage"
        />
      </BCol>
    </BRow>

    <!-- New microphone modal -->
    <BModal
      ref="newModal"
      title="Add Microphone"
      :ok-disabled="isSubmitting"
      @hidden="resetNew"
      @ok.prevent="submitNew"
    >
      <BForm>
        <BFormGroup label="Name" label-for="new-name">
          <BFormInput id="new-name" v-model="newForm.name" :state="validationState(vNew$.name)" />
          <BFormInvalidFeedback>{{ vNew$.name.$errors[0]?.$message }}</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Description" label-for="new-desc">
          <BFormInput id="new-desc" v-model="newForm.description" />
        </BFormGroup>
      </BForm>
    </BModal>

    <!-- Edit microphone modal -->
    <BModal
      ref="editModal"
      title="Edit Microphone"
      :ok-disabled="isSubmitting"
      @hidden="resetEdit"
      @ok.prevent="submitEdit"
    >
      <BForm>
        <BFormGroup label="Name" label-for="edit-name">
          <BFormInput
            id="edit-name"
            v-model="editForm.name"
            :state="validationState(vEdit$.name)"
          />
          <BFormInvalidFeedback>{{ vEdit$.name.$errors[0]?.$message }}</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Description" label-for="edit-desc">
          <BFormInput id="edit-desc" v-model="editForm.description" />
        </BFormGroup>
      </BForm>
    </BModal>
  </BContainer>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import { useVuelidate } from '@vuelidate/core';
import { required, helpers } from '@vuelidate/validators';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import { useConfirm } from '@/composables/useConfirm';
import { useFormValidation } from '@/composables/useFormValidation';
import type { Microphone } from '@/types/api/microphones';
import log from 'loglevel';

const showStore = useShowStore();
const systemStore = useSystemStore();
const { confirm } = useConfirm();
const { validationState } = useFormValidation();

const rowsPerPage = 15;
const currentPage = ref(1);
const isSubmitting = ref(false);

const newModal = ref<InstanceType<typeof BModal>>();
const editModal = ref<InstanceType<typeof BModal>>();

const newForm = ref({ name: '', description: '' });
const editForm = ref({ id: null as number | null, name: '', description: '' });

const uniqueNewName = helpers.withMessage(
  'A microphone with this name already exists',
  (value: string) =>
    !showStore.microphones.some((m) => m.name?.toLowerCase() === value.toLowerCase())
);
const uniqueEditName = helpers.withMessage(
  'A microphone with this name already exists',
  (value: string) =>
    !showStore.microphones.some(
      (m) => m.name?.toLowerCase() === value.toLowerCase() && m.id !== editForm.value.id
    )
);

const vNew$ = useVuelidate({ name: { required, uniqueNewName } }, newForm);
const vEdit$ = useVuelidate({ name: { required, uniqueEditName } }, editForm);

const fields = [
  { key: 'name', label: 'Name' },
  { key: 'description', label: 'Description' },
  { key: 'btn', label: '' },
];

function openEdit(mic: Microphone): void {
  editForm.value = { id: mic.id, name: mic.name ?? '', description: mic.description ?? '' };
  editModal.value?.show();
}

function resetNew(): void {
  newForm.value = { name: '', description: '' };
  isSubmitting.value = false;
  vNew$.value.$reset();
}

function resetEdit(): void {
  editForm.value = { id: null, name: '', description: '' };
  isSubmitting.value = false;
  vEdit$.value.$reset();
}

async function submitNew(): Promise<void> {
  const valid = await vNew$.value.$validate();
  if (!valid || isSubmitting.value) return;
  isSubmitting.value = true;
  try {
    await showStore.addMicrophone({
      name: newForm.value.name,
      description: newForm.value.description,
    });
    newModal.value?.hide();
  } catch (e) {
    log.error('Error adding microphone:', e);
  } finally {
    isSubmitting.value = false;
  }
}

async function submitEdit(): Promise<void> {
  const valid = await vEdit$.value.$validate();
  if (!valid || isSubmitting.value) return;
  isSubmitting.value = true;
  try {
    await showStore.updateMicrophone({
      id: editForm.value.id,
      name: editForm.value.name,
      description: editForm.value.description,
    });
    editModal.value?.hide();
  } catch (e) {
    log.error('Error updating microphone:', e);
  } finally {
    isSubmitting.value = false;
  }
}

async function confirmDelete(id: number): Promise<void> {
  const ok = await confirm('Are you sure you want to delete this microphone?', {
    title: 'Delete Microphone',
    okVariant: 'danger',
    okTitle: 'Delete',
  });
  if (!ok) return;
  try {
    await showStore.deleteMicrophone(id);
  } catch (e) {
    log.error('Error deleting microphone:', e);
  }
}
</script>
