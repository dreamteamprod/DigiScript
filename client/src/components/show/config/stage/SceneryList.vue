<template>
  <BContainer class="mx-0" fluid>
    <BRow>
      <BCol cols="5">
        <h5>Scenery Types</h5>
        <BTable
          :items="stageStore.sceneryTypes"
          :fields="sceneryTypeFields"
          :per-page="sceneryTypesPerPage"
          :current-page="currentSceneryTypesPage"
          show-empty
        >
          <template #head(btn)>
            <BButton
              v-if="systemStore.isShowEditor"
              variant="outline-success"
              @click="newSceneryTypeModal?.show()"
            >
              New Scenery Type
            </BButton>
          </template>
          <template #cell(btn)="data">
            <BButtonGroup v-if="systemStore.isShowEditor">
              <BButton
                variant="warning"
                :disabled="isSubmitting"
                @click="openEditSceneryType(data.item)"
              >
                Edit
              </BButton>
              <BButton
                variant="danger"
                :disabled="isSubmitting"
                @click="confirmDeleteSceneryType(data.item)"
              >
                Delete
              </BButton>
            </BButtonGroup>
          </template>
        </BTable>
        <PaginationControls
          v-model:per-page="sceneryTypesPerPage"
          v-model:current-page="currentSceneryTypesPage"
          :total-rows="stageStore.sceneryTypes.length"
        />
      </BCol>
      <BCol cols="7">
        <h5>Scenery List</h5>
        <BTable
          :items="stageStore.sceneryList"
          :fields="sceneryFields"
          :per-page="sceneryPerPage"
          :current-page="currentSceneryPage"
          show-empty
        >
          <template #head(btn)>
            <BButton
              v-if="systemStore.isShowEditor"
              variant="outline-success"
              @click="newSceneryModal?.show()"
            >
              New Scenery Item
            </BButton>
          </template>
          <template #cell(scenery_type_id)="data">
            <span>{{ stageStore.sceneryTypeById(data.item.scenery_type_id)?.name }}</span>
          </template>
          <template #cell(btn)="data">
            <BButtonGroup v-if="systemStore.isShowEditor">
              <BButton
                variant="warning"
                :disabled="isSubmitting"
                @click="openEditScenery(data.item)"
              >
                Edit
              </BButton>
              <BButton
                variant="danger"
                :disabled="isSubmitting"
                @click="confirmDeleteScenery(data.item)"
              >
                Delete
              </BButton>
            </BButtonGroup>
          </template>
        </BTable>
        <PaginationControls
          v-model:per-page="sceneryPerPage"
          v-model:current-page="currentSceneryPage"
          :total-rows="stageStore.sceneryList.length"
        />
      </BCol>
    </BRow>

    <BModal
      ref="newSceneryTypeModal"
      title="Add New Scenery Type"
      :ok-disabled="isSubmitting"
      @hidden="resetNewSceneryType"
      @ok.prevent="submitNewSceneryType"
    >
      <BForm>
        <BFormGroup label="Name" label-for="new-stype-name">
          <BFormInput
            id="new-stype-name"
            v-model="newSceneryTypeForm.name"
            :state="validationState(vNewType$.name)"
          />
          <BFormInvalidFeedback>{{ vNewType$.name.$errors[0]?.$message }}</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Description" label-for="new-stype-desc">
          <BFormInput id="new-stype-desc" v-model="newSceneryTypeForm.description" />
        </BFormGroup>
      </BForm>
    </BModal>

    <BModal
      ref="editSceneryTypeModal"
      title="Edit Scenery Type"
      :ok-disabled="isSubmitting"
      @hidden="resetEditSceneryType"
      @ok.prevent="submitEditSceneryType"
    >
      <BForm>
        <BFormGroup label="Name" label-for="edit-stype-name">
          <BFormInput
            id="edit-stype-name"
            v-model="editSceneryTypeForm.name"
            :state="validationState(vEditType$.name)"
          />
          <BFormInvalidFeedback>{{ vEditType$.name.$errors[0]?.$message }}</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Description" label-for="edit-stype-desc">
          <BFormInput id="edit-stype-desc" v-model="editSceneryTypeForm.description" />
        </BFormGroup>
      </BForm>
    </BModal>

    <BModal
      ref="newSceneryModal"
      title="Add New Scenery"
      :ok-disabled="isSubmitting"
      @hidden="resetNewScenery"
      @ok.prevent="submitNewScenery"
    >
      <BForm>
        <BFormGroup label="Scenery Type" label-for="new-scenery-type-sel">
          <BFormSelect
            id="new-scenery-type-sel"
            v-model="newSceneryForm.scenery_type_id"
            :options="sceneryTypeOptions"
            :state="validationState(vNewScenery$.scenery_type_id)"
          />
          <BFormInvalidFeedback>
            {{ vNewScenery$.scenery_type_id.$errors[0]?.$message }}
          </BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Name" label-for="new-scenery-name">
          <BFormInput
            id="new-scenery-name"
            v-model="newSceneryForm.name"
            :state="validationState(vNewScenery$.name)"
          />
          <BFormInvalidFeedback>{{ vNewScenery$.name.$errors[0]?.$message }}</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Description" label-for="new-scenery-desc">
          <BFormInput id="new-scenery-desc" v-model="newSceneryForm.description" />
        </BFormGroup>
      </BForm>
    </BModal>

    <BModal
      ref="editSceneryModal"
      title="Edit Scenery"
      :ok-disabled="isSubmitting"
      @hidden="resetEditScenery"
      @ok.prevent="submitEditScenery"
    >
      <BForm>
        <BFormGroup label="Scenery Type" label-for="edit-scenery-type-sel">
          <BFormSelect
            id="edit-scenery-type-sel"
            v-model="editSceneryForm.scenery_type_id"
            :options="sceneryTypeOptions"
            :state="validationState(vEditScenery$.scenery_type_id)"
          />
          <BFormInvalidFeedback>
            {{ vEditScenery$.scenery_type_id.$errors[0]?.$message }}
          </BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Name" label-for="edit-scenery-name">
          <BFormInput
            id="edit-scenery-name"
            v-model="editSceneryForm.name"
            :state="validationState(vEditScenery$.name)"
          />
          <BFormInvalidFeedback>{{ vEditScenery$.name.$errors[0]?.$message }}</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Description" label-for="edit-scenery-desc">
          <BFormInput id="edit-scenery-desc" v-model="editSceneryForm.description" />
        </BFormGroup>
      </BForm>
    </BModal>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import { useVuelidate } from '@vuelidate/core';
