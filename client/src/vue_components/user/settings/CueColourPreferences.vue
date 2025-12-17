<template>
  <b-table
    v-if="CURRENT_SHOW != null"
    id="cue-colour-table"
    :items="tableData"
    :fields="columns"
    :per-page="rowsPerPage"
    :current-page="currentPage"
    show-empty
  >
    <template #head(btn)="data">
      <b-button
        v-b-modal.cue-colour-new-override-select
        variant="outline-success"
        :disabled="overrideChoices.length <= 1"
      >
        New Override
      </b-button>
      <b-modal
        id="cue-colour-new-override-select"
        ref="cue-colour-new-override-select"
        title="Add New Cue Colour Override"
        :ok-disabled="newFormState.cueTypeId == null || isSubmittingNew"
        @show="resetOverrideSelect"
        @ok="openNewOverrideModal"
      >
        <b-form>
          <b-form-select
            v-model="newFormState.cueTypeId"
            :options="overrideChoices"
          />
        </b-form>
      </b-modal>
      <b-modal
        id="cue-colour-new-override-modal"
        ref="cue-colour-new-override-modal"
        title="Add New Cue Colour Override"
        size="lg"
        :ok-disabled="isSubmittingNew"
        @hidden="resetNewFormState"
        @ok="onSubmitNewOverride"
      >
        <div>
          <h4>Example Cue Button</h4>
          <button
            class="cue-button-example"
            :style="{'background-color': newFormState.colour,
                     color: contrastColor({'bgColor': newFormState.colour})}"
          >
            {{ newFormCueTypePrefix }}
          </button>
        </div>
        <div>
          <h4>Configuration Options</h4>
          <b-form
            ref="new-config-form"
            @ok="onSubmitNewOverride"
          >
            <b-form-group
              id="colour-input-group"
              label="Cue Button Colour"
              label-for="colour-input"
            >
              <b-form-input
                id="colour-input"
                v-model="$v.newFormState.colour.$model"
                name="colour-input"
                type="color"
                :state="validateNewState('colour')"
                aria-describedby="colour-feedback"
              />
              <b-form-invalid-feedback
                id="colour-feedback"
              >
                This is a required field.
              </b-form-invalid-feedback>
            </b-form-group>
          </b-form>
        </div>
      </b-modal>
      <b-modal
        id="cue-colour-edit-override-modal"
        ref="cue-colour-edit-override-modal"
        title="Edit Cue Colour Override"
        size="lg"
        :ok-disabled="isSubmittingEdit"
        @hidden="resetEditFormState"
        @ok="onSubmitEditOverride"
      >
        <div>
          <h4>Example Cue Button</h4>
          <button
            class="cue-button-example"
            :style="{'background-color': editFormState.colour,
                     color: contrastColor({'bgColor': editFormState.colour})}"
          >
            {{ editFormCueTypePrefix }}
          </button>
        </div>
        <div>
          <h4>Configuration Options</h4>
          <b-form
            ref="edit-config-form"
            @ok="onSubmitEditOverride"
          >
            <b-form-group
              id="colour-input-group"
              label="Cue Button Colour"
              label-for="colour-input"
            >
              <b-form-input
                id="colour-input"
                v-model="$v.editFormState.colour.$model"
                name="colour-input"
                type="color"
                :state="validateEditState('colour')"
                aria-describedby="colour-feedback"
              />
              <b-form-invalid-feedback
                id="colour-feedback"
              >
                This is a required field.
              </b-form-invalid-feedback>
            </b-form-group>
          </b-form>
        </div>
      </b-modal>
    </template>
    <template #cell(description)="data">
      {{ CUE_TYPES.find((elem) => elem.id === data.item.settings.id).description }}
    </template>
    <template #cell(example)="data">
      <button
        class="cue-button-example"
        :style="{'background-color': data.item.settings.colour,
                 color: contrastColor({'bgColor': data.item.settings.colour})}"
      >
        {{ CUE_TYPES.find((elem) => elem.id === data.item.settings.id).prefix }}
      </button>
    </template>
    <template #cell(btn)="data">
      <b-button-group>
        <b-button
          variant="warning"
          :disabled="isSubmittingEdit || isDeleting"
          @click="openEditForm(data)"
        >
          Edit
        </b-button>
        <b-button
          variant="danger"
          :disabled="isSubmittingEdit || isDeleting"
          @click="deleteOverride(data)"
        >
          Delete
        </b-button>
      </b-button-group>
    </template>
  </b-table>
  <b-alert
    v-else
    variant="danger"
  >
    No show loaded.
  </b-alert>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';
import { required } from 'vuelidate/lib/validators';
import { contrastColor } from 'contrast-color';
import log from 'loglevel';

