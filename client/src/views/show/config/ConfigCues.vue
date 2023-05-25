<template>
  <b-container
    class="mx-0"
    fluid
  >
    <b-row>
      <b-col>
        <b-tabs content-class="mt-3">
          <b-tab
            title="Cue Types"
            active
          >
            <b-table
              id="cue-types-table"
              :items="CUE_TYPES"
              :fields="cueTypeFields"
              :per-page="rowsPerPage"
              :current-page="currentPage"
              show-empty
            >
              <template #head(btn)="data">
                <b-button
                  v-b-modal.new-cue-type
                  variant="outline-success"
                >
                  New Cue Type
                </b-button>
              </template>
              <template #cell(colour)="data">
                <p :style="{color: data.item.colour}">
                  <b-icon-square-fill />
                </p>
              </template>
              <template #cell(btn)="data">
                <b-button-group>
                  <b-button
                    variant="warning"
                    @click="openEditCueTypeForm(data)"
                  >
                    Edit
                  </b-button>
                  <b-button
                    variant="danger"
                    @click="deleteCueType(data)"
                  >
                    Delete
                  </b-button>
                </b-button-group>
              </template>
            </b-table>
            <b-pagination
              v-show="CUE_TYPES.length > rowsPerPage"
              v-model="currentPage"
              :total-rows="CUE_TYPES.length"
              :per-page="rowsPerPage"
              aria-controls="cue-types-table"
              class="justify-content-center"
            />
          </b-tab>
          <b-tab title="Cue Configuration">
            <cue-editor />
          </b-tab>
        </b-tabs>
      </b-col>
    </b-row>
    <b-modal
      id="new-cue-type"
      ref="new-cue-type"
      title="Add Cue Type"
      size="md"
      @show="resetNewCueTypeForm"
      @hidden="resetNewCueTypeForm"
      @ok="onSubmitNewCueType"
    >
      <b-form
        ref="new-cue-type-form"
        @submit.stop.prevent="onSubmitNewCueType"
      >
        <b-form-group
          id="prefix-input-group"
          label="Prefix"
          label-for="prefix-input"
        >
          <b-form-input
            id="prefix-input"
            v-model="$v.newCueTypeForm.prefix.$model"
            name="prefix-input"
            :state="validateNewCueTypeState('prefix')"
            aria-describedby="prefix-feedback"
          />
          <b-form-invalid-feedback
            id="prefix-feedback"
          >
            This is a required field and must be 5 characters or less.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="description-input-group"
          label="Description"
          label-for="description-input"
        >
          <b-form-input
            id="description-input"
            v-model="$v.newCueTypeForm.description.$model"
            name="description-input"
            :state="validateNewCueTypeState('description')"
            aria-describedby="description-feedback"
          />
          <b-form-invalid-feedback
            id="description-feedback"
          >
            This is a required field and must be 100 characters or less.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="colour-input-group"
          label="Colour"
          label-for="colour-input"
        >
          <b-form-input
            id="colour-input"
            v-model="$v.newCueTypeForm.colour.$model"
            name="colour-input"
            type="color"
            :state="validateNewCueTypeState('colour')"
            aria-describedby="colour-feedback"
          />
          <b-form-invalid-feedback
            id="colour-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="edit-cue-type"
      ref="edit-cue-type"
      title="Edit Cue Type"
      size="md"
      @hidden="resetEditCueTypeForm"
      @ok="onSubmitEditCueType"
    >
      <b-form
        ref="edit-cue-type-form"
        @submit.stop.prevent="onSubmitEditCueType"
      >
        <b-form-group
          id="prefix-input-group"
          label="Prefix"
          label-for="prefix-input"
        >
          <b-form-input
            id="prefix-input"
            v-model="$v.editCueTypeFormState.prefix.$model"
            name="prefix-input"
            :state="validateEditCueTypeState('prefix')"
            aria-describedby="prefix-feedback"
          />
          <b-form-invalid-feedback
            id="prefix-feedback"
          >
            This is a required field and must be 5 characters or less.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="description-input-group"
          label="Description"
          label-for="description-input"
        >
          <b-form-input
            id="description-input"
            v-model="$v.editCueTypeFormState.description.$model"
            name="description-input"
            :state="validateEditCueTypeState('description')"
            aria-describedby="description-feedback"
          />
          <b-form-invalid-feedback
            id="description-feedback"
          >
            This is a required field and must be 100 characters or less.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="colour-input-group"
          label="Colour"
          label-for="colour-input"
        >
          <b-form-input
            id="colour-input"
            v-model="$v.editCueTypeFormState.colour.$model"
            name="colour-input"
            type="color"
            :state="validateEditCueTypeState('colour')"
            aria-describedby="colour-feedback"
          />
          <b-form-invalid-feedback
            id="colour-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
  </b-container>
