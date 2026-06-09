<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col>
        <b-tabs content-class="mt-3">
          <b-tab title="Cue Types" active>
            <b-table
              id="cue-types-table"
              :items="CUE_TYPES"
              :fields="cueTypeFields"
              :per-page="rowsPerPage"
              :current-page="currentPage"
              show-empty
            >
              <template #head(btn)="data">
                <b-button v-if="IS_SHOW_EDITOR" v-b-modal.new-cue-type variant="outline-success">
                  New Cue Type
                </b-button>
                <b-button
                  v-if="IS_SHOW_EDITOR"
                  variant="outline-info"
                  class="ml-2"
                  @click="openImportModal"
                >
                  Import Cue Type
                </b-button>
              </template>
              <template #cell(colour)="data">
                <p :style="{ color: data.item.colour }">
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
            <pagination-controls
              :per-page.sync="rowsPerPage"
              :current-page.sync="currentPage"
              :total-rows="CUE_TYPES.length"
              aria-controls="cue-types-table"
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
      <b-form ref="new-cue-type-form" @submit.stop.prevent="onSubmitNewCueType">
        <b-form-group id="new-prefix-input-group" label="Prefix" label-for="new-prefix-input">
          <b-form-input
            id="new-prefix-input"
            v-model="$v.newCueTypeForm.prefix.$model"
            name="new-prefix-input"
            :state="validateNewCueTypeState('prefix')"
            aria-describedby="new-prefix-feedback"
          />
          <b-form-invalid-feedback id="new-prefix-feedback">
            This is a required field and must be 5 characters or less.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="new-description-input-group"
          label="Description"
          label-for="new-description-input"
        >
          <b-form-input
            id="new-description-input"
            v-model="$v.newCueTypeForm.description.$model"
            name="new-description-input"
            :state="validateNewCueTypeState('description')"
            aria-describedby="new-description-feedback"
          />
          <b-form-invalid-feedback id="new-description-feedback">
            This is a required field and must be 100 characters or less.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group id="new-colour-input-group" label="Colour" label-for="new-colour-input">
          <b-form-input
            id="new-colour-input"
            v-model="$v.newCueTypeForm.colour.$model"
            name="new-colour-input"
            type="color"
            :state="validateNewCueTypeState('colour')"
            aria-describedby="new-colour-feedback"
          />
          <b-form-invalid-feedback id="new-colour-feedback">
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
      <b-form ref="edit-cue-type-form" @submit.stop.prevent="onSubmitEditCueType">
        <b-form-group id="edit-prefix-input-group" label="Prefix" label-for="edit-prefix-input">
          <b-form-input
            id="edit-prefix-input"
            v-model="$v.editCueTypeFormState.prefix.$model"
            name="edit-prefix-input"
            :state="validateEditCueTypeState('prefix')"
            aria-describedby="edit-prefix-feedback"
          />
          <b-form-invalid-feedback id="edit-prefix-feedback">
            This is a required field and must be 5 characters or less.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="edit-description-input-group"
          label="Description"
          label-for="edit-description-input"
        >
          <b-form-input
            id="edit-description-input"
            v-model="$v.editCueTypeFormState.description.$model"
            name="edit-description-input"
            :state="validateEditCueTypeState('description')"
            aria-describedby="edit-description-feedback"
          />
          <b-form-invalid-feedback id="edit-description-feedback">
            This is a required field and must be 100 characters or less.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group id="edit-colour-input-group" label="Colour" label-for="edit-colour-input">
          <b-form-input
            id="edit-colour-input"
            v-model="$v.editCueTypeFormState.colour.$model"
            name="edit-colour-input"
            type="color"
            :state="validateEditCueTypeState('colour')"
            aria-describedby="edit-colour-feedback"
          />
          <b-form-invalid-feedback id="edit-colour-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
    <b-modal
      id="import-cue-type-modal"
      ref="import-cue-type-modal"
      title="Import Cue Type"
      size="xl"
      hide-footer
      @hidden="resetImportState"
    >
      <div v-if="isLoadingImport" class="text-center">
        <b-spinner />
      </div>
      <div v-else-if="importCueTypeGroups.length === 0">
        <p class="text-muted">No cue types available to import from other shows.</p>
      </div>
      <div v-else>
        <b-card v-for="show in importCueTypeGroups" :key="show.id" no-body class="mb-2">
          <b-card-header style="cursor: pointer" @click="toggleImportShow(show.id)">
            <div class="d-flex justify-content-between align-items-center">
              <span>{{ show.name }}</span>
              <b-icon-chevron-down v-if="cueTypeGroupExpanded[show.id]" font-scale="0.8" />
              <b-icon-chevron-up v-else font-scale="0.8" />
            </div>
          </b-card-header>
          <b-collapse :visible="cueTypeGroupExpanded[show.id]">
            <b-table :items="show.cue_types" :fields="importCueTypeFields" small>
              <template #cell(colour)="data">
                <p :style="{ color: data.item.colour }">
                  <b-icon-square-fill />
                </p>
              </template>
              <template #cell(action)="data">
                <b-button
                  variant="outline-success"
                  size="sm"
                  :disabled="!!isImporting[data.item.id]"
                  @click="importCueType(data.item)"
                >
                  <b-spinner v-if="isImporting[data.item.id]" small />
                  <span v-else>Import</span>
                </b-button>
              </template>
            </b-table>
          </b-collapse>
        </b-card>
      </div>
    </b-modal>
  </b-container>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { required, maxLength } from 'vuelidate/lib/validators';
import { mapGetters, mapActions } from 'vuex';
import log from 'loglevel';
import paginationMixin from '@/mixins/paginationMixin';
import CueEditor from '@/vue_components/show/config/cues/CueEditor.vue';
import CueCountStats from '@/vue_components/show/config/cues/CueCountStats.vue';