export default {
  name: 'CueColourPreferences',
  data() {
    return {
      columns: [
        'description',
        { key: 'example', label: 'Example Cue Button' },
        { key: 'btn', label: '' },
      ],
      rowsPerPage: 15,
      currentPage: 1,
      newFormState: {
        cueTypeId: null,
        colour: '#FF0000',
      },
      editFormState: {
        id: null,
        cueTypeId: null,
        colour: '#FF0000',
      },
      isSubmittingNew: false,
      isSubmittingEdit: false,
      isDeleting: false,
    };
  },
  computed: {
    overrideChoices() {
      return [
        { value: null, text: 'Please select a cue type', disabled: true },
        ...this.CUE_TYPES.filter((item) => !this.CUE_COLOUR_OVERRIDES.map(
          (elem) => elem.settings.id,
        ).includes(item.id), this).map((item) => ({ value: item.id, text: `${item.prefix} - ${item.description}` })),
      ];
    },
    tableData() {
      return this.CUE_COLOUR_OVERRIDES
        .filter((item) => this.CUE_TYPES
          .map((elem) => elem.id).includes(item.settings.id), this);
    },
    newFormCueTypePrefix() {
      if (this.newFormState.cueTypeId) {
        const cueType = this.CUE_TYPES.find((ct) => ct.id === this.newFormState.cueTypeId);
        return cueType ? cueType.prefix : '';
      }
      return '';
    },
    editFormCueTypePrefix() {
      if (this.editFormState.cueTypeId) {
        const cueType = this.CUE_TYPES.find((ct) => ct.id === this.editFormState.cueTypeId);
        return cueType ? cueType.prefix : '';
      }
      return '';
    },
    createPayload() {
      return {
        cueTypeId: this.newFormState.cueTypeId,
        colour: this.newFormState.colour,
      };
    },
    editPayload() {
      return {
        id: this.editFormState.id,
        colour: this.editFormState.colour,
      };
    },
    ...mapGetters(['CURRENT_SHOW', 'CUE_TYPES', 'CUE_COLOUR_OVERRIDES']),
  },
  async beforeMount() {
    await this.GET_SHOW_DETAILS();
    if (this.CURRENT_SHOW != null) {
      await this.GET_CUE_TYPES();
      await this.GET_CUE_COLOUR_OVERRIDES();
    }
  },
  methods: {
    contrastColor,
    resetOverrideSelect() {
      this.newFormState.cueTypeId = null;
    },
    openNewOverrideModal(event) {
      const cueTypeToOverride = this.CUE_TYPES
        .find((item) => item.id === this.newFormState.cueTypeId, this);
      if (cueTypeToOverride == null) {
        log.error('Could not find cue type to override!');
        this.$toast.error('Could not find cue type to override!');
      } else {
        this.newFormState.cueTypeId = cueTypeToOverride.id;
        this.newFormState.colour = cueTypeToOverride.colour;
        this.$bvModal.show('cue-colour-new-override-modal');
      }
    },
    resetNewFormState() {
      this.newFormState = {
        cueTypeId: null,
        colour: '#FF0000',
      };
      this.isSubmittingNew = false;
      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    resetEditFormState() {
      this.editFormState = {
        id: null,
        cueTypeId: null,
        colour: '#FF0000',
      };
      this.isSubmittingEdit = false;
      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    async onSubmitNewOverride(event) {
      this.$v.newFormState.$touch();
      if (this.$v.newFormState.$anyError) {
        event.preventDefault();
        return;
      }

      if (this.isSubmittingNew) {
        event.preventDefault();
        return;
      }

      this.isSubmittingNew = true;

      try {
        await this.ADD_CUE_COLOUR_OVERRIDE(this.createPayload);
        this.$refs['cue-colour-new-override-modal'].hide();
        this.resetNewFormState();
      } catch (error) {
        log.error('Error adding new cue colour override:', error);
        this.$toast.error('Failed to add new override');
        event.preventDefault();
      } finally {
        this.isSubmittingNew = false;
      }
    },
    async onSubmitEditOverride(event) {
      this.$v.editFormState.$touch();
      if (this.$v.editFormState.$anyError) {
        event.preventDefault();
        return;
      }

      if (this.isSubmittingEdit) {
        event.preventDefault();
        return;
      }

      this.isSubmittingEdit = true;

      try {
        await this.UPDATE_CUE_COLOUR_OVERRIDE(this.editPayload);
        this.$refs['cue-colour-edit-override-modal'].hide();
        this.resetEditFormState();
      } catch (error) {
        log.error('Error updating cue colour override:', error);
        this.$toast.error('Failed to update override');
        event.preventDefault();
      } finally {
        this.isSubmittingEdit = false;
      }
    },
    validateNewState(name) {
      const { $dirty, $error } = this.$v.newFormState[name];
      return $dirty ? !$error : null;
    },
    validateEditState(name) {
      const { $dirty, $error } = this.$v.editFormState[name];
      return $dirty ? !$error : null;
    },
    async deleteOverride(override) {
      if (this.isDeleting) {
        return;
      }

      const msg = 'Are you sure you want to delete this override?';
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.isDeleting = true;
        try {
          await this.DELETE_CUE_COLOUR_OVERRIDE(override.item.id);
        } catch (error) {
          log.error('Error deleting cue colour override:', error);
          this.$toast.error('Failed to delete override');
        } finally {
          this.isDeleting = false;
        }
      }
    },
    openEditForm(override) {
      if (override != null) {
        const { settings } = override.item;
        this.editFormState.id = override.item.id;
        this.editFormState.cueTypeId = settings.id;
        this.editFormState.colour = settings.colour;
        this.$bvModal.show('cue-colour-edit-override-modal');
      }
    },
    ...mapActions(['GET_SHOW_DETAILS', 'GET_CUE_TYPES',
      'GET_CUE_COLOUR_OVERRIDES', 'ADD_CUE_COLOUR_OVERRIDE',
      'DELETE_CUE_COLOUR_OVERRIDE', 'UPDATE_CUE_COLOUR_OVERRIDE']),
  },
  validations: {
    newFormState: {
      colour: {
        required,
      },
    },
    editFormState: {
      colour: {
        required,
      },
    },
  },
};
</script>

<style scoped>
.cue-button-example {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  font-weight: bold;
  font-size: 14px;
  cursor: default;
  min-width: 60px;
}
</style>
