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
                  v-if="IS_SHOW_EDITOR"
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
                <b-button-group v-if="IS_SHOW_EDITOR">
                  <b-button
                    variant="warning"
                    :disabled="submittingNewCueType || submittingEditCueType || deletingCueType"
                    @click="openEditCueTypeForm(data)"
                  >
                    Edit
                  </b-button>
                  <b-button
                    variant="danger"
                    :disabled="submittingNewCueType || submittingEditCueType || deletingCueType"
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
          <b-tab title="Cue Counts">
            <cue-count-stats />
          </b-tab>
        </b-tabs>
      </b-col>
    </b-row>
    <b-modal
      id="new-cue-type"
      ref="new-cue-type"
      title="Add Cue Type"
      size="md"
      :ok-disabled="$v.newCueTypeForm.$invalid || submittingNewCueType"
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
      :ok-disabled="$v.editCueTypeFormState.$invalid || submittingEditCueType"
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
import log from 'loglevel';

import CueEditor from '@/vue_components/show/config/cues/CueEditor.vue';
import CueCountStats from '@/vue_components/show/config/cues/CueCountStats.vue';

export default {
  name: 'ConfigCues',
  components: { CueCountStats, CueEditor },
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
      submittingNewCueType: false,
      submittingEditCueType: false,
      deletingCueType: false,
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
  computed: {
    ...mapGetters(['CUE_TYPES', 'IS_SHOW_EDITOR']),
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
      this.submittingNewCueType = false;

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
      if (this.$v.newCueTypeForm.$anyError || this.submittingNewCueType) {
        event.preventDefault();
        return;
      }

      this.submittingNewCueType = true;
      try {
        await this.ADD_CUE_TYPE(this.newCueTypeForm);
        this.$bvModal.hide('new-cue-type');
        this.resetNewCueTypeForm();
      } catch (error) {
        log.error('Error submitting new cue type:', error);
        event.preventDefault();
      } finally {
        this.submittingNewCueType = false;
      }
    },
    async deleteCueType(cueType) {
      if (this.deletingCueType) {
        return;
      }

      const msg = `Are you sure you want to delete ${cueType.item.prefix}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.deletingCueType = true;
        try {
          await this.DELETE_CUE_TYPE(cueType.item.id);
        } catch (error) {
          log.error('Error deleting cue type:', error);
        } finally {
          this.deletingCueType = false;
        }
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
      this.submittingEditCueType = false;
      this.deletingCueType = false;

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    async onSubmitEditCueType(event) {
      this.$v.editCueTypeFormState.$touch();
      if (this.$v.editCueTypeFormState.$anyError || this.submittingEditCueType) {
        event.preventDefault();
        return;
      }

      this.submittingEditCueType = true;
      try {
        await this.UPDATE_CUE_TYPE(this.editCueTypeFormState);
        this.$bvModal.hide('edit-cue-type');
        this.resetEditCueTypeForm();
      } catch (error) {
        log.error('Error submitting edit cue type:', error);
        event.preventDefault();
      } finally {
        this.submittingEditCueType = false;
      }
    },
    validateEditCueTypeState(name) {
      const { $dirty, $error } = this.$v.editCueTypeFormState[name];
      return $dirty ? !$error : null;
    },
  },
};
</script>
