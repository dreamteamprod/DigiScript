<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col>
        <b-tabs content-class="mt-3">
          <b-tab title="Cast List" active>
            <b-table
              id="cast-table"
              :items="CAST_LIST"
              :fields="castFields"
              :per-page="rowsPerPage"
              :current-page="currentPage"
              show-empty
            >
              <template #head(btn)="data">
                <b-button v-if="IS_SHOW_EDITOR" v-b-modal.new-cast variant="outline-success">
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
            <pagination-controls
              :per-page.sync="rowsPerPage"
              :current-page.sync="currentPage"
              :total-rows="CAST_LIST.length"
              aria-controls="cast-table"
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
      <b-form ref="new-cast-form" @submit.stop.prevent="onSubmitNew">
        <b-form-group
          id="new-first-name-input-group"
          label="First Name"
          label-for="new-first-name-input"
        >
          <b-form-input
            id="new-first-name-input"
            v-model="$v.newFormState.firstName.$model"
            name="new-first-name-input"
            :state="getValidationState('newFormState', 'firstName')"
            aria-describedby="new-first-name-feedback"
          />
          <b-form-invalid-feedback id="new-first-name-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="new-last-name-input-group"
          label="Last Name"
          label-for="new-last-name-input"
        >
          <b-form-input
            id="new-last-name-input"
            v-model="$v.newFormState.lastName.$model"
            name="new-last-name-input"
            :state="getValidationState('newFormState', 'lastName')"
            aria-describedby="new-last-name-feedback"
          />
          <b-form-invalid-feedback id="new-last-name-feedback">
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
      <b-form ref="edit-cast-form" @submit.stop.prevent="onSubmitEdit">
        <b-form-group
          id="edit-first-name-input-group"
          label="First Name"
          label-for="edit-first-name-input"
        >
          <b-form-input
            id="edit-first-name-input"
            v-model="$v.editFormState.firstName.$model"
            name="edit-first-name-input"
            :state="getValidationState('editFormState', 'firstName')"
            aria-describedby="edit-first-name-feedback"
          />
          <b-form-invalid-feedback id="edit-first-name-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="edit-last-name-input-group"
          label="Last Name"
          label-for="edit-last-name-input"
        >
          <b-form-input
            id="edit-last-name-input"
            v-model="$v.editFormState.lastName.$model"
            name="edit-last-name-input"
            :state="getValidationState('editFormState', 'lastName')"
            aria-describedby="edit-last-name-feedback"
          />
          <b-form-invalid-feedback id="edit-last-name-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
  </b-container>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { required } from 'vuelidate/lib/validators';
import { mapGetters, mapActions } from 'vuex';
import CastLineStats from '@/vue_components/show/config/cast/CastLineStats.vue';
import log from 'loglevel';
import formValidationMixin from '@/mixins/formValidationMixin';
import paginationMixin from '@/mixins/paginationMixin';

export default defineComponent({
  name: 'ConfigCast',
  components: { CastLineStats },
  mixins: [formValidationMixin, paginationMixin],
  data() {
    return {
      tableKey: 'config_cast',
      castFields: ['first_name', 'last_name', { key: 'btn', label: '' }],
      newFormState: {
        firstName: '',
        lastName: '',
      },
      editFormState: {
        id: null as number | null,
        showID: null as number | null,
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
      firstName: { required },
      lastName: { required },
    },
    editFormState: {
      firstName: { required },
      lastName: { required },
    },
  },
  computed: {
    ...mapGetters(['CAST_LIST', 'IS_SHOW_EDITOR']),
  },
  async mounted(): Promise<void> {
    await (this as any).GET_CAST_LIST();
  },
  methods: {
    resetNewForm(): void {
      (this as any).resetForm('newFormState', { firstName: '', lastName: '' });
      this.submittingNewCast = false;
    },
    async onSubmitNew(event: Event): Promise<void> {
      (this as any).$v.newFormState.$touch();
      if ((this as any).$v.newFormState.$anyError || this.submittingNewCast) {
        event.preventDefault();
        return;
      }
      this.submittingNewCast = true;
      try {
        await (this as any).ADD_CAST_MEMBER(this.newFormState);
        (this as any).$bvModal.hide('new-cast');
        this.resetNewForm();
      } catch (error) {
        log.error('Error submitting new cast member:', error);
        event.preventDefault();
      } finally {
        this.submittingNewCast = false;
      }
    },
    openEditForm(castMember: any): void {
      if (castMember != null) {
        this.editFormState.id = castMember.item.id;
        this.editFormState.showID = castMember.item.show_id;
        this.editFormState.firstName = castMember.item.first_name;
        this.editFormState.lastName = castMember.item.last_name;
        (this as any).$bvModal.show('edit-cast');
      }
    },
    resetEditForm(): void {
      (this as any).resetForm('editFormState', {
        id: null,
        showID: null,
        firstName: '',
        lastName: '',
      });
      this.submittingEditCast = false;
      this.deletingCast = false;
    },
    async onSubmitEdit(event: Event): Promise<void> {
      (this as any).$v.editFormState.$touch();
      if ((this as any).$v.editFormState.$anyError || this.submittingEditCast) {
        event.preventDefault();
        return;
      }
      this.submittingEditCast = true;
      try {
        await (this as any).UPDATE_CAST_MEMBER(this.editFormState);
        (this as any).$bvModal.hide('edit-cast');
        this.resetEditForm();
      } catch (error) {
        log.error('Error submitting edit cast member:', error);
        event.preventDefault();
      } finally {
        this.submittingEditCast = false;
      }
    },
    async deleteCastMember(castMember: any): Promise<void> {
      if (this.deletingCast) {
        return;
      }
      const msg = `Are you sure you want to delete ${castMember.item.first_name} ${castMember.item.last_name}?`;
      const action = await (this as any).$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.deletingCast = true;
        try {
          await (this as any).DELETE_CAST_MEMBER(castMember.item.id);
        } catch (error) {
          log.error('Error deleting cast member:', error);
        } finally {
          this.deletingCast = false;
        }
      }
    },
    ...mapActions(['GET_CAST_LIST', 'ADD_CAST_MEMBER', 'DELETE_CAST_MEMBER', 'UPDATE_CAST_MEMBER']),
  },
});
</script>

<style scoped></style>
