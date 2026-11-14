<template>
  <BContainer class="mx-0" fluid>
    <BRow>
      <BCol cols="5">
        <h5>Prop Types</h5>
        <BTable
          :items="stageStore.propTypes"
          :fields="propTypeFields"
          :per-page="propTypesPerPage"
          :current-page="currentPropTypesPage"
          show-empty
        >
          <template #head(btn)>
            <BButton
              v-if="systemStore.isShowEditor"
              variant="outline-success"
              @click="newPropTypeModal?.show()"
            >
              New Prop Type
            </BButton>
          </template>
          <template #cell(btn)="data">
            <BButtonGroup v-if="systemStore.isShowEditor">
              <BButton
                variant="warning"
                :disabled="isSubmitting"
                @click="openEditPropType(data.item)"
              >
                Edit
              </BButton>
              <BButton
                variant="danger"
                :disabled="isSubmitting"
                @click="confirmDeletePropType(data.item)"
              >
                Delete
              </BButton>
            </BButtonGroup>
          </template>
        </BTable>
        <PaginationControls
          v-model:per-page="propTypesPerPage"
          v-model:current-page="currentPropTypesPage"
          :total-rows="stageStore.propTypes.length"
        />
      </BCol>
      <BCol cols="7">
        <h5>Props List</h5>
        <BTable
          :items="stageStore.propsList"
          :fields="propsFields"
          :per-page="propsPerPage"
          :current-page="currentPropsPage"
          show-empty
        >
          <template #head(btn)>
            <BButton
              v-if="systemStore.isShowEditor"
              variant="outline-success"
              @click="newPropModal?.show()"
            >
              New Props Item
            </BButton>
          </template>
          <template #cell(prop_type_id)="data">
            <span>{{ stageStore.propTypeById(data.item.prop_type_id)?.name }}</span>
          </template>
          <template #cell(btn)="data">
            <BButtonGroup v-if="systemStore.isShowEditor">
              <BButton variant="warning" :disabled="isSubmitting" @click="openEditProp(data.item)">
                Edit
              </BButton>
              <BButton
                variant="danger"
                :disabled="isSubmitting"
                @click="confirmDeleteProp(data.item)"
              >
                Delete
              </BButton>
            </BButtonGroup>
          </template>
        </BTable>
        <PaginationControls
          v-model:per-page="propsPerPage"
          v-model:current-page="currentPropsPage"
          :total-rows="stageStore.propsList.length"
        />
      </BCol>
    </BRow>

    <BModal
      ref="newPropTypeModal"
      title="Add New Prop Type"
      :ok-disabled="isSubmitting"
      @hidden="resetNewPropType"
      @ok.prevent="submitNewPropType"
    >
      <BForm>
        <BFormGroup label="Name" label-for="new-ptype-name">
          <BFormInput
            id="new-ptype-name"
            v-model="newPropTypeForm.name"
            :state="validationState(vNewPropType$.name)"
          />
          <BFormInvalidFeedback>{{ vNewPropType$.name.$errors[0]?.$message }}</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Description" label-for="new-ptype-desc">
          <BFormInput id="new-ptype-desc" v-model="newPropTypeForm.description" />
        </BFormGroup>
      </BForm>
    </BModal>

    <BModal
      ref="editPropTypeModal"
      title="Edit Prop Type"
      :ok-disabled="isSubmitting"
      @hidden="resetEditPropType"
      @ok.prevent="submitEditPropType"
    >
      <BForm>
        <BFormGroup label="Name" label-for="edit-ptype-name">
          <BFormInput
            id="edit-ptype-name"
            v-model="editPropTypeForm.name"
            :state="validationState(vEditPropType$.name)"
          />
          <BFormInvalidFeedback>
            {{ vEditPropType$.name.$errors[0]?.$message }}
          </BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Description" label-for="edit-ptype-desc">
          <BFormInput id="edit-ptype-desc" v-model="editPropTypeForm.description" />
        </BFormGroup>
      </BForm>
    </BModal>

    <BModal
      ref="newPropModal"
      title="Add New Prop"
      :ok-disabled="isSubmitting"
      @hidden="resetNewProp"
      @ok.prevent="submitNewProp"
    >
      <BForm>
        <BFormGroup label="Prop Type" label-for="new-prop-type-sel">
          <BFormSelect
            id="new-prop-type-sel"
            v-model="newPropForm.prop_type_id"
            :options="propTypeOptions"
            :state="validationState(vNewProp$.prop_type_id)"
          />
          <BFormInvalidFeedback>
            {{ vNewProp$.prop_type_id.$errors[0]?.$message }}
          </BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Name" label-for="new-prop-name">
          <BFormInput
            id="new-prop-name"
            v-model="newPropForm.name"
            :state="validationState(vNewProp$.name)"
          />
          <BFormInvalidFeedback>{{ vNewProp$.name.$errors[0]?.$message }}</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Description" label-for="new-prop-desc">
          <BFormInput id="new-prop-desc" v-model="newPropForm.description" />
        </BFormGroup>
      </BForm>
    </BModal>

    <BModal
      ref="editPropModal"
      title="Edit Prop"
      :ok-disabled="isSubmitting"
      @hidden="resetEditProp"
      @ok.prevent="submitEditProp"
    >
      <BForm>
        <BFormGroup label="Prop Type" label-for="edit-prop-type-sel">
          <BFormSelect
            id="edit-prop-type-sel"
            v-model="editPropForm.prop_type_id"
            :options="propTypeOptions"
            :state="validationState(vEditProp$.prop_type_id)"
          />
          <BFormInvalidFeedback>
            {{ vEditProp$.prop_type_id.$errors[0]?.$message }}
          </BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Name" label-for="edit-prop-name">
          <BFormInput
            id="edit-prop-name"
            v-model="editPropForm.name"
            :state="validationState(vEditProp$.name)"
          />
          <BFormInvalidFeedback>{{ vEditProp$.name.$errors[0]?.$message }}</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Description" label-for="edit-prop-desc">
          <BFormInput id="edit-prop-desc" v-model="editPropForm.description" />
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
import type { PropType, Props } from '@/types/api/stage';
import log from 'loglevel';

