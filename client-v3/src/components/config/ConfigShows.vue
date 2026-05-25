<template>
  <BContainer fluid class="mx-0">
    <template v-if="loaded">
      <BRow>
        <BCol>
          <BTable
            id="shows-table"
            :items="availableShows"
            :fields="showFields"
            :per-page="rowsPerPage"
            :current-page="currentPage"
          >
            <template #head(btn)>
              <BButton variant="success" @click="newShowModal?.show()">Setup New Show</BButton>
            </template>
            <template #cell(btn)="data">
              <BButton
                variant="primary"
                :disabled="
                  isSubmittingLoad || (currentShow != null && currentShow.id === data.item.id)
                "
                @click="loadShow(data.item)"
              >
                {{
                  currentShow != null && currentShow.id === data.item.id ? 'Loaded' : 'Load Show'
                }}
              </BButton>
            </template>
          </BTable>
          <BPagination
            v-show="availableShows.length > rowsPerPage"
            v-model="currentPage"
            :total-rows="availableShows.length"
            :per-page="rowsPerPage"
            aria-controls="shows-table"
            class="justify-content-center"
          />
        </BCol>
      </BRow>
    </template>
    <BRow v-else>
      <BCol class="text-center">
        <BSpinner label="Loading shows..." variant="primary" />
      </BCol>
    </BRow>

    <BModal ref="newShowModal" title="Setup New Show" @show="resetForm">
      <BForm @submit.stop.prevent>
        <BFormGroup label="Name" label-for="show-name-input" label-cols="4">
          <BFormInput
            id="show-name-input"
            v-model="formState.name"
            name="show-name-input"
            :state="fieldState('name')"
          />
          <BFormInvalidFeedback>Required, max 100 characters.</BFormInvalidFeedback>
        </BFormGroup>

        <BFormGroup label="Start Date" label-for="show-start-input" label-cols="4">
          <BFormInput
            id="show-start-input"
            v-model="formState.start"
            name="show-start-input"
            type="date"
            :state="fieldState('start')"
          />
          <BFormInvalidFeedback>Required, must be before or same as end date.</BFormInvalidFeedback>
        </BFormGroup>

        <BFormGroup label="End Date" label-for="show-end-input" label-cols="4">
          <BFormInput
            id="show-end-input"
            v-model="formState.end"
            name="show-end-input"
            type="date"
            :state="fieldState('end')"
          />
          <BFormInvalidFeedback
            >Required, must be after or same as start date.</BFormInvalidFeedback
          >
        </BFormGroup>

        <hr />

        <BFormGroup label="Script Mode" label-for="show-script-mode-input" label-cols="4">
          <BAlert variant="secondary" :model-value="true">
            Change the type of script for this show.
          </BAlert>
          <BFormSelect
            id="show-script-mode-input"
            v-model="formState.script_mode"
            :options="scriptModes"
            :state="fieldState('script_mode')"
          />
        </BFormGroup>
      </BForm>

      <template #footer="{ cancel }">
        <BButton @click="cancel()">Cancel</BButton>
        <BButton variant="success" :disabled="isSubmittingShow" @click="submit(false)">
          Save
        </BButton>
        <BButton variant="primary" :disabled="isSubmittingShow" @click="submit(true)">
          Save and Load
        </BButton>
      </template>
    </BModal>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useVuelidate } from '@vuelidate/core';
import { required, maxLength, helpers } from '@vuelidate/validators';
import { storeToRefs } from 'pinia';
import { BModal } from 'bootstrap-vue-next';
import log from 'loglevel';
import { makeURL } from '@/js/utils';
import { useSystemStore } from '@/stores/system';
import { useShowStore } from '@/stores/show';
import { toast } from '@/js/toast';
import type { Show } from '@/types/api/show';

const systemStore = useSystemStore();
const showStore = useShowStore();
const { availableShows, currentShow } = storeToRefs(systemStore);
const { scriptModes } = storeToRefs(showStore);

const loaded = ref(false);
const newShowModal = ref<InstanceType<typeof BModal>>();
const isSubmittingLoad = ref(false);
const isSubmittingShow = ref(false);
const currentPage = ref(1);
const rowsPerPage = 15;

const showFields = [
  { key: 'id', label: 'ID' },
  'name',
  'start_date',
  'end_date',
  'created_at',
  { key: 'btn', label: '' },
];

interface ShowForm {
  name: string;
  start: string;
  end: string;
  script_mode: number | null;
}

const defaultForm = (): ShowForm => ({
  name: '',
  start: '',
  end: '',
  script_mode: scriptModes.value[0]?.value ?? null,
});

const formState = ref<ShowForm>(defaultForm());

const beforeEnd = helpers.withMessage(
  'Start date must be before end date',
  () =>
    !formState.value.start ||
    !formState.value.end ||
    new Date(formState.value.start) <= new Date(formState.value.end)
);

const afterStart = helpers.withMessage(
  'End date must be after start date',
  () =>
    !formState.value.start ||
    !formState.value.end ||
    new Date(formState.value.end) >= new Date(formState.value.start)
);

const rules = {
  name: { required, maxLength: maxLength(100) },
  start: { required, beforeEnd },
  end: { required, afterStart },
  script_mode: { required },
};

const v$ = useVuelidate(rules, formState);

function fieldState(key: keyof ShowForm): boolean | null {
  const field = v$.value[key];
  if (!field) return null;
  return field.$dirty ? !field.$error : null;
}

function resetForm(): void {
  formState.value = defaultForm();
  if (scriptModes.value.length > 0) formState.value.script_mode = scriptModes.value[0].value;
  isSubmittingShow.value = false;
  v$.value.$reset();
}

async function submit(load: boolean): Promise<void> {
  const valid = await v$.value.$validate();
  if (!valid) return;
  if (isSubmittingShow.value) return;

  isSubmittingShow.value = true;
  try {
    const params = new URLSearchParams({ load: String(load) });
    const response = await fetch(`${makeURL('/api/v1/show')}?${params}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formState.value),
    });
    if (response.ok) {
      await systemStore.getAvailableShows();
      toast.success('Created new show!');
      newShowModal.value?.hide();
      resetForm();
    } else {
      log.error('Unable to create show');
      toast.error('Unable to save show');
    }
  } catch (err) {
    log.error('Error creating show:', err);
    toast.error('Unable to save show');
  } finally {
    isSubmittingShow.value = false;
  }
}

async function loadShow(show: Show): Promise<void> {
  if (isSubmittingLoad.value) return;
  isSubmittingLoad.value = true;
  try {
    const response = await fetch(makeURL('/api/v1/settings'), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_show: show.id }),
    });
    if (response.ok) {
      toast.success('Loaded show!');
      await systemStore.getAvailableShows();
    } else {
      log.error('Unable to load show');
      toast.error('Unable to load show');
    }
  } catch (err) {
    log.error('Error loading show:', err);
    toast.error('Unable to load show');
  } finally {
    isSubmittingLoad.value = false;
  }
}

onMounted(async () => {
  await Promise.all([systemStore.getAvailableShows(), showStore.getScriptModes()]);
  loaded.value = true;
});
</script>