</template>

<script>
import { required, maxLength } from 'vuelidate/lib/validators';
import { mapGetters, mapActions } from 'vuex';

import CueEditor from '@/vue_components/show/config/cues/CueEditor.vue';

export default {
  name: 'ConfigCues',
  components: { CueEditor },
  data() {
    return {
      cueTypeFields: [
        'prefix',
        'description',
        'colour',
        { key: 'btn', label: '' },
      ],
      rowsPerPage: 15,
      currentPage: 1,
      newCueTypeForm: {
        prefix: '',
        description: '',
        colour: '#000000',
      },
      editCueTypeFormState: {
        id: null,
        prefix: '',
        description: '',
        colour: '#000000',
      },
    };
  },
  validations: {
    newCueTypeForm: {
      prefix: {
        required,
        maxLength: maxLength(5),
      },
      description: {
        maxLength: maxLength(100),
      },
      colour: {
        required,
      },
    },
    editCueTypeFormState: {
      prefix: {
        required,
        maxLength: maxLength(5),
      },
      description: {
        maxLength: maxLength(100),
      },
      colour: {
        required,
      },
    },
  },
  async mounted() {
    await this.GET_CUE_TYPES();
  },
  methods: {
    ...mapActions(['GET_CUE_TYPES', 'ADD_CUE_TYPE', 'DELETE_CUE_TYPE', 'UPDATE_CUE_TYPE']),
    resetNewCueTypeForm() {
      this.newCueTypeForm = {
        prefix: '',
        description: '',
        colour: '#000000',
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    validateNewCueTypeState(name) {
      const { $dirty, $error } = this.$v.newCueTypeForm[name];
      return $dirty ? !$error : null;
    },
    async onSubmitNewCueType(event) {
      this.$v.newCueTypeForm.$touch();
      if (this.$v.newCueTypeForm.$anyError) {
        event.preventDefault();
      } else {
        await this.ADD_CUE_TYPE(this.newCueTypeForm);
        this.resetNewCueTypeForm();
      }
    },
    async deleteCueType(cueType) {
      const msg = `Are you sure you want to delete ${cueType.item.prefix}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await this.DELETE_CUE_TYPE(cueType.item.id);
      }
    },
    openEditCueTypeForm(cueType) {
      if (cueType != null) {
        this.editCueTypeFormState.id = cueType.item.id;
        this.editCueTypeFormState.prefix = cueType.item.prefix;
        this.editCueTypeFormState.description = cueType.item.description;
        this.editCueTypeFormState.colour = cueType.item.colour;
        this.$bvModal.show('edit-cue-type');
      }
    },
    resetEditCueTypeForm() {
      this.editCueTypeFormState = {
        id: null,
        prefix: '',
        description: '',
        colour: '#000000',
      };

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    async onSubmitEditCueType(event) {
      this.$v.editCueTypeFormState.$touch();
      if (this.$v.editCueTypeFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.UPDATE_CUE_TYPE(this.editCueTypeFormState);
        this.resetEditCueTypeForm();
      }
    },
    validateEditCueTypeState(name) {
      const { $dirty, $error } = this.$v.editCueTypeFormState[name];
      return $dirty ? !$error : null;
    },
  },
  computed: {
    ...mapGetters(['CUE_TYPES']),
  },
};
</script>
