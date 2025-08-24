<template>
  <b-container
    class="mx-0"
    fluid
  >
    <b-row>
      <b-col>
        <b-tabs content-class="mt-3">
          <b-tab
            title="Cast List"
            active
          >
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
                  v-if="IS_SHOW_EDITOR"
                  v-b-modal.new-cast
                  variant="outline-success"
                >
                  New Cast Member
                </b-button>
              </template>
              <template #cell(btn)="data">
                <b-button-group v-if="IS_SHOW_EDITOR">
                  <b-button
                    variant="warning"
                    :disabled="submittingEditCast || deletingCast"
                    @click="openEditForm(data)"
                  >
                    Edit
                  </b-button>
                  <b-button
                    variant="danger"
                    :disabled="submittingEditCast || deletingCast"
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
          </b-tab>
          <b-tab title="Line Counts">
            <cast-line-stats />
          </b-tab>
        </b-tabs>
      </b-col>
    </b-row>
    <b-modal
      id="new-cast"
      ref="new-cast"
      title="Add New Cast Member"
      size="sm"
      :ok-disabled="$v.newFormState.$invalid || submittingNewCast"
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
      :ok-disabled="$v.editFormState.$invalid || submittingEditCast"
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
import CastLineStats from '@/vue_components/show/config/cast/CastLineStats.vue';
import log from 'loglevel';

export default {
  name: 'ConfigCast',
  components: { CastLineStats },
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
      submittingNewCast: false,
      submittingEditCast: false,
      deletingCast: false,
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
    ...mapGetters(['CAST_LIST', 'IS_SHOW_EDITOR']),
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
      this.submittingNewCast = false;

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    async onSubmitNew(event) {
      this.$v.newFormState.$touch();
      if (this.$v.newFormState.$anyError || this.submittingNewCast) {
        event.preventDefault();
        return;
      }

      this.submittingNewCast = true;
      try {
        await this.ADD_CAST_MEMBER(this.newFormState);
        this.$bvModal.hide('new-cast');
        this.resetNewForm();
      } catch (error) {
        log.error('Error submitting new cast member:', error);
        event.preventDefault();
      } finally {
        this.submittingNewCast = false;
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
      this.submittingEditCast = false;
      this.deletingCast = false;

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    async onSubmitEdit(event) {
      this.$v.editFormState.$touch();
      if (this.$v.editFormState.$anyError || this.submittingEditCast) {
        event.preventDefault();
        return;
      }

      this.submittingEditCast = true;
      try {
        await this.UPDATE_CAST_MEMBER(this.editFormState);
        this.$bvModal.hide('edit-cast');
        this.resetEditForm();
      } catch (error) {
        log.error('Error submitting edit cast member:', error);
        event.preventDefault();
      } finally {
        this.submittingEditCast = false;
      }
    },
    validateEditState(name) {
      const { $dirty, $error } = this.$v.editFormState[name];
      return $dirty ? !$error : null;
    },
    async deleteCastMember(castMember) {
      if (this.deletingCast) {
        return;
      }

      const msg = `Are you sure you want to delete ${castMember.item.first_name} ${castMember.item.last_name}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.deletingCast = true;
        try {
          await this.DELETE_CAST_MEMBER(castMember.item.id);
        } catch (error) {
          log.error('Error deleting cast member:', error);
        } finally {
          this.deletingCast = false;
        }
      }
    },
    ...mapActions(['GET_CAST_LIST', 'ADD_CAST_MEMBER', 'DELETE_CAST_MEMBER', 'UPDATE_CAST_MEMBER']),
  },
};
</script>

<style scoped>

</style>
