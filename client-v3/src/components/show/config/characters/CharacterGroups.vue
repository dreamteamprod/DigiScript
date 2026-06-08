<template>
  <span v-if="!loading">
    <BTable
      id="character-group-table"
      :items="showStore.characterGroupList"
      :fields="characterGroupFields"
      :per-page="perPage"
      :current-page="currentPage"
      show-empty
    >
      <template #head(btn)>
        <BButton
          v-if="systemStore.isShowEditor"
          v-b-modal.new-character-group
          variant="outline-success"
        >
          New Character Group
        </BButton>
      </template>
      <template #cell(characters)="data">
        <div style="overflow-wrap: break-word">
          <p>
            {{
              showStore.characterList
                .filter((c) => data.item.characters.includes(c.id))
                .map((c) => c.name)
                .join(', ')
            }}
          </p>
        </div>
      </template>
      <template #cell(btn)="data">
        <BButtonGroup v-if="systemStore.isShowEditor">
          <BButton
            variant="warning"
            :disabled="submittingEditGroup || deletingGroup"
            @click="openEditForm(data.item)"
          >
            Edit
          </BButton>
          <BButton
            variant="danger"
            :disabled="submittingEditGroup || deletingGroup"
            @click="deleteCharacterGroup(data.item)"
          >
            Delete
          </BButton>
        </BButtonGroup>
      </template>
    </BTable>
    <PaginationControls
      v-model:per-page="perPage"
      v-model:current-page="currentPage"
      :total-rows="showStore.characterGroupList.length"
      aria-controls="character-group-table"
    />

    <BModal
      id="new-character-group"
      ref="newGroupModal"
      title="Add New Character Group"
      size="md"
      :ok-disabled="newV$.newFormState.$invalid || submittingNewGroup"
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
        <BFormGroup label="Description" label-for="new-description-input" label-cols="4">
          <BFormInput id="new-description-input" v-model="newFormState.description" />
        </BFormGroup>
        <BFormGroup label="Characters" label-for="new-characters-input" label-cols="4">
          <VueMultiselect
            v-model="newCharacterObjects"
            :multiple="true"
            :options="showStore.characterList"
            track-by="id"
            label="name"
          />
        </BFormGroup>
      </BForm>
    </BModal>

    <BModal
      id="edit-character-group"
      ref="editGroupModal"
      title="Edit Character Group"
      size="md"
      :ok-disabled="editV$.editFormState.$invalid || submittingEditGroup"
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
        <BFormGroup label="Description" label-for="edit-description-input" label-cols="4">
          <BFormInput id="edit-description-input" v-model="editFormState.description" />
        </BFormGroup>
        <BFormGroup label="Characters" label-for="edit-characters-input" label-cols="4">
          <VueMultiselect
            v-model="editCharacterObjects"
            :multiple="true"
            :options="showStore.characterList"
            track-by="id"
            label="name"
          />
        </BFormGroup>
      </BForm>
    </BModal>
  </span>
  <div v-else class="text-center py-5">
    <BSpinner label="Loading" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useVuelidate } from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import { BModal } from 'bootstrap-vue-next';
import VueMultiselect from 'vue-multiselect';
import 'vue-multiselect/dist/vue-multiselect.css';
import log from 'loglevel';
import { useSystemStore } from '@/stores/system';
import { useShowStore } from '@/stores/show';
import { useConfirm } from '@/composables/useConfirm';
import { usePagination } from '@/composables/usePagination';
import type { Character, CharacterGroup } from '@/types/api/show';

const systemStore = useSystemStore();
const showStore = useShowStore();
const { confirm } = useConfirm();

const loading = ref(true);
const { perPage, currentPage } = usePagination();
const submittingNewGroup = ref(false);
const submittingEditGroup = ref(false);
const deletingGroup = ref(false);

const newGroupModal = ref<InstanceType<typeof BModal>>();
const editGroupModal = ref<InstanceType<typeof BModal>>();