const stageStore = useStageStore();
const systemStore = useSystemStore();
const { confirm } = useConfirm();
const { validationState } = useFormValidation();

const { perPage: propTypesPerPage, currentPage: currentPropTypesPage } = usePagination(
  15,
  'config_prop_types'
);
const { perPage: propsPerPage, currentPage: currentPropsPage } = usePagination(15, 'config_props');
const isSubmitting = ref(false);

const newPropTypeModal = ref<InstanceType<typeof BModal>>();
const editPropTypeModal = ref<InstanceType<typeof BModal>>();
const newPropModal = ref<InstanceType<typeof BModal>>();
const editPropModal = ref<InstanceType<typeof BModal>>();

const newPropTypeForm = ref({ name: '', description: '' });
const editPropTypeForm = ref({ id: null as number | null, name: '', description: '' });
const newPropForm = ref({ name: '', description: '', prop_type_id: null as number | null });
const editPropForm = ref({
  id: null as number | null,
  name: '',
  description: '',
  prop_type_id: null as number | null,
});

const propTypeFields = [
  { key: 'name', label: 'Name' },
  { key: 'description', label: 'Description' },
  { key: 'btn', label: '' },
];
const propsFields = [
  { key: 'name', label: 'Name' },
  { key: 'description', label: 'Description' },
  { key: 'prop_type_id', label: 'Prop Type' },
  { key: 'btn', label: '' },
];

const propTypeOptions = computed(() => [
  { value: null, text: 'Please select an option', disabled: true },
  ...stageStore.propTypes.map((t) => ({ value: t.id, text: t.name })),
]);

const notNull = helpers.withMessage('This is a required field.', (v: unknown) => v !== null);

const vNewPropType$ = useVuelidate({ name: { required } }, newPropTypeForm);
const vEditPropType$ = useVuelidate({ name: { required } }, editPropTypeForm);
const vNewProp$ = useVuelidate(
  { name: { required }, prop_type_id: { required, notNull } },
  newPropForm
);
const vEditProp$ = useVuelidate(
  { name: { required }, prop_type_id: { required, notNull } },
  editPropForm
);

function openEditPropType(type: PropType): void {
  editPropTypeForm.value = { id: type.id, name: type.name, description: type.description ?? '' };
  editPropTypeModal.value?.show();
}

