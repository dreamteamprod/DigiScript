<template>
  <b-container
    class="mx-0"
    fluid
  >
    <b-row>
      <b-col>
        <h5>Character Groups</h5>
        <b-table
          id="character-group-table"
          :items="CHARACTER_GROUP_LIST"
          :fields="characterGroupFields"
          :per-page="rowsPerPage"
          :current-page="currentPage"
          show-empty
        >
          <template #head(btn)="data">
            <b-button
              v-b-modal.new-character-group
              variant="outline-success"
            >
              New Character Group
            </b-button>
          </template>
          <template #cell(characters)="data">
            <div style="overflow-wrap: break-word">
              <p>
                {{ CHARACTER_LIST.filter((c) => (
                  data.item.characters.includes(c.id))).map((c) => (c.name)).join(', ') }}
              </p>
            </div>
          </template>
          <template #cell(btn)="data">
            <b-button-group>
              <b-button
                variant="warning"
                @click="openEditForm(data)"
              >
                Edit
              </b-button>
              <b-button
                variant="danger"
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
      </b-col>
    </b-row>
    <b-modal
      id="new-character-group"
      ref="new-character"
      title="Add New Character Group"
      size="md"
      @show="resetNewForm"
      @hidden="resetNewForm"
      @ok="onSubmitNew"
    >
      <b-form
        ref="new-character-form"
        @submit.stop.prevent="onSubmitNew"
      >
        <b-form-group
          id="name-input-group"
          label="Name"
          label-for="name-input"
        >
          <b-form-input
            id="name-input"
            v-model="$v.newFormState.name.$model"
            name="name-input"
            :state="validateNewState('name')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback
            id="name-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="description-input-group"
          label="Description"
          label-for="description-input"
        >
          <b-form-input
            id="description-input"
            v-model="$v.newFormState.description.$model"
            name="description-input"
            :state="validateNewState('description')"
          />
        </b-form-group>
        <b-form-group
          id="characters-input-group"
          label="Characters"
          label-for="characters-input"
        >
          <multi-select
            id="characters-input"
            v-model="tempCharacterList"
            name="characters-input"
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
      title="Add New Character Group"
      size="md"
      @hidden="resetEditForm"
      @ok="onSubmitEdit"
    >
      <b-form
        ref="edit-character-form"
        @submit.stop.prevent="onSubmitEdit"
      >
        <b-form-group
          id="name-input-group"
          label="Name"
          label-for="name-input"
        >
          <b-form-input
            id="name-input"
            v-model="$v.editFormState.name.$model"
            name="name-input"
            :state="validateEditState('name')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback
            id="name-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="description-input-group"
          label="Description"
          label-for="description-input"
        >
          <b-form-input
            id="description-input"
            v-model="$v.editFormState.description.$model"
            name="description-input"
            :state="validateEditState('description')"
          />
        </b-form-group>
        <b-form-group
          id="characters-input-group"
          label="Characters"
          label-for="characters-input"
        >
          <multi-select
            id="characters-input"
            v-model="tempEditCharacterList"
            name="characters-input"
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
  </b-container>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';
import { required } from 'vuelidate/lib/validators';

export default {
  name: 'ConfigCharacterGroups',
  data() {
    return {
      characterGroupFields: [
        'name',
        'description',
        'characters',
        { key: 'btn', label: '' },
      ],
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
  async mounted() {
    await this.GET_CHARACTER_LIST();
    await this.GET_CHARACTER_GROUP_LIST();
  },
  methods: {
    newSelectChanged(value, id) {
      this.$v.newFormState.characters.$model = value.map((character) => (character.id));
    },
    resetNewForm() {
      this.tempCharacterList = [];
      this.newFormState = {
        name: '',
        description: '',
        characters: [],
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    async onSubmitNew(event) {
      this.$v.newFormState.$touch();
      if (this.$v.newFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.ADD_CHARACTER_GROUP(this.newFormState);
        this.resetNewForm();
      }
    },
    validateNewState(name) {
      const { $dirty, $error } = this.$v.newFormState[name];
      return $dirty ? !$error : null;
    },
    async deleteCharacterGroup(characterGroup) {
      const msg = `Are you sure you want to delete ${characterGroup.item.name}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await this.DELETE_CHARACTER_GROUP(characterGroup.item.id);
      }
    },
    openEditForm(characterGroup) {
      if (characterGroup != null) {
        this.editFormState.id = characterGroup.item.id;
        this.editFormState.name = characterGroup.item.name;
        this.editFormState.description = characterGroup.item.description;
        this.editFormState.characters = characterGroup.item.characters;

        this.tempEditCharacterList.push(...this.CHARACTER_LIST.filter((character) => (
          this.editFormState.characters.includes(character.id))));

        this.$bvModal.show('edit-character-group');
      }
    },
    resetEditForm() {
      this.editFormState = {
        id: null,
        name: '',
        description: '',
        characters: [],
      };
      this.tempEditCharacterList = [];

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    editSelectChanged(value, id) {
      this.$v.editFormState.characters.$model = value.map((character) => (character.id));
    },
    async onSubmitEdit(event) {
      this.$v.editFormState.$touch();
      if (this.$v.editFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.UPDATE_CHARACTER_GROUP(this.editFormState);
        this.resetEditForm();
      }
    },
    validateEditState(name) {
      const { $dirty, $error } = this.$v.editFormState[name];
      return $dirty ? !$error : null;
    },
    ...mapActions(['GET_CHARACTER_LIST', 'GET_CHARACTER_GROUP_LIST', 'ADD_CHARACTER_GROUP',
      'DELETE_CHARACTER_GROUP', 'UPDATE_CHARACTER_GROUP']),
  },
  computed: {
    ...mapGetters(['CHARACTER_LIST', 'CHARACTER_GROUP_LIST']),
  },
};
</script>

<style scoped>

</style>
