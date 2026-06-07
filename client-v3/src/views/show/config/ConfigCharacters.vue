<template>
  <BContainer class="mx-0" fluid>
    <BRow>
      <BCol>
        <BTabs content-class="mt-3">
          <BTab title="Characters" active>
            <BTable
              id="character-table"
              :items="showStore.characterList"
              :fields="characterFields"
              :per-page="rowsPerPage"
              :current-page="currentPage"
              show-empty
            >
              <template #head(btn)>
                <BButton
                  v-if="systemStore.isShowEditor"
                  v-b-modal.new-character
                  variant="outline-success"
                >
                  New Character
                </BButton>
              </template>
              <template #cell(cast_member)="data">
                <template v-if="data.item.cast_member">
                  {{ data.item.cast_member.first_name }} {{ data.item.cast_member.last_name }}
                </template>
                <template v-else-if="systemStore.isShowEditor">
                  <BLink @click="openEditForm(data.item)">Set Cast Member</BLink>
                </template>
              </template>
              <template #cell(btn)="data">
                <BButtonGroup v-if="systemStore.isShowEditor">
                  <BButton
                    variant="warning"
                    :disabled="submittingEditCharacter || deletingCharacter || mergingCharacter"
                    @click="openEditForm(data.item)"
                  >
                    Edit
                  </BButton>
                  <BButton
                    variant="info"
                    :disabled="submittingEditCharacter || deletingCharacter || mergingCharacter"
                    @click="openMergeForm(data.item)"
                  >
                    Merge
                  </BButton>
                  <BButton
                    variant="danger"
                    :disabled="submittingEditCharacter || deletingCharacter || mergingCharacter"
                    @click="deleteCharacter(data.item)"
                  >
                    Delete
                  </BButton>
                </BButtonGroup>
              </template>
            </BTable>
            <BPagination
              v-show="showStore.characterList.length > rowsPerPage"
              v-model="currentPage"
              :total-rows="showStore.characterList.length"
              :per-page="rowsPerPage"
              aria-controls="character-table"
              class="justify-content-center"
            />
          </BTab>
          <BTab title="Character Groups">
            <CharacterGroups />
          </BTab>
          <BTab title="Line Counts">
            <CharacterLineStats />
          </BTab>
          <BTab title="Timeline">
            <CharacterTimeline />
          </BTab>
        </BTabs>
      </BCol>
    </BRow>

    <BModal
      id="new-character"
      ref="newCharacterModal"
      title="Add New Character"
      size="md"
      :ok-disabled="newV$.newFormState.$invalid || submittingNewCharacter"
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
        <BFormGroup label="Played By" label-for="new-played-by-input" label-cols="4">
          <BFormSelect
            id="new-played-by-input"
            v-model="newFormState.played_by"
            :options="castOptions"
          />
        </BFormGroup>
      </BForm>
    </BModal>

    <BModal
      id="merge-character"
      ref="mergeCharacterModal"
      :title="`Merge ${mergeSourceCharacter?.name ?? 'Character'}`"
      size="md"
      :ok-disabled="!mergeDestinationObject || mergingCharacter"
      @hide="resetMergeForm"
      @ok="onSubmitMerge"
    >
      <p>
        Select a destination character. All script lines and group memberships from
        <strong>{{ mergeSourceCharacter?.name }}</strong> will be transferred to the selected
        character, and <strong>{{ mergeSourceCharacter?.name }}</strong> will be deleted.
      </p>
      <BFormGroup label="Merge into" label-for="merge-destination-input" label-cols="4">
        <VueMultiselect
          id="merge-destination-input"
          v-model="mergeDestinationObject"
          :multiple="false"
          :options="mergeDestinationOptions"
          track-by="id"
          label="name"
          placeholder="Select destination character"
        />
      </BFormGroup>
    </BModal>

    <BModal
      id="edit-character"
      ref="editCharacterModal"
      title="Edit Character"
      size="md"
      :ok-disabled="editV$.editFormState.$invalid || submittingEditCharacter"
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
        <BFormGroup label="Played By" label-for="edit-played-by-input" label-cols="4">
          <BFormSelect
            id="edit-played-by-input"
            v-model="editFormState.played_by"
            :options="castOptions"
          />
        </BFormGroup>
      </BForm>
    </BModal>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useVuelidate } from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import { BModal } from 'bootstrap-vue-next';
import log from 'loglevel';
import VueMultiselect from 'vue-multiselect';
import 'vue-multiselect/dist/vue-multiselect.css';
import { useSystemStore } from '@/stores/system';
import { useShowStore } from '@/stores/show';
import { useConfirm } from '@/composables/useConfirm';
import CharacterGroups from '@/components/show/config/characters/CharacterGroups.vue';
import CharacterLineStats from '@/components/show/config/characters/CharacterLineStats.vue';
import type { Character } from '@/types/api/show';

const systemStore = useSystemStore();
const showStore = useShowStore();
const { confirm } = useConfirm();

const rowsPerPage = 15;
const currentPage = ref(1);
const submittingNewCharacter = ref(false);
const submittingEditCharacter = ref(false);
const deletingCharacter = ref(false);