import { required, helpers } from '@vuelidate/validators';
import { useStageStore } from '@/stores/stage';
import { useSystemStore } from '@/stores/system';
import { useConfirm } from '@/composables/useConfirm';
import { usePagination } from '@/composables/usePagination';
import { useFormValidation } from '@/composables/useFormValidation';
import type { SceneryType, Scenery } from '@/types/api/stage';
import log from 'loglevel';

const stageStore = useStageStore();
const systemStore = useSystemStore();
const { confirm } = useConfirm();
const { validationState } = useFormValidation();

const { perPage: sceneryTypesPerPage, currentPage: currentSceneryTypesPage } = usePagination(
  15,
  'config_scenery_types'
);
const { perPage: sceneryPerPage, currentPage: currentSceneryPage } = usePagination(
  15,
  'config_scenery'
);
const isSubmitting = ref(false);

const newSceneryTypeModal = ref<InstanceType<typeof BModal>>();
const editSceneryTypeModal = ref<InstanceType<typeof BModal>>();
const newSceneryModal = ref<InstanceType<typeof BModal>>();
const editSceneryModal = ref<InstanceType<typeof BModal>>();

const newSceneryTypeForm = ref({ name: '', description: '' });
const editSceneryTypeForm = ref({ id: null as number | null, name: '', description: '' });
const newSceneryForm = ref({
  name: '',
  description: '',
  scenery_type_id: null as number | null,
});
const editSceneryForm = ref({
  id: null as number | null,
  name: '',
  description: '',
  scenery_type_id: null as number | null,
});

const sceneryTypeFields = [
  { key: 'name', label: 'Name' },
  { key: 'description', label: 'Description' },
  { key: 'btn', label: '' },
];
const sceneryFields = [
  { key: 'name', label: 'Name' },
  { key: 'description', label: 'Description' },
  { key: 'scenery_type_id', label: 'Scenery Type' },
  { key: 'btn', label: '' },
];

const sceneryTypeOptions = computed(() => [
  { value: null, text: 'Please select an option', disabled: true },
  ...stageStore.sceneryTypes.map((t) => ({ value: t.id, text: t.name })),
]);

const notNull = helpers.withMessage('This is a required field.', (v: unknown) => v !== null);

const vNewType$ = useVuelidate({ name: { required } }, newSceneryTypeForm);
const vEditType$ = useVuelidate({ name: { required } }, editSceneryTypeForm);
const vNewScenery$ = useVuelidate(
  { name: { required }, scenery_type_id: { required, notNull } },
  newSceneryForm
);
const vEditScenery$ = useVuelidate(
  { name: { required }, scenery_type_id: { required, notNull } },
  editSceneryForm
);

