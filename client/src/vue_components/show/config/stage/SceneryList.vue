<template>
  <span>
    <b-table
      id="scenery-table"
      :items="SCENERY_LIST"
      :fields="sceneryFields"
      :per-page="rowsPerPage"
      :current-page="currentPage"
      show-empty
    >
      <template #head(btn)="data">
        <b-button
          v-if="IS_SHOW_EDITOR"
          v-b-modal.new-scenery
          variant="outline-success"
        >
          New Scenery Item
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
            @click="deleteSceneryItem(data)"
          >
            Delete
          </b-button>
        </b-button-group>
      </template>
    </b-table>
    <b-pagination
      v-show="SCENERY_LIST.length > rowsPerPage"
      v-model="currentPage"
      :total-rows="SCENERY_LIST.length"
      :per-page="rowsPerPage"
      aria-controls="scenery-table"
      class="justify-content-center"
    />
    <b-modal
      id="new-scenery"
      ref="new-scenery"
      title="Add New Scenery Member"
      size="sm"
      @show="resetNewForm"
      @hidden="resetNewForm"
      @ok="onSubmitNew"
    >
      <b-form
        ref="new-scenery-form"
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
      id="edit-scenery"
      ref="edit-scenery"
      title="Edit Scenery Member"
      size="sm"
      @hidden="resetEditForm"
      @ok="onSubmitEdit"
    >
      <b-form
        ref="edit-scenery-form"
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
  name: 'SceneryList',
  data() {
    return {
      sceneryFields: [
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
    ...mapGetters(['SCENERY_LIST', 'IS_SHOW_EDITOR']),
  },
  async mounted() {
    await this.GET_SCENERY_LIST();
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
        await this.ADD_SCENERY_MEMBER(this.newFormState);
        this.resetNewForm();
      }
    },
    validateNewState(name) {
      const { $dirty, $error } = this.$v.newFormState[name];
      return $dirty ? !$error : null;
    },
    openEditForm(sceneryMember) {
      if (sceneryMember != null) {
        this.editFormState.id = sceneryMember.item.id;
        this.editFormState.showID = sceneryMember.item.show_id;
        this.editFormState.name = sceneryMember.item.first_name;
        this.editFormState.description = sceneryMember.item.last_name;
        this.$bvModal.show('edit-scenery');
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
        await this.UPDATE_SCENERY_MEMBER(this.editFormState);
        this.resetEditForm();
      }
    },
    validateEditState(name) {
      const { $dirty, $error } = this.$v.editFormState[name];
      return $dirty ? !$error : null;
    },
    async deleteSceneryItem(sceneryMember) {
      const msg = `Are you sure you want to delete ${sceneryMember.item.name}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await this.DELETE_SCENERY_MEMBER(sceneryMember.item.id);
      }
    },
    ...mapActions(['GET_SCENERY_LIST', 'ADD_SCENERY_MEMBER', 'DELETE_SCENERY_MEMBER', 'UPDATE_SCENERY_MEMBER']),
  },
};
</script>
