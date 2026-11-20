<template>
  <BContainer id="show-config" class="mx-0" fluid>
    <BRow>
      <BCol cols="12" class="text-end">
        <BButton
          v-if="systemStore.isShowEditor"
          variant="warning"
          :disabled="submittingEditShow"
          @click="openEditForm"
        >
          Edit Show
        </BButton>
      </BCol>
    </BRow>
    <BRow>
      <BCol>
        <BTableSimple class="w-100">
          <BTbody>
            <BTr v-for="key in orderedKeys" :key="key">
              <BTh>{{ key }}</BTh>
              <BTd>{{ tableData[key] != null ? tableData[key] : 'N/A' }}</BTd>
            </BTr>
          </BTbody>
        </BTableSimple>
      </BCol>
    </BRow>

    <BModal
      ref="editShowModal"
      title="Edit Show"
      size="md"
      :ok-disabled="v$.editFormState.$invalid || submittingEditShow"
      @hide="resetEditForm"
      @ok="onSubmitEdit"
    >
      <BForm @submit.stop.prevent="onSubmitEdit">
        <BFormGroup label="Name" label-for="name-input" label-cols="4">
          <BFormInput id="name-input" v-model="editFormState.name" :state="fieldState('name')" />
          <BFormInvalidFeedback>
            This is a required field and must be less than 100 characters.
          </BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Start Date" label-for="start-input" label-cols="4">
          <BFormInput
            id="start-input"
            v-model="editFormState.start_date"
            type="date"
            :state="fieldState('start_date')"
          />
          <BFormInvalidFeedback>
            This is a required field and must be before or the same as the end date.
          </BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="End Date" label-for="end-input" label-cols="4">
          <BFormInput
            id="end-input"
            v-model="editFormState.end_date"
            type="date"
            :state="fieldState('end_date')"
          />
          <BFormInvalidFeedback>
            This is a required field and must be after or the same as the start date.
          </BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Act" label-for="act-input" label-cols="4">
          <BFormSelect id="act-input" v-model="editFormState.first_act_id" :options="actOptions" />
        </BFormGroup>
      </BForm>
    </BModal>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useVuelidate } from '@vuelidate/core';
import { required, maxLength, helpers } from '@vuelidate/validators';
import { BModal } from 'bootstrap-vue-next';
import log from 'loglevel';
import { titleCase } from '@/js/utils';
import { useSystemStore } from '@/stores/system';
import { useShowStore } from '@/stores/show';

const systemStore = useSystemStore();
const showStore = useShowStore();

const submittingEditShow = ref(false);
const editShowModal = ref<InstanceType<typeof BModal>>();

interface EditShowForm {
  name: string | null;
  start_date: string | null;
  end_date: string | null;
  first_act_id: number | null;
}

const editFormState = ref<EditShowForm>({
  name: null,
  start_date: null,
  end_date: null,
  first_act_id: null,
});

const beforeEnd = helpers.withMessage(
  'Start date must be before or the same as end date',
  () =>
    !editFormState.value.start_date ||
    !editFormState.value.end_date ||
    new Date(editFormState.value.start_date) <= new Date(editFormState.value.end_date)
);

const afterStart = helpers.withMessage(
  'End date must be after or the same as start date',
  () =>
    !editFormState.value.start_date ||
    !editFormState.value.end_date ||
    new Date(editFormState.value.end_date) >= new Date(editFormState.value.start_date)
);

const rules = {
  editFormState: {
    name: { required, maxLength: maxLength(100) },
    start_date: { required, beforeEnd },
    end_date: { required, afterStart },
    first_act_id: {},
  },
};

const v$ = useVuelidate(rules, { editFormState });

const tableData = computed((): Record<string, unknown> => {
  const show = systemStore.currentShow;
  if (!show) return {};
  const data: Record<string, unknown> = {};
  for (const key of Object.keys(show)) {
    data[titleCase(key, '_')] = (show as Record<string, unknown>)[key];
  }
  return data;
});

const orderedKeys = computed(() => Object.keys(tableData.value).sort());

const actOptions = computed(() => [
  { value: null, text: 'N/A', disabled: false },
  ...showStore.actList.map((act) => ({ value: act.id, text: act.name })),
]);

function fieldState(key: keyof EditShowForm): boolean | null {
  const field = v$.value.editFormState[key];
  if (!field) return null;
  return field.$dirty ? !field.$error : null;
}

function resetEditForm(): void {
  editFormState.value = { name: null, start_date: null, end_date: null, first_act_id: null };
  submittingEditShow.value = false;
  v$.value.$reset();
}

function openEditForm(): void {
  const show = systemStore.currentShow;
  if (show) {
    editFormState.value.name = show.name;
    editFormState.value.start_date = show.start_date;
    editFormState.value.end_date = show.end_date;
    editFormState.value.first_act_id = show.first_act_id;
  }
  editShowModal.value?.show();
}

async function onSubmitEdit(event: Event): Promise<void> {
  v$.value.editFormState.$touch();
  if (v$.value.editFormState.$invalid || submittingEditShow.value) {
    event.preventDefault();
    return;
  }
  submittingEditShow.value = true;
  try {
    await systemStore.updateShow(editFormState.value);
    editShowModal.value?.hide();
    resetEditForm();
  } catch (error) {
    log.error('Error submitting edit show:', error);
    event.preventDefault();
  } finally {
    submittingEditShow.value = false;
  }
}

onMounted(async () => {
  await systemStore.getShowDetails();
  await showStore.getActList();
});
</script>

<style scoped>
.row {
  margin-top: 0.5em;
  margin-bottom: 0.5em;
}
</style>
