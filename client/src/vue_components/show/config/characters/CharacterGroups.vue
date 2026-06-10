<template>
  <span v-if="!loading">
    <b-table
      id="character-group-table"
      :items="CHARACTER_GROUP_LIST"
      :fields="characterGroupFields"
      :per-page="rowsPerPage"
      :current-page="currentPage"
      show-empty
    >
      <template #head(btn)="data">
        <b-button v-if="IS_SHOW_EDITOR" v-b-modal.new-character-group variant="outline-success">
          New Character Group
        </b-button>
      </template>
      <template #cell(characters)="data">
        <div style="overflow-wrap: break-word">
          <p>
            {{
              CHARACTER_LIST.filter((c) => data.item.characters.includes(c.id))
                .map((c) => c.name)
                .join(', ')
            }}
          </p>
        </div>
      </template>
      <template #cell(btn)="data">
        <b-button-group v-if="IS_SHOW_EDITOR">
          <b-button
            variant="warning"
            :disabled="submittingEditGroup || deletingGroup"
            @click="openEditForm(data)"
          >
            Edit
          </b-button>
          <b-button
            variant="danger"
            :disabled="submittingEditGroup || deletingGroup"
            @click="deleteCharacterGroup(data)"
          >
            Delete
          </b-button>
        </b-button-group>
      </template>
    </b-table>
    <pagination-controls
      :per-page.sync="rowsPerPage"
      :current-page.sync="currentPage"
      :total-rows="CHARACTER_GROUP_LIST.length"
      aria-controls="character-group-table"
    />
    <b-modal
      id="new-character-group"
      ref="new-character"
      title="Add New Character Group"
      size="md"
      :ok-disabled="$v.newFormState.$invalid || submittingNewGroup"
      @show="resetNewForm"
      @hidden="resetNewForm"
      @ok="onSubmitNew"
    >
      <b-form ref="new-character-form" @submit.stop.prevent="onSubmitNew">
        <b-form-group id="new-name-input-group" label="Name" label-for="new-name-input">
          <b-form-input
            id="new-name-input"
            v-model="$v.newFormState.name.$model"
            name="new-name-input"
            :state="getValidationState('newFormState', 'name')"
            aria-describedby="new-name-feedback"
          />
          <b-form-invalid-feedback id="new-name-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="new-description-input-group"
          label="Description"
          label-for="new-description-input"
        >
          <b-form-input
            id="new-description-input"
            v-model="$v.newFormState.description.$model"
            name="new-description-input"
            :state="getValidationState('newFormState', 'description')"
          />
        </b-form-group>
        <b-form-group
          id="new-characters-input-group"
          label="Characters"
          label-for="new-characters-input"
        >
          <multi-select
            id="new-characters-input"
            v-model="tempCharacterList"
            name="new-characters-input"
            :multiple="true"
            :options="CHARACTER_LIST"
            track-by="id"
            label="name"
            :state="getValidationState('newFormState', 'characters')"
            @input="newSelectChanged"
          />
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="edit-character-group"
      ref="edit-character"
      title="Edit Character Group"
      size="md"
      :ok-disabled="$v.editFormState.$invalid || submittingEditGroup"
      @hidden="resetEditForm"
      @ok="onSubmitEdit"
    >
      <b-form ref="edit-character-form" @submit.stop.prevent="onSubmitEdit">
        <b-form-group id="edit-name-input-group" label="Name" label-for="edit-name-input">
          <b-form-input
            id="edit-name-input"
            v-model="$v.editFormState.name.$model"
            name="edit-name-input"
            :state="getValidationState('editFormState', 'name')"
            aria-describedby="edit-name-feedback"
          />
          <b-form-invalid-feedback id="edit-name-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="edit-description-input-group"
          label="Description"
          label-for="edit-description-input"
        >
          <b-form-input
            id="edit-description-input"
            v-model="$v.editFormState.description.$model"
            name="edit-description-input"
            :state="getValidationState('editFormState', 'description')"
          />
        </b-form-group>
        <b-form-group
          id="edit-characters-input-group"
          label="Characters"
          label-for="edit-characters-input"
        >
          <multi-select
            id="edit-characters-input"
            v-model="tempEditCharacterList"
            name="edit-characters-input"
            :multiple="true"
            :options="CHARACTER_LIST"
            track-by="id"
            label="name"
            :state="getValidationState('editFormState', 'characters')"
            @input="editSelectChanged"
          />
        </b-form-group>
      </b-form>
    </b-modal>
  </span>
  <div v-else class="text-center py-5">
    <b-spinner label="Loading" />
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapActions, mapGetters } from 'vuex';
import { required } from 'vuelidate/lib/validators';
import log from 'loglevel';
import formValidationMixin from '@/mixins/formValidationMixin';
import paginationMixin from '@/mixins/paginationMixin';

