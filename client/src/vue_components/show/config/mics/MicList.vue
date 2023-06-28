<template>
  <span>
    <b-table
      id="microphones-table"
      :items="MICROPHONES"
      :fields="micFields"
      :per-page="rowsPerPage"
      :current-page="currentPage"
      show-empty
    >
      <template #head(btn)="data">
        <b-button
          v-b-modal.new-microphone
          variant="outline-success"
        >
          New Microphone
        </b-button>
      </template>
      <template #cell(btn)="data">
        <b-button-group>
          <b-button
            variant="warning"
            @click="openEditMicForm(data)"
          >
            Edit
          </b-button>
          <b-button
            variant="danger"
            @click="deleteMic(data)"
          >
            Delete
          </b-button>
        </b-button-group>
      </template>
    </b-table>
    <b-pagination
      v-show="MICROPHONES.length > rowsPerPage"
      v-model="currentPage"
      :total-rows="MICROPHONES.length"
      :per-page="rowsPerPage"
      aria-controls="microphones-table"
      class="justify-content-center"
    />
    <b-modal
      id="new-microphone"
      ref="new-microphone"
      title="Add Microphone"
      size="md"
      @show="resetNewMicrophoneForm"
      @hidden="resetNewMicrophoneForm"
      @ok="onSubmitNewMicrophone"
    >
      <b-form
        ref="new-microphone-form"
        @submit.stop.prevent="onSubmitNewMicrophone"
      >
        <b-form-group
          id="name-input-group"
          label="Name"
          label-for="name-input"
        >
          <b-form-input
            id="name-input"
            v-model="$v.newMicrophoneForm.name.$model"
            name="name-input"
            :state="validateNewMicrophone('name')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback
            id="name-feedback"
          >
            This is a required field, and must be unique.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="description-input-group"
          label="Description"
          label-for="description-input"
        >
          <b-form-input
            id="description-input"
            v-model="$v.newMicrophoneForm.description.$model"
            name="description-input"
            :state="validateNewMicrophone('description')"
            aria-describedby="description-feedback"
          />
          <b-form-invalid-feedback
            id="description-feedback"
          >
            Something went wrong!
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="edit-microphone"
      ref="edit-microphone"
      title="Edit Microphone"
      size="md"
      @hidden="resetEditMicrophoneForm"
      @ok="onSubmitEditMicrophone"
    >
      <b-form
        ref="edit-microphone-form"
        @submit.stop.prevent="onSubmitEditMicrophone"
      >
        <b-form-group
          id="name-input-group"
          label="Name"
          label-for="name-input"
        >
          <b-form-input
            id="name-input"
            v-model="$v.editMicrophoneForm.name.$model"
            name="name-input"
            :state="validateEditMicrophone('name')"
            aria-describedby="name-feedback"
          />
          <b-form-invalid-feedback
            id="name-feedback"
          >
            This is a required field, and must be unique.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="description-input-group"
          label="Description"
          label-for="description-input"
        >
          <b-form-input
            id="description-input"
            v-model="$v.editMicrophoneForm.description.$model"
            name="description-input"
            :state="validateEditMicrophone('description')"
            aria-describedby="description-feedback"
          />
          <b-form-invalid-feedback
            id="description-feedback"
          >
            Something went wrong!
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
  </span>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';
import { required } from 'vuelidate/lib/validators';

function isNameUnique(value) {
  if (value === '') {
    return true;
  }
  if (this.editMicrophoneForm.id != null) {
    if (this.MICROPHONES != null && this.MICROPHONES.length > 0) {
      return !this.MICROPHONES.some((mic) => (
        mic.name === value && mic.id !== this.editMicrophoneForm.id));
    }
  } else if (this.MICROPHONES != null && this.MICROPHONES.length > 0) {
    return !this.MICROPHONES.some((mic) => (mic.name === value));
  }
  return true;
}

export default {
  name: 'MicList',
  data() {
    return {
      micFields: [
        'name',
        'description',
        { key: 'btn', label: '' },
      ],
      rowsPerPage: 15,
      currentPage: 1,
      newMicrophoneForm: {
        name: '',
        description: '',
      },
      editMicrophoneForm: {
        id: null,
        name: '',
        description: '',
      },
    };
  },
  validations: {
    newMicrophoneForm: {
      name: {
        required,
        unique: isNameUnique,
      },
      description: {
      },
    },
    editMicrophoneForm: {
      name: {
        required,
        unique: isNameUnique,
      },
      description: {
      },
    },
  },
  methods: {
    openEditMicForm(mic) {
      if (mic != null) {
        this.editMicrophoneForm.id = mic.item.id;
        this.editMicrophoneForm.name = mic.item.name;
        this.editMicrophoneForm.description = mic.item.description;
        this.$bvModal.show('edit-microphone');
      }
    },
    resetEditMicrophoneForm() {
      this.editMicrophoneForm = {
        id: null,
        name: '',
        description: '',
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    async onSubmitEditMicrophone(event) {
      this.$v.editMicrophoneForm.$touch();
      if (this.$v.editMicrophoneForm.$anyError) {
        event.preventDefault();
      } else {
        await this.UPDATE_MICROPHONE(this.editMicrophoneForm);
        this.resetEditMicrophoneForm();
      }
    },
    validateEditMicrophone(name) {
      const { $dirty, $error } = this.$v.editMicrophoneForm[name];
      return $dirty ? !$error : null;
    },
    async deleteMic(mic) {
      const msg = `Are you sure you want to delete ${mic.item.name}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await this.DELETE_MICROPHONE(mic.item.id);
      }
    },
    resetNewMicrophoneForm() {
      this.newMicrophoneForm = {
        name: '',
        description: '',
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    async onSubmitNewMicrophone(event) {
      this.$v.newMicrophoneForm.$touch();
      if (this.$v.newMicrophoneForm.$anyError) {
        event.preventDefault();
      } else {
        await this.ADD_MICROPHONE(this.newMicrophoneForm);
        this.resetNewMicrophoneForm();
      }
    },
    validateNewMicrophone(name) {
      const { $dirty, $error } = this.$v.newMicrophoneForm[name];
      return $dirty ? !$error : null;
    },
    ...mapActions(['DELETE_MICROPHONE', 'ADD_MICROPHONE', 'UPDATE_MICROPHONE']),
  },
  computed: {
    ...mapGetters(['MICROPHONES']),
  },
};
</script>
