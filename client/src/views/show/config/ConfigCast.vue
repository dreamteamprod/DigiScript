<template>
  <b-container
    class="mx-0"
    fluid
  >
    <b-row>
      <b-col>
        <h5>Cast List</h5>
        <b-table
          id="cast-table"
          :items="CAST_LIST"
          :fields="castFields"
          :per-page="rowsPerPage"
          :current-page="currentPage"
          show-empty
        >
          <template #head(btn)="data">
            <b-button
              v-b-modal.new-cast
              variant="outline-success"
            >
              New Cast Member
            </b-button>
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
                @click="deleteCastMember(data)"
              >
                Delete
              </b-button>
            </b-button-group>
          </template>
        </b-table>
        <b-pagination
          v-show="CAST_LIST.length > rowsPerPage"
          v-model="currentPage"
          :total-rows="CAST_LIST.length"
          :per-page="rowsPerPage"
          aria-controls="cast-table"
          class="justify-content-center"
        />
      </b-col>
    </b-row>
    <b-modal
      id="new-cast"
      ref="new-cast"
      title="Add New Cast Member"
      size="sm"
      @show="resetNewForm"
      @hidden="resetNewForm"
      @ok="onSubmitNew"
    >
      <b-form
        ref="new-cast-form"
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
      id="edit-cast"
      ref="edit-cast"
      title="Edit Cast Member"
      size="sm"
      @hidden="resetEditForm"
      @ok="onSubmitEdit"
    >
      <b-form
        ref="edit-cast-form"
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
  </b-container>
</template>

<script>
import { required } from 'vuelidate/lib/validators';
import { mapGetters, mapActions } from 'vuex';

export default {
  name: 'ConfigCast',
  data() {
    return {
      castFields: [
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
  async mounted() {
    await this.GET_CAST_LIST();
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
        await this.ADD_CAST_MEMBER(this.newFormState);
        this.resetNewForm();
      }
    },
    validateNewState(name) {
      const { $dirty, $error } = this.$v.newFormState[name];
      return $dirty ? !$error : null;
    },
    openEditForm(castMember) {
      if (castMember != null) {
        this.editFormState.id = castMember.item.id;
        this.editFormState.showID = castMember.item.show_id;
        this.editFormState.firstName = castMember.item.first_name;
        this.editFormState.lastName = castMember.item.last_name;
        this.$bvModal.show('edit-cast');
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
        await this.UPDATE_CAST_MEMBER(this.editFormState);
        this.resetEditForm();
      }
    },
    validateEditState(name) {
      const { $dirty, $error } = this.$v.editFormState[name];
      return $dirty ? !$error : null;
    },
    async deleteCastMember(castMember) {
      const msg = `Are you sure you want to delete ${castMember.item.first_name} ${castMember.item.last_name}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await this.DELETE_CAST_MEMBER(castMember.item.id);
      }
    },
    ...mapActions(['GET_CAST_LIST', 'ADD_CAST_MEMBER', 'DELETE_CAST_MEMBER', 'UPDATE_CAST_MEMBER']),
  },
  computed: {
    ...mapGetters(['CAST_LIST']),
  },
};
</script>

<style scoped>

</style>