const characterGroupFields = ['name', 'description', 'characters', { key: 'btn', label: '' }];

interface NewGroupForm {
  name: string;
  description: string;
  characters: number[];
}

interface EditGroupForm {
  id: number | null;
  name: string;
  description: string;
  characters: number[];
}

const newFormState = ref<NewGroupForm>({ name: '', description: '', characters: [] });
const editFormState = ref<EditGroupForm>({ id: null, name: '', description: '', characters: [] });

const newCharacterObjects = ref<Character[]>([]);
const editCharacterObjects = ref<Character[]>([]);

const newRules = { newFormState: { name: { required } } };
const editRules = { editFormState: { name: { required } } };

const newV$ = useVuelidate(newRules, { newFormState });
const editV$ = useVuelidate(editRules, { editFormState });

function newFieldState(key: keyof NewGroupForm): boolean | null {
  const field = newV$.value.newFormState[key];
  if (!field) return null;
  return field.$dirty ? !field.$error : null;
}

function editFieldState(key: keyof EditGroupForm): boolean | null {
  const field = editV$.value.editFormState[key];
  if (!field) return null;
  return field.$dirty ? !field.$error : null;
}

function resetNewForm(): void {
  newCharacterObjects.value = [];
  newFormState.value = { name: '', description: '', characters: [] };
  submittingNewGroup.value = false;
  newV$.value.$reset();
}

function resetEditForm(): void {
  editCharacterObjects.value = [];
  editFormState.value = { id: null, name: '', description: '', characters: [] };
  submittingEditGroup.value = false;
  deletingGroup.value = false;
  editV$.value.$reset();
}

function openEditForm(group: CharacterGroup): void {
  editFormState.value.id = group.id;
  editFormState.value.name = group.name ?? '';
  editFormState.value.description = group.description ?? '';
  editFormState.value.characters = group.characters;
  editCharacterObjects.value = showStore.characterList.filter((c) =>
    group.characters.includes(c.id)
  );
  editGroupModal.value?.show();
}

async function onSubmitNew(event: Event): Promise<void> {
  newV$.value.newFormState.$touch();
  if (newV$.value.newFormState.$invalid || submittingNewGroup.value) {
    event.preventDefault();
    return;
  }
  submittingNewGroup.value = true;
  try {
    const payload = {
      ...newFormState.value,
      characters: newCharacterObjects.value.map((c) => c.id),
    };
    await showStore.addCharacterGroup(payload);
    newGroupModal.value?.hide();
    resetNewForm();
  } catch (error) {
    log.error('Error submitting new character group:', error);
    event.preventDefault();
  } finally {
    submittingNewGroup.value = false;
  }
}

async function onSubmitEdit(event: Event): Promise<void> {
  editV$.value.editFormState.$touch();
  if (editV$.value.editFormState.$invalid || submittingEditGroup.value) {
    event.preventDefault();
    return;
  }
  submittingEditGroup.value = true;
  try {
    const payload = {
      ...editFormState.value,
      characters: editCharacterObjects.value.map((c) => c.id),
    };
    await showStore.updateCharacterGroup(payload);
    editGroupModal.value?.hide();
    resetEditForm();
  } catch (error) {
    log.error('Error submitting edit character group:', error);
    event.preventDefault();
  } finally {
    submittingEditGroup.value = false;
  }
}

async function deleteCharacterGroup(group: CharacterGroup): Promise<void> {
  if (deletingGroup.value) return;
  const ok = await confirm(`Are you sure you want to delete ${group.name}?`);
  if (ok) {
    deletingGroup.value = true;
    try {
      await showStore.deleteCharacterGroup(group.id);
    } catch (error) {
      log.error('Error deleting character group:', error);
    } finally {
      deletingGroup.value = false;
    }
  }
}

onMounted(async () => {
  await Promise.all([showStore.getCharacterList(), showStore.getCharacterGroupList()]);
  loading.value = false;
});
</script>
