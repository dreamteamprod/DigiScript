<template>
  <b-table
    id="stage-directions-table"
    :items="STAGE_DIRECTION_STYLES"
    :fields="columns"
    :per-page="rowsPerPage"
    :current-page="currentPage"
    show-empty
  >
    <template #head(btn)="data">
      <b-button v-if="IS_SCRIPT_EDITOR" v-b-modal.new-config-modal variant="outline-success">
        New Style
      </b-button>
      <b-button
        v-if="IS_SCRIPT_EDITOR"
        variant="outline-info"
        class="ml-2"
        @click="openImportModal"
      >
        Import Style
      </b-button>
      <b-modal
        id="import-style-modal"
        ref="import-style-modal"
        title="Import Stage Direction Style"
        size="xl"
        ok-only
        ok-title="Close"
        @hidden="resetImportState"
      >
        <div v-if="isLoadingImport" class="text-center py-3">
          <b-spinner />
        </div>
        <div v-else-if="importStyleGroups.length === 0" class="text-muted text-center py-3">
          No styles available to import from other shows.
        </div>
        <div v-else>
          <b-card v-for="show in importStyleGroups" :key="show.id" no-body class="mb-2">
            <b-card-header class="section-card-header" @click="toggleImportShow(show.id)">
              <div class="d-flex justify-content-between align-items-center">
                <span>{{ show.name }}</span>
                <b-icon-chevron-down v-if="styleGroupExpanded[show.id]" font-scale="0.8" />
                <b-icon-chevron-up v-else font-scale="0.8" />
              </div>
            </b-card-header>
            <b-collapse :visible="styleGroupExpanded[show.id]">
              <b-card-body class="p-0">
                <b-table :items="show.styles" :fields="importColumns" small show-empty class="mb-0">
                  <template #cell(example)="row">
                    <i class="example-stage-direction" :style="exampleCss(row.item)">
                      <template v-if="row.item.text_format === 'upper'">
                        {{ exampleText | uppercase }}
                      </template>
                      <template v-else-if="row.item.text_format === 'lower'">
                        {{ exampleText | lowercase }}
                      </template>
                      <template v-else>
                        {{ exampleText }}
                      </template>
                    </i>
                  </template>
                  <template #cell(btn)="row">
                    <b-button
                      variant="outline-success"
                      size="sm"
                      :disabled="!!isImporting[row.item.id]"
                      @click="importStyle(row.item)"
                    >
                      <b-spinner v-if="isImporting[row.item.id]" small />
                      <span v-else>Import</span>
                    </b-button>
                  </template>
                </b-table>
              </b-card-body>
            </b-collapse>
          </b-card>
        </div>
      </b-modal>
      <b-modal
        id="new-config-modal"
        ref="new-config-modal"
        title="Add New Config"
        size="lg"
        :ok-disabled="isSubmittingNew"
        @show="resetNewFormState"
        @hidden="resetNewFormState"
        @ok="onSubmitNewStyle"
      >
        <div>
          <h4>Example Stage Direction</h4>
          <i class="example-stage-direction" :style="newFormExampleCss">
            <template v-if="newStyleFormState.textFormat === 'upper'">
              {{ exampleText | uppercase }}
            </template>
            <template v-else-if="newStyleFormState.textFormat === 'lower'">
              {{ exampleText | lowercase }}
            </template>
            <template v-else>
              {{ exampleText }}
            </template>
          </i>
        </div>
        <div>
          <h4>Configuration Options</h4>
          <b-form ref="new-config-form" @ok="onSubmitNewStyle">
            <b-form-group
              id="new-description-input-group"
              label="Description"
              label-for="new-description-input"
            >
              <b-form-input
                id="new-description-input"
                v-model="$v.newStyleFormState.description.$model"
                name="new-description-input"
                :state="validateNewStyleState('description')"
                aria-describedby="new-description-feedback"
              />
              <b-form-invalid-feedback id="new-description-feedback">
                This is a required field.
              </b-form-invalid-feedback>
            </b-form-group>
            <b-form-group
              id="new-styling-group"
              label="Default Styles"
              label-for="new-styling-input"
            >
              <b-button-group id="new-styling-input">
                <b-button
                  v-for="(btn, idx) in $v.newStyleFormState.styleOptions.$model"
                  :key="idx"
                  :pressed.sync="btn.state"
                  variant="primary"
                >
                  {{ btn.caption }}
                </b-button>
              </b-button-group>
            </b-form-group>
            <b-form-group
              id="new-text-formatting-group"
              label="Default Text Format"
              label-for="new-text-format-input"
            >
              <b-form-select
                id="new-text-format-input"
                v-model="$v.newStyleFormState.textFormat.$model"
              >
                <b-form-select-option value="default"> Default </b-form-select-option>
                <b-form-select-option value="upper"> Uppercase </b-form-select-option>
                <b-form-select-option value="lower"> Lowercase </b-form-select-option>
              </b-form-select>
            </b-form-group>
            <b-form-group
              id="new-text-colour-input-group"
              label="Text Colour"
              label-for="new-text-colour-input"
            >
              <b-form-input
                id="new-text-colour-input"
                v-model="$v.newStyleFormState.textColour.$model"
                name="new-text-colour-input"
                type="color"
                :state="validateNewStyleState('textColour')"
                aria-describedby="new-colour-feedback"
              />
              <b-form-invalid-feedback id="new-colour-feedback">
                This is a required field.
              </b-form-invalid-feedback>
            </b-form-group>
            <b-form-group
              id="new-background-colour-enable-group"
              label="Background Colour"
              label-for="new-background-colour-enable"
            >
              <b-form-checkbox
                id="new-background-colour-enable"
                v-model="$v.newStyleFormState.enableBackgroundColour.$model"
                :switch="true"
              />
            </b-form-group>
            <b-form-group
              v-if="newStyleFormState.enableBackgroundColour"
              id="new-background-colour-input-group"
            >
              <b-form-input
                id="new-background-colour-picker"
                v-model="$v.newStyleFormState.backgroundColour.$model"
                name="new-background-colour-picker"
                type="color"
                :state="validateNewStyleState('textColour')"
              />
            </b-form-group>
          </b-form>
        </div>
      </b-modal>
      <b-modal
        id="edit-config-modal"
        ref="edit-config-modal"
        title="Edit Config"
        size="lg"
        :ok-disabled="isSubmittingEdit"
        @hidden="resetEditFormState"
        @ok="onSubmitEditStyle"
      >
        <div>
          <h4>Example Stage Direction</h4>
          <i class="example-stage-direction" :style="editFormExampleCss">
            <template v-if="editStyleFormState.textFormat === 'upper'">
              {{ exampleText | uppercase }}
            </template>
            <template v-else-if="editStyleFormState.textFormat === 'lower'">
              {{ exampleText | lowercase }}
            </template>
            <template v-else>
              {{ exampleText }}
            </template>
          </i>
        </div>
        <div>
          <h4>Configuration Options</h4>
          <b-form ref="edit-config-form" @ok="onSubmitEditStyle">
            <b-form-group
              id="edit-description-input-group"
              label="Description"
              label-for="edit-description-input"
            >
              <b-form-input
                id="edit-description-input"
                v-model="$v.editStyleFormState.description.$model"
                name="edit-description-input"
                :state="validateEditStyleState('description')"
                aria-describedby="edit-description-feedback"
              />
              <b-form-invalid-feedback id="edit-description-feedback">
                This is a required field.
              </b-form-invalid-feedback>
            </b-form-group>
            <b-form-group
              id="edit-styling-group"
              label="Default Styles"
              label-for="edit-styling-input"
            >
              <b-button-group id="edit-styling-input">
                <b-button
                  v-for="(btn, idx) in $v.editStyleFormState.styleOptions.$model"
                  :key="idx"
                  :pressed.sync="btn.state"
                  variant="primary"
                >
                  {{ btn.caption }}
                </b-button>
              </b-button-group>
            </b-form-group>
            <b-form-group
              id="edit-text-formatting-group"
              label="Default Text Format"
              label-for="edit-text-format-input"
            >
              <b-form-select
                id="edit-text-format-input"
                v-model="$v.editStyleFormState.textFormat.$model"
              >
                <b-form-select-option value="default"> Default </b-form-select-option>
                <b-form-select-option value="upper"> Uppercase </b-form-select-option>
                <b-form-select-option value="lower"> Lowercase </b-form-select-option>
              </b-form-select>
            </b-form-group>
            <b-form-group
              id="edit-text-colour-input-group"
              label="Text Colour"
              label-for="edit-text-colour-input"
            >
              <b-form-input
                id="edit-text-colour-input"
                v-model="$v.editStyleFormState.textColour.$model"
                name="edit-text-colour-input"
                type="color"
                :state="validateEditStyleState('textColour')"
                aria-describedby="edit-colour-feedback"
              />
              <b-form-invalid-feedback id="edit-colour-feedback">
                This is a required field.
              </b-form-invalid-feedback>
            </b-form-group>
            <b-form-group
              id="edit-background-colour-enable-group"
              label="Background Colour"
              label-for="edit-background-colour-enable"
            >
              <b-form-checkbox
                id="edit-background-colour-enable"
                v-model="$v.editStyleFormState.enableBackgroundColour.$model"
                :switch="true"
              />
            </b-form-group>
            <b-form-group
              v-if="editStyleFormState.enableBackgroundColour"
              id="edit-background-colour-input-group"
            >
              <b-form-input
                id="edit-background-colour-picker"
                v-model="$v.editStyleFormState.backgroundColour.$model"
                name="edit-background-colour-picker"
                type="color"
                :state="validateEditStyleState('textColour')"
              />
            </b-form-group>
          </b-form>
        </div>
      </b-modal>
    </template>
    <template #cell(example)="data">
      <i class="example-stage-direction" :style="exampleCss(data.item)">
        <template v-if="data.item.text_format === 'upper'">
          {{ exampleText | uppercase }}
        </template>
        <template v-else-if="data.item.text_format === 'lower'">
          {{ exampleText | lowercase }}
        </template>
        <template v-else>
          {{ exampleText }}
        </template>
      </i>
    </template>
    <template #cell(btn)="data">
      <b-button-group v-if="IS_SCRIPT_EDITOR">
        <b-button
          variant="warning"
          :disabled="isSubmittingEdit || isDeleting"
          @click="openEditStyleForm(data)"
        >
          Edit
        </b-button>
        <b-button
          variant="danger"
          :disabled="isSubmittingEdit || isDeleting"
          @click="deleteStyle(data)"
        >
          Delete
        </b-button>
      </b-button-group>
    </template>
  </b-table>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapGetters, mapActions } from 'vuex';
