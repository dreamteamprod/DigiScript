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
        <b-button v-if="IS_SHOW_EDITOR" v-b-modal.new-crew variant="outline-success">
          New Crew Member
        </b-button>
      </template>
      <template #cell(btn)="data">
        <b-button-group v-if="IS_SHOW_EDITOR">
          <b-button variant="warning" @click="openEditForm(data)"> Edit </b-button>
          <b-button variant="danger" @click="deleteCrewMember(data)"> Delete </b-button>
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
      <b-form ref="new-crew-form" @submit.stop.prevent="onSubmitNew">
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
      id="edit-crew"
      ref="edit-crew"
      title="Edit Crew Member"
      size="sm"
      @hidden="resetEditForm"
      @ok="onSubmitEdit"
    >
      <b-form ref="edit-crew-form" @submit.stop.prevent="onSubmitEdit">
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
  </span>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { required } from 'vuelidate/lib/validators';
import { mapGetters, mapActions } from 'vuex';
import formValidationMixin from '@/mixins/formValidationMixin';

export default defineComponent({
  name: 'CrewList',
  mixins: [formValidationMixin],
  data() {
    return {
      crewFields: ['first_name', 'last_name', { key: 'btn', label: '' }],
      newFormState: {
        firstName: '',
        lastName: '',
      },
      rowsPerPage: 15,
      currentPage: 1,
      editFormState: {
        id: null as number | null,
        showID: null as number | null,
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
  async mounted(): Promise<void> {
    await (this as any).GET_CREW_LIST();
  },
  methods: {
    resetNewForm(): void {
      (this as any).resetForm('newFormState', {
        firstName: '',
        lastName: '',
      });
    },
    async onSubmitNew(event: Event): Promise<void> {
      (this as any).$v.newFormState.$touch();
      if ((this as any).$v.newFormState.$anyError) {
        event.preventDefault();
      } else {
        await (this as any).ADD_CREW_MEMBER(this.newFormState);
        this.resetNewForm();
      }
    },
    openEditForm(crewMember: any): void {
      if (crewMember != null) {
        this.editFormState.id = crewMember.item.id;
        this.editFormState.showID = crewMember.item.show_id;
        this.editFormState.firstName = crewMember.item.first_name;
        this.editFormState.lastName = crewMember.item.last_name;
        (this as any).$bvModal.show('edit-crew');
      }
    },
    resetEditForm(): void {
      (this as any).resetForm('editFormState', {
        id: null,
        showID: null,
        firstName: '',
        lastName: '',
      });
    },
    async onSubmitEdit(event: Event): Promise<void> {
      (this as any).$v.editFormState.$touch();
      if ((this as any).$v.editFormState.$anyError) {
        event.preventDefault();
      } else {
        await (this as any).UPDATE_CREW_MEMBER(this.editFormState);
        this.resetEditForm();
      }
    },
    async deleteCrewMember(crewMember: any): Promise<void> {
      const msg = `Are you sure you want to delete ${crewMember.item.first_name} ${crewMember.item.last_name}?`;
      const action = await (this as any).$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await (this as any).DELETE_CREW_MEMBER(crewMember.item.id);
      }
    },
    ...mapActions(['GET_CREW_LIST', 'ADD_CREW_MEMBER', 'DELETE_CREW_MEMBER', 'UPDATE_CREW_MEMBER']),
  },
});
</script>