const newCharacterModal = ref<InstanceType<typeof BModal>>();
const editCharacterModal = ref<InstanceType<typeof BModal>>();
const mergeCharacterModal = ref<InstanceType<typeof BModal>>();

const mergingCharacter = ref(false);
const mergeSourceCharacter = ref<Character | null>(null);
const mergeDestinationObject = ref<Character | null>(null);

const characterFields = [
  'name',
  'description',
  { key: 'cast_member', label: 'Played By' },
  { key: 'btn', label: '' },
];

interface NewCharacterForm {
  name: string;
  description: string;
  played_by: number | null;
}

interface EditCharacterForm {
  id: number | null;
  showID: number | null;
  name: string;
  description: string;
  played_by: number | null;
}

const newFormState = ref<NewCharacterForm>({ name: '', description: '', played_by: null });
const editFormState = ref<EditCharacterForm>({
  id: null,
  showID: null,
  name: '',
  description: '',
  played_by: null,
});

const newRules = { newFormState: { name: { required } } };
const editRules = { editFormState: { name: { required } } };

const newV$ = useVuelidate(newRules, { newFormState });
const editV$ = useVuelidate(editRules, { editFormState });

const mergeDestinationOptions = computed(() =>
  showStore.characterList.filter(
    (c) => mergeSourceCharacter.value === null || c.id !== mergeSourceCharacter.value.id
  )
);

const castOptions = computed(() => [
  { value: null, text: 'Please select an option', disabled: true },
  ...showStore.castList.map((c) => ({
    value: c.id,
    text: `${c.first_name} ${c.last_name}`,
  })),
]);

function newFieldState(key: keyof NewCharacterForm): boolean | null {
  const field = newV$.value.newFormState[key];
  if (!field) return null;
  return field.$dirty ? !field.$error : null;
}

function editFieldState(key: keyof EditCharacterForm): boolean | null {
  const field = editV$.value.editFormState[key];
  if (!field) return null;
  return field.$dirty ? !field.$error : null;
}

function resetNewForm(): void {
  newFormState.value = { name: '', description: '', played_by: null };
  submittingNewCharacter.value = false;
  newV$.value.$reset();
}

function resetEditForm(): void {
  editFormState.value = { id: null, showID: null, name: '', description: '', played_by: null };
  submittingEditCharacter.value = false;
  deletingCharacter.value = false;
  editV$.value.$reset();
}

function openEditForm(character: Character): void {
  editFormState.value.id = character.id;
  editFormState.value.showID = character.show_id;
  editFormState.value.name = character.name ?? '';
  editFormState.value.description = character.description ?? '';
  editFormState.value.played_by = character.played_by;
  editCharacterModal.value?.show();
}

async function onSubmitNew(event: Event): Promise<void> {
  newV$.value.newFormState.$touch();
  if (newV$.value.newFormState.$invalid || submittingNewCharacter.value) {
    event.preventDefault();
    return;
  }
  submittingNewCharacter.value = true;
  try {
    await showStore.addCharacter(newFormState.value);
    newCharacterModal.value?.hide();
    resetNewForm();
  } catch (error) {
    log.error('Error submitting new character:', error);
    event.preventDefault();
  } finally {
    submittingNewCharacter.value = false;
  }
}

async function onSubmitEdit(event: Event): Promise<void> {
  editV$.value.editFormState.$touch();
  if (editV$.value.editFormState.$invalid || submittingEditCharacter.value) {
    event.preventDefault();
    return;
  }
  submittingEditCharacter.value = true;
  try {
    await showStore.updateCharacter(editFormState.value);
    editCharacterModal.value?.hide();
    resetEditForm();
  } catch (error) {
    log.error('Error submitting edit character:', error);
    event.preventDefault();
  } finally {
    submittingEditCharacter.value = false;
  }
}

function openMergeForm(character: Character): void {
  mergeSourceCharacter.value = character;
  mergeDestinationObject.value = null;
  mergeCharacterModal.value?.show();
}

function resetMergeForm(): void {
  mergeSourceCharacter.value = null;
  mergeDestinationObject.value = null;
  mergingCharacter.value = false;
}

async function onSubmitMerge(event: Event): Promise<void> {
  if (!mergeDestinationObject.value || mergingCharacter.value) {
    event.preventDefault();
    return;
  }
  mergingCharacter.value = true;
  try {
    await showStore.mergeCharacter(mergeSourceCharacter.value!.id, mergeDestinationObject.value.id);
    mergeCharacterModal.value?.hide();
    resetMergeForm();
  } catch (error) {
    log.error('Error merging character:', error);
    event.preventDefault();
  } finally {
    mergingCharacter.value = false;
  }
}

async function deleteCharacter(character: Character): Promise<void> {
  if (deletingCharacter.value) return;
  const ok = await confirm(`Are you sure you want to delete ${character.name}?`);
  if (ok) {
    deletingCharacter.value = true;
    try {
      await showStore.deleteCharacter(character.id);
    } catch (error) {
      log.error('Error deleting character:', error);
    } finally {
      deletingCharacter.value = false;
    }
  }
}

onMounted(async () => {
  await Promise.all([showStore.getCharacterList(), showStore.getCastList()]);
});
</script>