import { required } from 'vuelidate/lib/validators';
import log from 'loglevel';
import paginationMixin from '@/mixins/paginationMixin';

export default defineComponent({
  name: 'StageDirectionConfigs',
  mixins: [paginationMixin],
  data() {
    return {
      tableKey: 'show_stage_direction_styles',
      exampleText: 'Your stage direction will look like this when formatted in the script!',
      columns: [
        'description',
        { key: 'example', label: 'Example Stage Direction' },
        { key: 'btn', label: '' },
      ],
      importColumns: [
        'description',
        { key: 'example', label: 'Example Stage Direction' },
        { key: 'btn', label: '' },
      ],
      newStyleFormState: {
        description: '',
        styleOptions: [
          { caption: 'Bold', state: false },
          { caption: 'Italic', state: false },
          { caption: 'Underline', state: false },
        ],
        textFormat: 'default',
        textColour: '#FFFFFF',
        enableBackgroundColour: false,
        backgroundColour: '#000000',
      },
      editStyleFormState: {
        id: null as number | null,
        description: '',
        styleOptions: [
          { caption: 'Bold', state: false },
          { caption: 'Italic', state: false },
          { caption: 'Underline', state: false },
        ],
        textFormat: 'default',
        textColour: '#FFFFFF',
        enableBackgroundColour: false,
        backgroundColour: '#000000',
      },
      isSubmittingNew: false,
      isSubmittingEdit: false,
      isDeleting: false,
      importStyleGroups: [] as any[],
      styleGroupExpanded: {} as Record<number, boolean>,
      isLoadingImport: false,
      isImporting: {} as Record<number, boolean>,
    };
  },
  computed: {
    ...mapGetters(['STAGE_DIRECTION_STYLES', 'IS_SCRIPT_EDITOR']),
    newFormExampleCss(): Record<string, string> {
      const style: Record<string, string> = {
        'font-weight': this.newStyleFormState.styleOptions.find((el) => el.caption === 'Bold')!
          .state
          ? 'bold'
          : 'normal',
        'font-style': this.newStyleFormState.styleOptions.find((el) => el.caption === 'Italic')!
          .state
          ? 'italic'
          : 'normal',
        'text-decoration-line': this.newStyleFormState.styleOptions.find(
          (el) => el.caption === 'Underline'
        )!.state
          ? 'underline'
          : 'none',
        color: this.newStyleFormState.textColour,
      };
      if (this.newStyleFormState.enableBackgroundColour) {
        style['background-color'] = this.newStyleFormState.backgroundColour;
      }
      return style;
    },
    editFormExampleCss(): Record<string, string> {
      const style: Record<string, string> = {
        'font-weight': this.editStyleFormState.styleOptions.find((el) => el.caption === 'Bold')!
          .state
          ? 'bold'
          : 'normal',
        'font-style': this.editStyleFormState.styleOptions.find((el) => el.caption === 'Italic')!
          .state
          ? 'italic'
          : 'normal',
        'text-decoration-line': this.editStyleFormState.styleOptions.find(
          (el) => el.caption === 'Underline'
        )!.state
          ? 'underline'
          : 'none',
        color: this.editStyleFormState.textColour,
      };
      if (this.editStyleFormState.enableBackgroundColour) {
        style['background-color'] = this.editStyleFormState.backgroundColour;
      }
      return style;
    },
    createPayload(): any {
      return {
        description: this.newStyleFormState.description,
        bold: this.newStyleFormState.styleOptions.find((el) => el.caption === 'Bold')!.state,
        italic: this.newStyleFormState.styleOptions.find((el) => el.caption === 'Italic')!.state,
        underline: this.newStyleFormState.styleOptions.find((el) => el.caption === 'Underline')!
          .state,
        textFormat: this.newStyleFormState.textFormat,
        textColour: this.newStyleFormState.textColour,
        enableBackgroundColour: this.newStyleFormState.enableBackgroundColour,
        backgroundColour: this.newStyleFormState.backgroundColour,
      };
    },
    editPayload(): any {
      return {
        id: this.editStyleFormState.id,
        description: this.editStyleFormState.description,
        bold: this.editStyleFormState.styleOptions.find((el) => el.caption === 'Bold')!.state,
        italic: this.editStyleFormState.styleOptions.find((el) => el.caption === 'Italic')!.state,
        underline: this.editStyleFormState.styleOptions.find((el) => el.caption === 'Underline')!
          .state,
        textFormat: this.editStyleFormState.textFormat,
        textColour: this.editStyleFormState.textColour,
        enableBackgroundColour: this.editStyleFormState.enableBackgroundColour,
        backgroundColour: this.editStyleFormState.backgroundColour,
      };
    },
  },
  async mounted(): Promise<void> {
    await (this as any).GET_STAGE_DIRECTION_STYLES();
  },
  validations: {
    newStyleFormState: {
      description: {
        required,
      },
      styleOptions: {
        required,
      },
      textFormat: {
        required,
      },
      textColour: {
        required,
      },
      enableBackgroundColour: {
        required,
      },
      backgroundColour: {
        required,
      },
    },
    editStyleFormState: {
      description: {
        required,
      },
      styleOptions: {
        required,
      },
      textFormat: {
        required,
      },
      textColour: {
        required,
      },
      enableBackgroundColour: {
        required,
      },
      backgroundColour: {
        required,
      },
    },
  },
  methods: {
    resetNewFormState(): void {
      this.newStyleFormState = {
        description: '',
        styleOptions: [
          { caption: 'Bold', state: false },
          { caption: 'Italic', state: false },
          { caption: 'Underline', state: false },
        ],
        textFormat: 'default',
        textColour: '#FFFFFF',
        enableBackgroundColour: false,
        backgroundColour: '#000000',
      };
      this.isSubmittingNew = false;
      this.$nextTick(() => {
        (this as any).$v.$reset();
      });
    },
    resetEditFormState(): void {
      this.editStyleFormState = {
        id: null,
        description: '',
        styleOptions: [
          { caption: 'Bold', state: false },
          { caption: 'Italic', state: false },
          { caption: 'Underline', state: false },
        ],
        textFormat: 'default',
        textColour: '#FFFFFF',
        enableBackgroundColour: false,
        backgroundColour: '#000000',
      };
      this.isSubmittingEdit = false;
      this.$nextTick(() => {
        (this as any).$v.$reset();
      });
    },
    validateNewStyleState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.newStyleFormState[name];
      return $dirty ? !$error : null;
    },
    validateEditStyleState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.editStyleFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitNewStyle(event: Event): Promise<void> {
      (this as any).$v.newStyleFormState.$touch();
      if ((this as any).$v.newStyleFormState.$anyError) {
        event.preventDefault();
        return;
      }

      if (this.isSubmittingNew) {
        event.preventDefault();
        return;
      }

      this.isSubmittingNew = true;

      try {
        await (this as any).ADD_STAGE_DIRECTION_STYLE(this.createPayload);
        (this as any).$refs['new-config-modal'].hide();
        this.resetNewFormState();
      } catch (error) {
        log.error('Error adding new stage direction style:', error);
        (this as any).$toast.error('Failed to add new style');
        event.preventDefault();
      } finally {
        this.isSubmittingNew = false;
      }
    },
    async onSubmitEditStyle(event: Event): Promise<void> {
      (this as any).$v.editStyleFormState.$touch();
      if ((this as any).$v.editStyleFormState.$anyError) {
        event.preventDefault();
        return;
      }

      if (this.isSubmittingEdit) {
        event.preventDefault();
        return;
      }

      this.isSubmittingEdit = true;

      try {
        await (this as any).UPDATE_STAGE_DIRECTION_STYLE(this.editPayload);
        (this as any).$refs['edit-config-modal'].hide();
        this.resetEditFormState();
      } catch (error) {
        log.error('Error updating stage direction style:', error);
        (this as any).$toast.error('Failed to update style');
        event.preventDefault();
      } finally {
        this.isSubmittingEdit = false;
      }
    },
    openEditStyleForm(style: any): void {
      if (style != null) {
        this.editStyleFormState.id = style.item.id;
        this.editStyleFormState.description = style.item.description;
        this.editStyleFormState.styleOptions = [
          { caption: 'Bold', state: style.item.bold },
          { caption: 'Italic', state: style.item.italic },
          { caption: 'Underline', state: style.item.underline },
        ];
        this.editStyleFormState.textFormat = style.item.text_format;
        this.editStyleFormState.textColour = style.item.text_colour;
        this.editStyleFormState.enableBackgroundColour = style.item.enable_background_colour;
        this.editStyleFormState.backgroundColour = style.item.background_colour;
        (this as any).$bvModal.show('edit-config-modal');
      }
    },
    async deleteStyle(style: any): Promise<void> {
      if (this.isDeleting) {
        return;
      }

      const msg = `Are you sure you want to delete ${style.item.description}?`;
      const action = await (this as any).$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.isDeleting = true;
        try {
          await (this as any).DELETE_STAGE_DIRECTION_STYLE(style.item.id);
        } catch (error) {
          log.error('Error deleting stage direction style:', error);
          (this as any).$toast.error('Failed to delete style');
        } finally {
          this.isDeleting = false;
        }
      }
    },
    exampleCss(data: any): Record<string, string> {
      const style: Record<string, string> = {
        'font-weight': data.bold ? 'bold' : 'normal',
        'font-style': data.italic ? 'italic' : 'normal',
        'text-decoration-line': data.underline ? 'underline' : 'none',
        color: data.text_colour,
      };
      if (data.enable_background_colour) {
        style['background-color'] = data.background_colour;
      }
      return style;
    },
    async openImportModal(): Promise<void> {
      (this as any).$bvModal.show('import-style-modal');
      this.isLoadingImport = true;
      try {
        const data = await (this as any).GET_IMPORTABLE_STAGE_DIRECTION_STYLES();
        this.importStyleGroups = data.style_groups;
        const expanded: Record<number, boolean> = {};
        data.style_groups.forEach((group: any) => {
          expanded[group.id] = true;
        });
        this.styleGroupExpanded = expanded;
      } catch (error) {
        log.error('Error fetching importable stage direction styles:', error);
        (this as any).$toast.error('Failed to load styles for import');
      } finally {
        this.isLoadingImport = false;
      }
    },
    resetImportState(): void {
      this.importStyleGroups = [];
      this.styleGroupExpanded = {};
      this.isLoadingImport = false;
      this.isImporting = {};
    },
    toggleImportShow(showId: number): void {
      this.$set(this.styleGroupExpanded, showId, !this.styleGroupExpanded[showId]);
    },
    async importStyle(style: any): Promise<void> {
      this.$set(this.isImporting, style.id, true);
      try {
        await (this as any).ADD_STAGE_DIRECTION_STYLE({
          description: style.description,
          bold: style.bold,
          italic: style.italic,
          underline: style.underline,
          textFormat: style.text_format,
          textColour: style.text_colour,
          enableBackgroundColour: style.enable_background_colour,
          backgroundColour: style.background_colour,
        });
        (this as any).$toast.success(`Imported "${style.description}"`);
      } catch (error) {
        log.error('Error importing stage direction style:', error);
        (this as any).$toast.error(`Failed to import "${style.description}"`);
      } finally {
        this.$set(this.isImporting, style.id, false);
      }
    },
    ...mapActions([
      'GET_STAGE_DIRECTION_STYLES',
      'ADD_STAGE_DIRECTION_STYLE',
      'DELETE_STAGE_DIRECTION_STYLE',
      'UPDATE_STAGE_DIRECTION_STYLE',
      'GET_IMPORTABLE_STAGE_DIRECTION_STYLES',
    ]),
  },
});
</script>