export default defineComponent({
  name: 'CharacterGroups',
  mixins: [formValidationMixin, paginationMixin],
  data() {
    return {
      tableKey: 'config_character_groups',
      loading: true,
      characterGroupFields: ['name', 'description', 'characters', { key: 'btn', label: '' }],
      tempCharacterList: [] as any[],
      newFormState: {
        name: '',
        description: '',
        characters: [] as number[],
      },
      tempEditCharacterList: [] as any[],
      editFormState: {
        id: null as number | null,
        name: '',
        description: '',
        characters: [] as number[],
      },
      submittingNewGroup: false,
      submittingEditGroup: false,
      deletingGroup: false,
    };
  },
  validations: {
    newFormState: {
      name: { required },
      description: {},
      characters: {},
    },
    editFormState: {
      name: { required },
      description: {},
      characters: {},
    },
  },
  computed: {
    ...mapGetters(['CHARACTER_LIST', 'CHARACTER_GROUP_LIST', 'IS_SHOW_EDITOR']),
  },
  async mounted(): Promise<void> {
    await Promise.all([
      (this as any).GET_CHARACTER_LIST(),
      (this as any).GET_CHARACTER_GROUP_LIST(),
    ]);
    this.loading = false;
  },
  methods: {
    newSelectChanged(value: any[]): void {
      (this as any).$v.newFormState.characters.$model = value.map((character) => character.id);
    },
    resetNewForm(): void {
      this.tempCharacterList = [];
      (this as any).resetForm('newFormState', { name: '', description: '', characters: [] });
      this.submittingNewGroup = false;
    },
    async onSubmitNew(event: Event): Promise<void> {
      (this as any).$v.newFormState.$touch();
      if ((this as any).$v.newFormState.$anyError || this.submittingNewGroup) {
        event.preventDefault();
        return;
      }
      this.submittingNewGroup = true;
      try {
        await (this as any).ADD_CHARACTER_GROUP(this.newFormState);
        (this as any).$bvModal.hide('new-character-group');
        this.resetNewForm();
      } catch (error) {
        log.error('Error submitting new character group:', error);
        event.preventDefault();
      } finally {
        this.submittingNewGroup = false;
      }
    },
    async deleteCharacterGroup(characterGroup: any): Promise<void> {
      if (this.deletingGroup) {
        return;
      }
      const msg = `Are you sure you want to delete ${characterGroup.item.name}?`;
      const action = await (this as any).$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.deletingGroup = true;
        try {
          await (this as any).DELETE_CHARACTER_GROUP(characterGroup.item.id);
        } catch (error) {
          log.error('Error deleting character group:', error);
        } finally {
          this.deletingGroup = false;
        }
      }
    },
    openEditForm(characterGroup: any): void {
      if (characterGroup != null) {
        this.editFormState.id = characterGroup.item.id;
        this.editFormState.name = characterGroup.item.name;
        this.editFormState.description = characterGroup.item.description;
        this.editFormState.characters = characterGroup.item.characters;
        this.tempEditCharacterList.push(
          ...(this as any).CHARACTER_LIST.filter((character: any) =>
            this.editFormState.characters.includes(character.id)
          )
        );
        (this as any).$bvModal.show('edit-character-group');
      }
    },
    resetEditForm(): void {
      (this as any).resetForm('editFormState', {
        id: null,
        name: '',
        description: '',
        characters: [],
      });
      this.tempEditCharacterList = [];
      this.submittingEditGroup = false;
      this.deletingGroup = false;
    },
    editSelectChanged(value: any[]): void {
      (this as any).$v.editFormState.characters.$model = value.map((character) => character.id);
    },
    async onSubmitEdit(event: Event): Promise<void> {
      (this as any).$v.editFormState.$touch();
      if ((this as any).$v.editFormState.$anyError || this.submittingEditGroup) {
        event.preventDefault();
        return;
      }
      this.submittingEditGroup = true;
      try {
        await (this as any).UPDATE_CHARACTER_GROUP(this.editFormState);
        (this as any).$bvModal.hide('edit-character-group');
        this.resetEditForm();
      } catch (error) {
        log.error('Error submitting edit character group:', error);
        event.preventDefault();
      } finally {
        this.submittingEditGroup = false;
      }
    },
    ...mapActions([
      'GET_CHARACTER_LIST',
      'GET_CHARACTER_GROUP_LIST',
      'ADD_CHARACTER_GROUP',
      'DELETE_CHARACTER_GROUP',
      'UPDATE_CHARACTER_GROUP',
    ]),
  },
});
</script>

<style scoped></style>
