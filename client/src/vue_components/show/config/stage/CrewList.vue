<template>
  <span>
    <b-table
      id="crew-table"
      :items="CREW_LIST"
      :fields="crewFields"
      :per-page="rowsPerPage"
      :current-page="currentPage"
      show-empty
    >
      <template #head(btn)="data">
        <b-button
          v-if="IS_SHOW_EDITOR"
          v-b-modal.new-crew
          variant="outline-success"
        >
          New Crew Member
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
            @click="deleteCrewMember(data)"
          >
            Delete
          </b-button>
        </b-button-group>
      </template>
    </b-table>
    <b-pagination
      v-show="CREW_LIST.length > rowsPerPage"
      v-model="currentPage"
      :total-rows="CREW_LIST.length"
      :per-page="rowsPerPage"
      aria-controls="crew-table"
      class="justify-content-center"
    />
    <b-modal
      id="new-crew"
      ref="new-crew"
      title="Add New Crew Member"
      size="sm"
      @show="resetNewForm"
      @hidden="resetNewForm"
      @ok="onSubmitNew"
    >
      <b-form
        ref="new-crew-form"
        @submit.stop.prevent="onSubmitNew"
      >
        <b-form-group
          id="first-name-input-group"
          label="First Name"
          label-for="first-name-input"
        >
          <b-form-input
            id="first-name-input"
            v-model="$v.newFormState.firstName.$model"
            name="first-name-input"
            :state="validateNewState('firstName')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback
            id="first-name-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="last-name-input-group"
          label="Last Name"
          label-for="last-name-input"
        >
          <b-form-input
            id="last-name-input"
            v-model="$v.newFormState.lastName.$model"
            name="last-name-input"
            :state="validateNewState('lastName')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback
            id="last-name-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="edit-crew"
      ref="edit-crew"
      title="Edit Crew Member"
      size="sm"
      @hidden="resetEditForm"
      @ok="onSubmitEdit"
    >
      <b-form
        ref="edit-crew-form"
        @submit.stop.prevent="onSubmitEdit"
      >
        <b-form-group
          id="first-name-input-group"
          label="First Name"
          label-for="first-name-input"
        >
          <b-form-input
            id="first-name-input"
            v-model="$v.editFormState.firstName.$model"
            name="first-name-input"
            :state="validateEditState('firstName')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback
            id="first-name-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="last-name-input-group"
          label="Last Name"
          label-for="last-name-input"
        >
          <b-form-input
            id="last-name-input"
            v-model="$v.editFormState.lastName.$model"
            name="last-name-input"
            :state="validateEditState('lastName')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback
            id="last-name-feedback"
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
  name: 'CrewList',
  data() {
    return {
      crewFields: [
        'first_name',
        'last_name',
        { key: 'btn', label: '' },
      ],
      newFormState: {
        firstName: '',
        lastName: '',
      },
      rowsPerPage: 15,
      currentPage: 1,
      editFormState: {
        id: null,
        showID: null,
        firstName: '',
        lastName: '',
      },
    };
  },
  validations: {
    newFormState: {
      firstName: {
        required,
      },
      lastName: {
        required,
      },
    },
    editFormState: {
      firstName: {
        required,
      },
      lastName: {
        required,
      },
    },
  },
  computed: {
    ...mapGetters(['CREW_LIST', 'IS_SHOW_EDITOR']),
  },
  async mounted() {
    await this.GET_CREW_LIST();
  },
  methods: {
    resetNewForm() {
      this.newFormState = {
        firstName: '',
        lastName: '',
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
        await this.ADD_CREW_MEMBER(this.newFormState);
        this.resetNewForm();
      }
    },
    validateNewState(name) {
      const { $dirty, $error } = this.$v.newFormState[name];
      return $dirty ? !$error : null;
    },
    openEditForm(crewMember) {
      if (crewMember != null) {
        this.editFormState.id = crewMember.item.id;
        this.editFormState.showID = crewMember.item.show_id;
        this.editFormState.firstName = crewMember.item.first_name;
        this.editFormState.lastName = crewMember.item.last_name;
        this.$bvModal.show('edit-crew');
      }
    },
    resetEditForm() {
      this.editFormState = {
        id: null,
        showID: null,
        firstName: '',
        lastName: '',
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
        await this.UPDATE_CREW_MEMBER(this.editFormState);
        this.resetEditForm();
      }
    },
    validateEditState(name) {
      const { $dirty, $error } = this.$v.editFormState[name];
      return $dirty ? !$error : null;
    },
    async deleteCrewMember(crewMember) {
      const msg = `Are you sure you want to delete ${crewMember.item.first_name} ${crewMember.item.last_name}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await this.DELETE_CREW_MEMBER(crewMember.item.id);
      }
    },
    ...mapActions(['GET_CREW_LIST', 'ADD_CREW_MEMBER', 'DELETE_CREW_MEMBER', 'UPDATE_CREW_MEMBER']),
  },
};
</script>
