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
      <b-button
        v-if="IS_SCRIPT_EDITOR"
        v-b-modal.new-config-modal
        variant="outline-success"
      >
        New Style
      </b-button>
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
          <i
            class="example-stage-direction"
            :style="newFormExampleCss"
          >
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
          <b-form
            ref="new-config-form"
            @ok="onSubmitNewStyle"
          >
            <b-form-group
              id="description-input-group"
              label="Description"
              label-for="description-input"
            >
              <b-form-input
                id="description-input"
                v-model="$v.newStyleFormState.description.$model"
                name="description-input"
                :state="validateNewStyleState('description')"
                aria-describedby="description-feedback"
              />
              <b-form-invalid-feedback
                id="description-feedback"
              >
                This is a required field.
              </b-form-invalid-feedback>
            </b-form-group>
            <b-form-group
              id="styling-group"
              label="Default Styles"
              label-for="styling-input"
            >
              <b-button-group id="styling-input">
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
              id="text-formatting-group"
              label="Default Text Format"
              label-for="text-format-input"
            >
              <b-form-select
                id="text-format-input"
                v-model="$v.newStyleFormState.textFormat.$model"
              >
                <b-form-select-option
                  value="default"
                >
                  Default
                </b-form-select-option>
                <b-form-select-option
                  value="upper"
                >
                  Uppercase
                </b-form-select-option>
                <b-form-select-option
                  value="lower"
                >
                  Lowercase
                </b-form-select-option>
              </b-form-select>
            </b-form-group>
            <b-form-group
              id="text-colour-input-group"
              label="Text Colour"
              label-for="text-colour-input"
            >
              <b-form-input
                id="text-colour-input"
                v-model="$v.newStyleFormState.textColour.$model"
                name="text-colour-input"
                type="color"
                :state="validateNewStyleState('textColour')"
                aria-describedby="colour-feedback"
              />
              <b-form-invalid-feedback
                id="colour-feedback"
              >
                This is a required field.
              </b-form-invalid-feedback>
            </b-form-group>
            <b-form-group
              id="background-colour-enable-group"
              label="Background Colour"
              label-for="background-colour-enable"
            >
              <b-form-checkbox
                id="background-colour-enable"
                v-model="$v.newStyleFormState.enableBackgroundColour.$model"
                :switch="true"
              />
            </b-form-group>
            <b-form-group
              v-if="newStyleFormState.enableBackgroundColour"
              id="background-colour-input-group"
            >
              <b-form-input
                id="background-colour-picker"
                v-model="$v.newStyleFormState.backgroundColour.$model"
                name="background-colour-picker"
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
          <i
            class="example-stage-direction"
            :style="editFormExampleCss"
          >
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
          <b-form
            ref="edit-config-form"
            @ok="onSubmitEditStyle"
          >
            <b-form-group
              id="description-input-group"
              label="Description"
              label-for="description-input"
            >
              <b-form-input
                id="description-input"
                v-model="$v.editStyleFormState.description.$model"
                name="description-input"
                :state="validateEditStyleState('description')"
                aria-describedby="description-feedback"
              />
              <b-form-invalid-feedback
                id="description-feedback"
              >
                This is a required field.
              </b-form-invalid-feedback>
            </b-form-group>
            <b-form-group
              id="styling-group"
              label="Default Styles"
              label-for="styling-input"
            >
              <b-button-group id="styling-input">
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
              id="text-formatting-group"
              label="Default Text Format"
              label-for="text-format-input"
            >
              <b-form-select
                id="text-format-input"
                v-model="$v.editStyleFormState.textFormat.$model"
              >
                <b-form-select-option
                  value="default"
                >
                  Default
                </b-form-select-option>
                <b-form-select-option
                  value="upper"
                >
                  Uppercase
                </b-form-select-option>
                <b-form-select-option
                  value="lower"
                >
                  Lowercase
                </b-form-select-option>
              </b-form-select>
            </b-form-group>
            <b-form-group
              id="text-colour-input-group"
              label="Text Colour"
              label-for="text-colour-input"
            >
              <b-form-input
                id="text-colour-input"
                v-model="$v.editStyleFormState.textColour.$model"
                name="text-colour-input"
                type="color"
                :state="validateEditStyleState('textColour')"
                aria-describedby="colour-feedback"
              />
              <b-form-invalid-feedback
                id="colour-feedback"
              >
                This is a required field.
              </b-form-invalid-feedback>
            </b-form-group>
            <b-form-group
              id="background-colour-enable-group"
              label="Background Colour"
              label-for="background-colour-enable"
            >
              <b-form-checkbox
                id="background-colour-enable"
                v-model="$v.editStyleFormState.enableBackgroundColour.$model"
                :switch="true"
              />
            </b-form-group>
            <b-form-group
              v-if="editStyleFormState.enableBackgroundColour"
              id="background-colour-input-group"
            >
              <b-form-input
                id="background-colour-picker"
                v-model="$v.editStyleFormState.backgroundColour.$model"
                name="background-colour-picker"
                type="color"
                :state="validateEditStyleState('textColour')"
              />
            </b-form-group>
          </b-form>
        </div>
      </b-modal>
    </template>
    <template #cell(example)="data">
      <i
        class="example-stage-direction"
        :style="exampleCss(data.item)"
      >
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

<script>
import { mapGetters, mapActions } from 'vuex';
import { required } from 'vuelidate/lib/validators';
import log from 'loglevel';