function openEditSceneryType(type: SceneryType): void {
  editSceneryTypeForm.value = { id: type.id, name: type.name, description: type.description ?? '' };
  editSceneryTypeModal.value?.show();
}

function openEditScenery(scenery: Scenery): void {
  editSceneryForm.value = {
    id: scenery.id,
    name: scenery.name,
    description: scenery.description ?? '',
    scenery_type_id: scenery.scenery_type_id,
  };
  editSceneryModal.value?.show();
}

function resetNewSceneryType(): void {
  newSceneryTypeForm.value = { name: '', description: '' };
  isSubmitting.value = false;
  vNewType$.value.$reset();
}

function resetEditSceneryType(): void {
  editSceneryTypeForm.value = { id: null, name: '', description: '' };
  isSubmitting.value = false;
  vEditType$.value.$reset();
}

function resetNewScenery(): void {
  newSceneryForm.value = { name: '', description: '', scenery_type_id: null };
  isSubmitting.value = false;
  vNewScenery$.value.$reset();
}

function resetEditScenery(): void {
  editSceneryForm.value = { id: null, name: '', description: '', scenery_type_id: null };
  isSubmitting.value = false;
  vEditScenery$.value.$reset();
}

async function submitNewSceneryType(): Promise<void> {
  const valid = await vNewType$.value.$validate();
  if (!valid || isSubmitting.value) return;
  isSubmitting.value = true;
  try {
    await stageStore.addSceneryType({
      name: newSceneryTypeForm.value.name,
      description: newSceneryTypeForm.value.description || null,
    });
    newSceneryTypeModal.value?.hide();
  } catch (e) {
    log.error('Error adding scenery type:', e);
  } finally {
    isSubmitting.value = false;
  }
}

async function submitEditSceneryType(): Promise<void> {
  const valid = await vEditType$.value.$validate();
  if (!valid || isSubmitting.value) return;
  isSubmitting.value = true;
  try {
    await stageStore.updateSceneryType({
      id: editSceneryTypeForm.value.id!,
      name: editSceneryTypeForm.value.name,
      description: editSceneryTypeForm.value.description || null,
    });
    editSceneryTypeModal.value?.hide();
  } catch (e) {
    log.error('Error updating scenery type:', e);
  } finally {
    isSubmitting.value = false;
  }
}

async function submitNewScenery(): Promise<void> {
  const valid = await vNewScenery$.value.$validate();
  if (!valid || isSubmitting.value) return;
  isSubmitting.value = true;
  try {
    await stageStore.addScenery({
      name: newSceneryForm.value.name,
      description: newSceneryForm.value.description || null,
      scenery_type_id: newSceneryForm.value.scenery_type_id!,
    });
    newSceneryModal.value?.hide();
  } catch (e) {
    log.error('Error adding scenery:', e);
  } finally {
    isSubmitting.value = false;
  }
}

async function submitEditScenery(): Promise<void> {
  const valid = await vEditScenery$.value.$validate();
  if (!valid || isSubmitting.value) return;
  isSubmitting.value = true;
  try {
    await stageStore.updateScenery({
      id: editSceneryForm.value.id!,
      name: editSceneryForm.value.name,
      description: editSceneryForm.value.description || null,
      scenery_type_id: editSceneryForm.value.scenery_type_id!,
    });
    editSceneryModal.value?.hide();
  } catch (e) {
    log.error('Error updating scenery:', e);
  } finally {
    isSubmitting.value = false;
  }
}

async function confirmDeleteSceneryType(type: SceneryType): Promise<void> {
  const itemCount = stageStore.sceneryList.filter((s) => s.scenery_type_id === type.id).length;
  let msg = `Are you sure you want to delete ${type.name}?`;
  if (itemCount > 0) msg += ` This will also delete ${itemCount} scenery items.`;
  const ok = await confirm(msg, {
    title: 'Delete Scenery Type',
    okVariant: 'danger',
    okTitle: 'Delete',
  });
  if (!ok) return;
  try {
    await stageStore.deleteSceneryType(type.id);
  } catch (e) {
    log.error('Error deleting scenery type:', e);
  }
}

async function confirmDeleteScenery(scenery: Scenery): Promise<void> {
  const ok = await confirm(`Are you sure you want to delete ${scenery.name}?`, {
    title: 'Delete Scenery',
    okVariant: 'danger',
    okTitle: 'Delete',
  });
  if (!ok) return;
  try {
    await stageStore.deleteScenery(scenery.id);
  } catch (e) {
    log.error('Error deleting scenery:', e);
  }
}

onMounted(async () => {
  await Promise.all([stageStore.getSceneryTypes(), stageStore.getSceneryList()]);
});
</script>
