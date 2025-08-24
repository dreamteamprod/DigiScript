<template>
  <b-container
    class="mx-0"
    fluid
  >
    <b-row>
      <b-col>
        <b-tabs content-class="mt-3">
          <b-tab
            title="Characters"
            active
          >
            <b-table
              id="character-table"
              :items="CHARACTER_LIST"
              :fields="characterFields"
              :per-page="rowsPerPage"
              :current-page="currentPage"
              show-empty
            >
              <template #head(btn)="data">
                <b-button
                  v-if="IS_SHOW_EDITOR"
                  v-b-modal.new-character
                  variant="outline-success"
                >
                  New Character
                </b-button>
              </template>
              <template #cell(cast_member)="data">
                <template v-if="data.item.cast_member">
                  {{ data.item.cast_member.first_name }} {{ data.item.cast_member.last_name }}
                </template>
                <template v-else-if="IS_SHOW_EDITOR">
                  <b-link @click="openEditForm(data)">
                    Set Cast Member
                  </b-link>
                </template>
              </template>
              <template #cell(btn)="data">
                <b-button-group v-if="IS_SHOW_EDITOR">
                  <b-button
                    variant="warning"
                    :disabled="submittingEditCharacter || deletingCharacter"
                    @click="openEditForm(data)"
                  >
                    Edit
                  </b-button>
                  <b-button
                    variant="danger"
                    :disabled="submittingEditCharacter || deletingCharacter"
                    @click="deleteCharacter(data)"
                  >
                    Delete
                  </b-button>
                </b-button-group>
              </template>
            </b-table>
            <b-pagination
              v-show="CHARACTER_LIST.length > rowsPerPage"
              v-model="currentPage"
              :total-rows="CHARACTER_LIST.length"
              :per-page="rowsPerPage"
              aria-controls="character-table"
              class="justify-content-center"
            />
          </b-tab>
          <b-tab title="Line Counts">
            <character-line-stats />
          </b-tab>
        </b-tabs>
      </b-col>
    </b-row>
    <b-modal
      id="new-character"
      ref="new-character"
      title="Add New Character"
      size="md"
      :ok-disabled="$v.newFormState.$invalid || submittingNewCharacter"
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
          id="played-by-input-group"
          label="Played By"
          label-for="played-by-input"
        >
          <b-form-select
            v-model="$v.newFormState.played_by.$model"
            :options="castOptions"
            :state="validateNewState('played_by')"
          />
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="edit-character"
      ref="edit-character"
      title="Edit Cast Member"
      size="md"
      :ok-disabled="$v.editFormState.$invalid || submittingEditCharacter"
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
          id="played-by-input-group"
          label="Played By"
          label-for="played-by-input"
        >
          <b-form-select
            v-model="$v.editFormState.played_by.$model"
            :options="castOptions"
            :state="validateEditState('played_by')"
          />
        </b-form-group>
      </b-form>
    </b-modal>
  </b-container>
</template>

<script>
import { required } from 'vuelidate/lib/validators';
import { mapGetters, mapActions } from 'vuex';
import CharacterLineStats from '@/vue_components/show/config/characters/CharacterLineStats.vue';
import log from 'loglevel';

export default {
  name: 'ConfigCharacters',
  components: { CharacterLineStats },
  data() {
    return {
      rowsPerPage: 15,
      currentPage: 1,
      characterFields: [
        'name',
        'description',
        { key: 'cast_member', label: 'Played By' },
        { key: 'btn', label: '' },
      ],
      newFormState: {
        name: '',
        description: '',
        played_by: null,
      },
      editFormState: {
        id: null,
        showID: null,
        name: '',
        description: '',
        played_by: null,
      },
      submittingNewCharacter: false,
      submittingEditCharacter: false,
      deletingCharacter: false,
    };
  },
  validations: {
    newFormState: {
      name: {
        required,
      },
      description: {
      },
      played_by: {
      },
    },
    editFormState: {
      name: {
        required,
      },
      description: {
      },
      played_by: {
      },
    },
  },
  computed: {
    ...mapGetters(['CHARACTER_LIST', 'CAST_LIST', 'IS_SHOW_EDITOR']),
    castOptions() {
      return [
        { value: null, text: 'Please select an option', disabled: true },
        ...this.CAST_LIST.map((castMember) => ({ value: castMember.id, text: `${castMember.first_name} ${castMember.last_name}` })),
      ];
    },
  },
  async mounted() {
    await this.GET_CHARACTER_LIST();
    await this.GET_CAST_LIST();
  },
  methods: {
    resetNewForm() {
      this.newFormState = {
        name: '',
        description: '',
        played_by: null,
      };
      this.submittingNewCharacter = false;

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    async onSubmitNew(event) {
      this.$v.newFormState.$touch();
      if (this.$v.newFormState.$anyError || this.submittingNewCharacter) {
        event.preventDefault();
        return;
      }

      this.submittingNewCharacter = true;
      try {
        await this.ADD_CHARACTER(this.newFormState);
        this.$bvModal.hide('new-character');
        this.resetNewForm();
      } catch (error) {
        log.error('Error submitting new character:', error);
        event.preventDefault();
      } finally {
        this.submittingNewCharacter = false;
      }
    },
    validateNewState(name) {
      const { $dirty, $error } = this.$v.newFormState[name];
      return $dirty ? !$error : null;
    },
    openEditForm(character) {
      if (character != null) {
        this.editFormState.id = character.item.id;
        this.editFormState.showID = character.item.show_id;
        this.editFormState.name = character.item.name;
        this.editFormState.description = character.item.description;
        this.editFormState.played_by = character.item.played_by;
        this.$bvModal.show('edit-character');
      }
    },
    resetEditForm() {
      this.editFormState = {
        id: null,
        showID: null,
        name: '',
        description: '',
        played_by: null,
      };
      this.submittingEditCharacter = false;
      this.deletingCharacter = false;

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    async onSubmitEdit(event) {
      this.$v.editFormState.$touch();
      if (this.$v.editFormState.$anyError || this.submittingEditCharacter) {
        event.preventDefault();
        return;
      }

      this.submittingEditCharacter = true;
      try {
        await this.UPDATE_CHARACTER(this.editFormState);
        this.$bvModal.hide('edit-character');
        this.resetEditForm();
      } catch (error) {
        log.error('Error submitting edit character:', error);
        event.preventDefault();
      } finally {
        this.submittingEditCharacter = false;
      }
    },
    validateEditState(name) {
      const { $dirty, $error } = this.$v.editFormState[name];
      return $dirty ? !$error : null;
    },
    async deleteCharacter(character) {
      if (this.deletingCharacter) {
        return;
      }

      const msg = `Are you sure you want to delete ${character.item.name}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.deletingCharacter = true;
        try {
          await this.DELETE_CHARACTER(character.item.id);
        } catch (error) {
          log.error('Error deleting character:', error);
        } finally {
          this.deletingCharacter = false;
        }
      }
    },
    ...mapActions(['GET_CHARACTER_LIST', 'GET_CAST_LIST', 'ADD_CHARACTER', 'UPDATE_CHARACTER', 'DELETE_CHARACTER']),
  },
};
</script>

<style scoped>

</style>
