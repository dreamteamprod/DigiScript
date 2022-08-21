<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col>
        <h5>Character Groups</h5>
        <b-table id="character-group-table" :items="CHARACTER_GROUP_LIST"
                 :fields="characterGroupFields" show-empty>
          <template #head(btn)="data">
            <b-button variant="outline-success" v-b-modal.new-character-group>
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
              <b-button variant="warning" @click="openEditForm(data)">
                Edit
              </b-button>
              <b-button variant="danger" @click="deleteCharacterGroup(data)">
                Delete
              </b-button>
            </b-button-group>
          </template>
        </b-table>
      </b-col>
    </b-row>
    <b-modal id="new-character-group" title="Add New Character Group" ref="new-character" size="md"
             @show="resetNewForm" @hidden="resetNewForm" @ok="onSubmitNew">
      <b-form @submit.stop.prevent="onSubmitNew" ref="new-character-form">
        <b-form-group id="name-input-group" label="Name" label-for="name-input">
          <b-form-input
            id="name-input"
            name="name-input"
            v-model="$v.newFormState.name.$model"
            :state="validateNewState('name')"
            aria-describedby="name-feedback"
          ></b-form-input>
          <b-form-invalid-feedback
            id="name-feedback"
          >This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group id="description-input-group" label="Description"
                      label-for="description-input">
          <b-form-input
            id="description-input"
            name="description-input"
            v-model="$v.newFormState.description.$model"
            :state="validateNewState('description')"
          ></b-form-input>
        </b-form-group>
        <b-form-group id="characters-input-group" label="Characters"
                      label-for="characters-input">
          <multi-select
            id="characters-input"
            name="characters-input"
            v-model="tempCharacterList"
            :multiple="true"
            :options="CHARACTER_LIST"
            track-by="id"
            label="name"
            @input="newSelectChanged"
            :state="validateNewState('characters')"
          ></multi-select>
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
        { key: 'id', label: 'ID' },
        'name',
        'description',
        'characters',
        { key: 'btn', label: '' },
      ],
      tempCharacterList: [],
      newFormState: {
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
    ...mapActions(['GET_CHARACTER_LIST', 'GET_CHARACTER_GROUP_LIST', 'ADD_CHARACTER_GROUP',
      'DELETE_CHARACTER_GROUP']),
  },
  computed: {
    ...mapGetters(['CHARACTER_LIST', 'CHARACTER_GROUP_LIST']),
  },
};
</script>

<style scoped>

</style>