export default {
  name: 'StageDirectionConfigs',
  data() {
    return {
      exampleText: 'Your stage direction will look like this when formatted in the script!',
      columns: [
        'description',
        { key: 'example', label: 'Example Stage Direction' },
        { key: 'btn', label: '' },
      ],
      rowsPerPage: 15,
      currentPage: 1,
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
      },
      isSubmittingNew: false,
      isSubmittingEdit: false,
      isDeleting: false,
    };
  },
  computed: {
    ...mapGetters(['STAGE_DIRECTION_STYLES', 'IS_SCRIPT_EDITOR']),
    newFormExampleCss() {
      const style = {
        'font-weight': this.newStyleFormState.styleOptions.find((el) => el.caption === 'Bold').state ? 'bold' : 'normal',
        'font-style': this.newStyleFormState.styleOptions.find((el) => el.caption === 'Italic').state ? 'italic' : 'normal',
        'text-decoration-line': this.newStyleFormState.styleOptions.find((el) => el.caption === 'Underline').state ? 'underline' : 'none',
        color: this.newStyleFormState.textColour,
      };
      if (this.newStyleFormState.enableBackgroundColour) {
        style['background-color'] = this.newStyleFormState.backgroundColour;
      }
      return style;
    },
    editFormExampleCss() {
      const style = {
        'font-weight': this.editStyleFormState.styleOptions.find((el) => el.caption === 'Bold').state ? 'bold' : 'normal',
        'font-style': this.editStyleFormState.styleOptions.find((el) => el.caption === 'Italic').state ? 'italic' : 'normal',
        'text-decoration-line': this.editStyleFormState.styleOptions.find((el) => el.caption === 'Underline').state ? 'underline' : 'none',
        color: this.editStyleFormState.textColour,
      };
      if (this.editStyleFormState.enableBackgroundColour) {
        style['background-color'] = this.editStyleFormState.backgroundColour;
      }
      return style;
    },
    createPayload() {
      return {
        description: this.newStyleFormState.description,
        bold: this.newStyleFormState.styleOptions.find((el) => el.caption === 'Bold').state,
        italic: this.newStyleFormState.styleOptions.find((el) => el.caption === 'Italic').state,
        underline: this.newStyleFormState.styleOptions.find((el) => el.caption === 'Underline').state,
        textFormat: this.newStyleFormState.textFormat,
        textColour: this.newStyleFormState.textColour,
        enableBackgroundColour: this.newStyleFormState.enableBackgroundColour,
        backgroundColour: this.newStyleFormState.backgroundColour,
      };
    },
    editPayload() {
      return {
        id: this.editStyleFormState.id,
        description: this.editStyleFormState.description,
        bold: this.editStyleFormState.styleOptions.find((el) => el.caption === 'Bold').state,
        italic: this.editStyleFormState.styleOptions.find((el) => el.caption === 'Italic').state,
        underline: this.editStyleFormState.styleOptions.find((el) => el.caption === 'Underline').state,
        textFormat: this.editStyleFormState.textFormat,
        textColour: this.editStyleFormState.textColour,
        enableBackgroundColour: this.editStyleFormState.enableBackgroundColour,
        backgroundColour: this.editStyleFormState.backgroundColour,
      };
    },
  },
  async mounted() {
    await this.GET_STAGE_DIRECTION_STYLES();
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
    resetNewFormState() {
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
        this.$v.$reset();
      });
    },
    resetEditFormState() {
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
        this.$v.$reset();
      });
    },
    validateNewStyleState(name) {
      const { $dirty, $error } = this.$v.newStyleFormState[name];
      return $dirty ? !$error : null;
    },
    validateEditStyleState(name) {
      const { $dirty, $error } = this.$v.editStyleFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitNewStyle(event) {
      this.$v.newStyleFormState.$touch();
      if (this.$v.newStyleFormState.$anyError) {
        event.preventDefault();
        return;
      }

      if (this.isSubmittingNew) {
        event.preventDefault();
        return;
      }

      this.isSubmittingNew = true;

      try {
        await this.ADD_STAGE_DIRECTION_STYLE(this.createPayload);
        this.$refs['new-config-modal'].hide();
        this.resetNewFormState();
      } catch (error) {
        log.error('Error adding new stage direction style:', error);
        this.$toast.error('Failed to add new style');
        event.preventDefault();
      } finally {
        this.isSubmittingNew = false;
      }
    },
    async onSubmitEditStyle(event) {
      this.$v.editStyleFormState.$touch();
      if (this.$v.editStyleFormState.$anyError) {
        event.preventDefault();
        return;
      }

      if (this.isSubmittingEdit) {
        event.preventDefault();
        return;
      }

      this.isSubmittingEdit = true;

      try {
        await this.UPDATE_STAGE_DIRECTION_STYLE(this.editPayload);
        this.$refs['edit-config-modal'].hide();
        this.resetEditFormState();
      } catch (error) {
        log.error('Error updating stage direction style:', error);
        this.$toast.error('Failed to update style');
        event.preventDefault();
      } finally {
        this.isSubmittingEdit = false;
      }
    },
    openEditStyleForm(style) {
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
        this.$bvModal.show('edit-config-modal');
      }
    },
    async deleteStyle(style) {
      if (this.isDeleting) {
        return;
      }

      const msg = `Are you sure you want to delete ${style.item.description}?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.isDeleting = true;
        try {
          await this.DELETE_STAGE_DIRECTION_STYLE(style.item.id);
        } catch (error) {
          log.error('Error deleting stage direction style:', error);
          this.$toast.error('Failed to delete style');
        } finally {
          this.isDeleting = false;
        }
      }
    },
    exampleCss(data) {
      const style = {
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
    ...mapActions(['GET_STAGE_DIRECTION_STYLES', 'ADD_STAGE_DIRECTION_STYLE', 'DELETE_STAGE_DIRECTION_STYLE', 'UPDATE_STAGE_DIRECTION_STYLE']),
  },
};
</script>
