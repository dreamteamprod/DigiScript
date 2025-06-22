<template>
  <span>
    <b-table
      id="props-table"
      :items="PROPS_LIST"
      :fields="propsFields"
      :per-page="rowsPerPage"
      :current-page="currentPage"
      show-empty
    >
      <template #head(btn)="data">
        <b-button
          v-if="IS_SHOW_EDITOR"
          v-b-modal.new-props
          variant="outline-success"
        >
          New Props Item
        </b-button>
      </template>
      <template #cell(btn)="data">
        <b-button-group v-if="IS_SHOW_EDITOR">
          <b-button
            variant="warning"
            @click="openEditForm(data)"
          >
            Edit
          </b-button>
          <b-button
            variant="danger"
            @click="deletePropsItem(data)"
          >
            Delete
          </b-button>
        </b-button-group>
      </template>
    </b-table>
    <b-pagination
      v-show="PROPS_LIST.length > rowsPerPage"
      v-model="currentPage"
      :total-rows="PROPS_LIST.length"
      :per-page="rowsPerPage"
      aria-controls="props-table"
      class="justify-content-center"
    />
    <b-modal
      id="new-props"
      ref="new-props"
      title="Add New Props Member"
      size="sm"
      @show="resetNewForm"
      @hidden="resetNewForm"
      @ok="onSubmitNew"
    >
      <b-form
        ref="new-props-form"
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
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback
            id="description-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="edit-props"
      ref="edit-props"
      title="Edit Props Member"
      size="sm"
      @hidden="resetEditForm"
      @ok="onSubmitEdit"
    >
      <b-form
        ref="edit-props-form"
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
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback
            id="description-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
  </span>
</template>

<script>
import { required } from 'vuelidate/lib/validators';
import { mapGetters, mapActions } from 'vuex';

export default {
  name: 'PropsList',
  data() {
    return {
      propsFields: [
        'name',
        'description',
        { key: 'btn', label: '' },
      ],
      newFormState: {
        name: '',
        description: '',
      },
      rowsPerPage: 15,
      currentPage: 1,
      editFormState: {
        id: null,
        showID: null,
        name: '',
        description: '',
      },
    };
  },
  validations: {
    newFormState: {
      name: {
        required,
      },
      description: {},
    },
    editFormState: {
      name: {
        required,
      },
      description: {},
    },
  },
  computed: {
    ...mapGetters(['PROPS_LIST', 'IS_SHOW_EDITOR']),
  },
  async mounted() {
    await this.GET_PROPS_LIST();
  },
  methods: {
    resetNewForm() {
      this.newFormState = {
        name: '',
        description: '',
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
        await this.ADD_PROPS_MEMBER(this.newFormState);
        this.resetNewForm();
      }
    },
    validateNewState(name) {
      const { $dirty, $error } = this.$v.newFormState[name];
      return $dirty ? !$error : null;
    },
    openEditForm(propsMember) {
      if (propsMember != null) {
        this.editFormState.id = propsMember.item.id;
        this.editFormState.showID = propsMember.item.show_id;
        this.editFormState.name = propsMember.item.first_name;
        this.editFormState.description = propsMember.item.last_name;
        this.$bvModal.show('edit-props');
      }
    },
    resetEditForm() {
      this.editFormState = {
        id: null,
        showID: null,
        name: '',
        description: '',
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    async onSubmitEdit(event) {
      this.$v.editFormState.$touch();
      if (this.$v.editFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.UPDATE_PROPS_MEMBER(this.editFormState);
        this.resetEditForm();
      }
    },
    validateEditState(name) {
      const { $dirty, $error } = this.$v.editFormState[name];
      return $dirty ? !$error : null;
    },
    async deletePropsItem(propsMember) {
      const msg = `Are you sure you want to delete ${propsMember.item.name}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await this.DELETE_PROPS_MEMBER(propsMember.item.id);
      }
    },
    ...mapActions(['GET_PROPS_LIST', 'ADD_PROPS_MEMBER', 'DELETE_PROPS_MEMBER', 'UPDATE_PROPS_MEMBER']),
  },
};
</script>