function openEditProp(prop: Props): void {
  editPropForm.value = {
    id: prop.id,
    name: prop.name,
    description: prop.description ?? '',
    prop_type_id: prop.prop_type_id,
  };
  editPropModal.value?.show();
}

function resetNewPropType(): void {
  newPropTypeForm.value = { name: '', description: '' };
  isSubmitting.value = false;
  vNewPropType$.value.$reset();
}

function resetEditPropType(): void {
  editPropTypeForm.value = { id: null, name: '', description: '' };
  isSubmitting.value = false;
  vEditPropType$.value.$reset();
}

function resetNewProp(): void {
  newPropForm.value = { name: '', description: '', prop_type_id: null };
  isSubmitting.value = false;
  vNewProp$.value.$reset();
}

function resetEditProp(): void {
  editPropForm.value = { id: null, name: '', description: '', prop_type_id: null };
  isSubmitting.value = false;
  vEditProp$.value.$reset();
}

async function submitNewPropType(): Promise<void> {
  const valid = await vNewPropType$.value.$validate();
  if (!valid || isSubmitting.value) return;
  isSubmitting.value = true;
  try {
    await stageStore.addPropType({
      name: newPropTypeForm.value.name,
      description: newPropTypeForm.value.description || null,
    });
    newPropTypeModal.value?.hide();
  } catch (e) {
    log.error('Error adding prop type:', e);
  } finally {
    isSubmitting.value = false;
  }
}

async function submitEditPropType(): Promise<void> {
  const valid = await vEditPropType$.value.$validate();
  if (!valid || isSubmitting.value) return;
  isSubmitting.value = true;
  try {
    await stageStore.updatePropType({
      id: editPropTypeForm.value.id!,
      name: editPropTypeForm.value.name,
      description: editPropTypeForm.value.description || null,
    });
    editPropTypeModal.value?.hide();
  } catch (e) {
    log.error('Error updating prop type:', e);
  } finally {
    isSubmitting.value = false;
  }
}

async function submitNewProp(): Promise<void> {
  const valid = await vNewProp$.value.$validate();
  if (!valid || isSubmitting.value) return;
  isSubmitting.value = true;
  try {
    await stageStore.addProp({
      name: newPropForm.value.name,
      description: newPropForm.value.description || null,
      prop_type_id: newPropForm.value.prop_type_id!,
    });
    newPropModal.value?.hide();
  } catch (e) {
    log.error('Error adding prop:', e);
  } finally {
    isSubmitting.value = false;
  }
}

async function submitEditProp(): Promise<void> {
  const valid = await vEditProp$.value.$validate();
  if (!valid || isSubmitting.value) return;
  isSubmitting.value = true;
  try {
    await stageStore.updateProp({
      id: editPropForm.value.id!,
      name: editPropForm.value.name,
      description: editPropForm.value.description || null,
      prop_type_id: editPropForm.value.prop_type_id!,
    });
    editPropModal.value?.hide();
  } catch (e) {
    log.error('Error updating prop:', e);
  } finally {
    isSubmitting.value = false;
  }
}

async function confirmDeletePropType(type: PropType): Promise<void> {
  const itemCount = stageStore.propsList.filter((p) => p.prop_type_id === type.id).length;
  let msg = `Are you sure you want to delete ${type.name}?`;
  if (itemCount > 0) msg += ` This will also delete ${itemCount} props.`;
  const ok = await confirm(msg, {
    title: 'Delete Prop Type',
    okVariant: 'danger',
    okTitle: 'Delete',
  });
  if (!ok) return;
  try {
    await stageStore.deletePropType(type.id);
  } catch (e) {
    log.error('Error deleting prop type:', e);
  }
}

async function confirmDeleteProp(prop: Props): Promise<void> {
  const ok = await confirm(`Are you sure you want to delete ${prop.name}?`, {
    title: 'Delete Prop',
    okVariant: 'danger',
    okTitle: 'Delete',
  });
  if (!ok) return;
  try {
    await stageStore.deleteProp(prop.id);
  } catch (e) {
    log.error('Error deleting prop:', e);
  }
}

onMounted(async () => {
  await Promise.all([stageStore.getPropTypes(), stageStore.getPropsList()]);
});
</script>