export default defineComponent({
  name: 'ConfigCues',
  components: { CueCountStats, CueEditor },
  mixins: [paginationMixin],
  data() {
    return {
      tableKey: 'config_cues',
      cueTypeFields: ['prefix', 'description', 'colour', { key: 'btn', label: '' }],
      newCueTypeForm: {
        prefix: '',
        description: '',
        colour: '#000000',
      },
      editCueTypeFormState: {
        id: null as number | null,
        prefix: '',
        description: '',
        colour: '#000000',
      },
      submittingNewCueType: false,
      submittingEditCueType: false,
      deletingCueType: false,
      importCueTypeGroups: [] as any[],
      cueTypeGroupExpanded: {} as Record<number, boolean>,
      isLoadingImport: false,
      isImporting: {} as Record<number, boolean>,
      importCueTypeFields: [
        { key: 'prefix', label: 'Prefix' },
        { key: 'description', label: 'Description' },
        { key: 'colour', label: 'Colour' },
        { key: 'action', label: '' },
      ],
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
  async mounted(): Promise<void> {
    await (this as any).GET_CUE_TYPES();
  },
  methods: {
    ...mapActions([
      'GET_CUE_TYPES',
      'ADD_CUE_TYPE',
      'DELETE_CUE_TYPE',
      'UPDATE_CUE_TYPE',
      'GET_IMPORTABLE_CUE_TYPES',
    ]),
    resetNewCueTypeForm(): void {
      this.newCueTypeForm = {
        prefix: '',
        description: '',
        colour: '#000000',
      };
      this.submittingNewCueType = false;

      this.$nextTick(() => {
        (this as any).$v.$reset();
      });
    },
    validateNewCueTypeState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.newCueTypeForm[name];
      return $dirty ? !$error : null;
    },
    async onSubmitNewCueType(event: Event): Promise<void> {
      (this as any).$v.newCueTypeForm.$touch();
      if ((this as any).$v.newCueTypeForm.$anyError || this.submittingNewCueType) {
        event.preventDefault();
        return;
      }

      this.submittingNewCueType = true;
      try {
        await (this as any).ADD_CUE_TYPE(this.newCueTypeForm);
        (this as any).$bvModal.hide('new-cue-type');
        this.resetNewCueTypeForm();
      } catch (error) {
        log.error('Error submitting new cue type:', error);
        event.preventDefault();
      } finally {
        this.submittingNewCueType = false;
      }
    },
    async deleteCueType(cueType: any): Promise<void> {
      if (this.deletingCueType) {
        return;
      }

      const msg = `Are you sure you want to delete ${cueType.item.prefix}?`;
      const action = await (this as any).$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.deletingCueType = true;
        try {
          await (this as any).DELETE_CUE_TYPE(cueType.item.id);
        } catch (error) {
          log.error('Error deleting cue type:', error);
        } finally {
          this.deletingCueType = false;
        }
      }
    },
    openEditCueTypeForm(cueType: any): void {
      if (cueType != null) {
        this.editCueTypeFormState.id = cueType.item.id;
        this.editCueTypeFormState.prefix = cueType.item.prefix;
        this.editCueTypeFormState.description = cueType.item.description;
        this.editCueTypeFormState.colour = cueType.item.colour;
        (this as any).$bvModal.show('edit-cue-type');
      }
    },
    resetEditCueTypeForm(): void {
      this.editCueTypeFormState = {
        id: null,
        prefix: '',
        description: '',
        colour: '#000000',
      };
      this.submittingEditCueType = false;
      this.deletingCueType = false;

      this.$nextTick(() => {
        (this as any).$v.$reset();
      });
    },
    async onSubmitEditCueType(event: Event): Promise<void> {
      (this as any).$v.editCueTypeFormState.$touch();
      if ((this as any).$v.editCueTypeFormState.$anyError || this.submittingEditCueType) {
        event.preventDefault();
        return;
      }

      this.submittingEditCueType = true;
      try {
        await (this as any).UPDATE_CUE_TYPE(this.editCueTypeFormState);
        (this as any).$bvModal.hide('edit-cue-type');
        this.resetEditCueTypeForm();
      } catch (error) {
        log.error('Error submitting edit cue type:', error);
        event.preventDefault();
      } finally {
        this.submittingEditCueType = false;
      }
    },
    validateEditCueTypeState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.editCueTypeFormState[name];
      return $dirty ? !$error : null;
    },
    async openImportModal(): Promise<void> {
      (this as any).$bvModal.show('import-cue-type-modal');
      this.isLoadingImport = true;
      try {
        const data = await (this as any).GET_IMPORTABLE_CUE_TYPES();
        this.importCueTypeGroups = data.cue_type_groups;
        data.cue_type_groups.forEach((show: any) => {
          this.$set(this.cueTypeGroupExpanded, show.id, true);
        });
      } catch (e) {
        log.error('Error loading importable cue types:', e);
      } finally {
        this.isLoadingImport = false;
      }
    },
    toggleImportShow(showId: number): void {
      this.$set(this.cueTypeGroupExpanded, showId, !this.cueTypeGroupExpanded[showId]);
    },
    async importCueType(cueType: any): Promise<void> {
      this.$set(this.isImporting, cueType.id, true);
      try {
        await (this as any).ADD_CUE_TYPE({
          prefix: cueType.prefix,
          description: cueType.description,
          colour: cueType.colour,
        });
      } finally {
        this.$set(this.isImporting, cueType.id, false);
      }
    },
    resetImportState(): void {
      this.importCueTypeGroups = [];
      this.cueTypeGroupExpanded = {};
      this.isLoadingImport = false;
      this.isImporting = {};
    },
  },
});
</script>
