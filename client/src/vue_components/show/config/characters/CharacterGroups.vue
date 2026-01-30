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
    <b-pagination
      v-show="CHARACTER_GROUP_LIST.length > rowsPerPage"
      v-model="currentPage"
      :total-rows="CHARACTER_GROUP_LIST.length"
      :per-page="rowsPerPage"
      aria-controls="character-group-table"
      class="justify-content-center"
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
            :state="validateNewState('name')"
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
            :state="validateNewState('description')"
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
            :state="validateNewState('characters')"
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
            :state="validateEditState('name')"
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
            :state="validateEditState('description')"
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
            :state="validateEditState('characters')"
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

<script>
import { mapActions, mapGetters } from 'vuex';
import { required } from 'vuelidate/lib/validators';
import log from 'loglevel';
import formValidationMixin from '@/mixins/formValidationMixin';

export default {
  name: 'CharacterGroups',
  mixins: [formValidationMixin],
  data() {
    return {
      loading: true,
      characterGroupFields: ['name', 'description', 'characters', { key: 'btn', label: '' }],
      rowsPerPage: 15,
      currentPage: 1,
      tempCharacterList: [],
      newFormState: {
        name: '',
        description: '',
        characters: [],
      },
      tempEditCharacterList: [],
      editFormState: {
        id: null,
        name: '',
        description: '',
        characters: [],
      },
      submittingNewGroup: false,
      submittingEditGroup: false,
      deletingGroup: false,
    };
  },
  validations: {
    newFormState: {
      name: {
        required,
      },
      description: {},
      characters: {},
    },
    editFormState: {
      name: {
        required,
      },
      description: {},
      characters: {},
    },
  },
  computed: {
    ...mapGetters(['CHARACTER_LIST', 'CHARACTER_GROUP_LIST', 'IS_SHOW_EDITOR']),
  },
  async mounted() {
    await Promise.all([this.GET_CHARACTER_LIST(), this.GET_CHARACTER_GROUP_LIST()]);
    this.loading = false;
  },
  methods: {
    newSelectChanged(value, id) {
      this.$v.newFormState.characters.$model = value.map((character) => character.id);
    },
    resetNewForm() {
      this.tempCharacterList = [];
      this.resetForm('newFormState', {
        name: '',
        description: '',
        characters: [],
      });
      this.submittingNewGroup = false;
    },
    async onSubmitNew(event) {
      this.$v.newFormState.$touch();
      if (this.$v.newFormState.$anyError || this.submittingNewGroup) {
        event.preventDefault();
        return;
      }

      this.submittingNewGroup = true;
      try {
        await this.ADD_CHARACTER_GROUP(this.newFormState);
        this.$bvModal.hide('new-character-group');
        this.resetNewForm();
      } catch (error) {
        log.error('Error submitting new character group:', error);
        event.preventDefault();
      } finally {
        this.submittingNewGroup = false;
      }
    },
    async deleteCharacterGroup(characterGroup) {
      if (this.deletingGroup) {
        return;
      }

      const msg = `Are you sure you want to delete ${characterGroup.item.name}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.deletingGroup = true;
        try {
          await this.DELETE_CHARACTER_GROUP(characterGroup.item.id);
        } catch (error) {
          log.error('Error deleting character group:', error);
        } finally {
          this.deletingGroup = false;
        }
      }
    },
    openEditForm(characterGroup) {
      if (characterGroup != null) {
        this.editFormState.id = characterGroup.item.id;
        this.editFormState.name = characterGroup.item.name;
        this.editFormState.description = characterGroup.item.description;
        this.editFormState.characters = characterGroup.item.characters;

        this.tempEditCharacterList.push(
          ...this.CHARACTER_LIST.filter((character) =>
            this.editFormState.characters.includes(character.id)
          )
        );

        this.$bvModal.show('edit-character-group');
      }
    },
    resetEditForm() {
      this.resetForm('editFormState', {
        id: null,
        name: '',
        description: '',
        characters: [],
      });
      this.tempEditCharacterList = [];
      this.submittingEditGroup = false;
      this.deletingGroup = false;
    },
    editSelectChanged(value, id) {
      this.$v.editFormState.characters.$model = value.map((character) => character.id);
    },
    async onSubmitEdit(event) {
      this.$v.editFormState.$touch();
      if (this.$v.editFormState.$anyError || this.submittingEditGroup) {
        event.preventDefault();
        return;
      }

      this.submittingEditGroup = true;
      try {
        await this.UPDATE_CHARACTER_GROUP(this.editFormState);
        this.$bvModal.hide('edit-character-group');
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
};
</script>

<style scoped></style>
