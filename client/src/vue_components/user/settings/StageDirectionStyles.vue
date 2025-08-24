<template>
  <b-table
    v-if="CURRENT_SHOW != null"
    id="stage-directions-table"
    :items="tableData"
    :fields="columns"
    :per-page="rowsPerPage"
    :current-page="currentPage"
    show-empty
  >
    <template #head(btn)="data">
      <b-button
        v-b-modal.new-override-select
        variant="outline-success"
        :disabled="overrideChoices.length <= 1"
      >
        New Override
      </b-button>
      <b-modal
        id="new-override-select"
        ref="new-override-select"
        title="Add New Override"
        :ok-disabled="newStyleFormState.styleId == null || isSubmittingNew"
        @show="resetOverrideSelect"
        @ok="openNewOverrideModal"
      >
        <b-form>
          <b-form-select
            v-model="newStyleFormState.styleId"
            :options="overrideChoices"
          />
        </b-form>
      </b-modal>
      <b-modal
        id="new-override-modal"
        ref="new-override-modal"
        title="Add New Override"
        size="lg"
        :ok-disabled="isSubmittingNew"
        @hidden="resetNewFormState"
        @ok="onSubmitNewOverride"
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
            @ok="onSubmitNewOverride"
          >
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
        id="edit-override-modal"
        ref="edit-override-modal"
        title="Edit Override"
        size="lg"
        :ok-disabled="isSubmittingEdit"
        @hidden="resetEditFormState"
        @ok="onSubmitEditOverride"
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
            @ok="onSubmitEditOverride"
          >
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
    <template #cell(description)="data">
      {{ STAGE_DIRECTION_STYLES.find((elem) => elem.id === data.item.settings.id).description }}
    </template>
    <template #cell(example)="data">
      <i
        class="example-stage-direction"
        :style="exampleCss(data.item.settings)"
      >
        <template v-if="data.item.settings.text_format === 'upper'">
          {{ exampleText | uppercase }}
        </template>
        <template v-else-if="data.item.settings.text_format === 'lower'">
          {{ exampleText | lowercase }}
        </template>
        <template v-else>
          {{ exampleText }}
        </template>
      </i>
    </template>
    <template #cell(btn)="data">
      <b-button-group>
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
          @click="deleteStyleOverride(data)"
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
import log from 'loglevel';

export default {
  name: 'StageDirectionStyles',
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
        styleId: null,
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
    overrideChoices() {
      return [
        { value: null, text: 'Please select an option', disabled: true },
        ...this.STAGE_DIRECTION_STYLES.filter((item) => !this.STAGE_DIRECTION_STYLE_OVERRIDES.map(
          (elem) => elem.settings.id,
        ).includes(item.id), this).map((item) => ({ value: item.id, text: item.description })),
      ];
    },
    tableData() {
      return this.STAGE_DIRECTION_STYLE_OVERRIDES
        .filter((item) => this.STAGE_DIRECTION_STYLES
          .map((elem) => elem.id).includes(item.settings.id), this);
    },
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
        styleId: this.newStyleFormState.styleId,
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
        bold: this.editStyleFormState.styleOptions.find((el) => el.caption === 'Bold').state,
        italic: this.editStyleFormState.styleOptions.find((el) => el.caption === 'Italic').state,
        underline: this.editStyleFormState.styleOptions.find((el) => el.caption === 'Underline').state,
        text_format: this.editStyleFormState.textFormat,
        text_colour: this.editStyleFormState.textColour,
        enable_background_colour: this.editStyleFormState.enableBackgroundColour,
        background_colour: this.editStyleFormState.backgroundColour,
      };
    },
    ...mapGetters(['CURRENT_SHOW', 'STAGE_DIRECTION_STYLES', 'STAGE_DIRECTION_STYLE_OVERRIDES']),
  },
  async beforeMount() {
    await this.GET_SHOW_DETAILS();
    if (this.CURRENT_SHOW != null) {
      await this.GET_STAGE_DIRECTION_STYLES();
      await this.GET_STAGE_DIRECTION_STYLE_OVERRIDES();
    }
  },
  methods: {
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
    resetOverrideSelect() {
      this.newStyleFormState.styleId = null;
    },
    openNewOverrideModal(event) {
      const styleToOverride = this.STAGE_DIRECTION_STYLES
        .find((item) => item.id === this.newStyleFormState.styleId, this);
      if (styleToOverride == null) {
        log.error('Could not find style to override!');
        this.$toast.error('Could not find style to override!');
      } else {
        this.newStyleFormState.styleId = styleToOverride.id;
        this.newStyleFormState.styleOptions = [
          { caption: 'Bold', state: styleToOverride.bold },
          { caption: 'Italic', state: styleToOverride.italic },
          { caption: 'Underline', state: styleToOverride.underline },
        ];
        this.newStyleFormState.textFormat = styleToOverride.text_format;
        this.newStyleFormState.textColour = styleToOverride.text_colour;
        this.newStyleFormState.enableBackgroundColour = styleToOverride.enable_background_colour;
        this.newStyleFormState.backgroundColour = styleToOverride.background_colour;
        this.$bvModal.show('new-override-modal');
      }
    },
    resetNewFormState() {
      this.newStyleFormState = {
        styleId: null,
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
    async onSubmitNewOverride(event) {
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
        await this.ADD_STAGE_DIRECTION_STYLE_OVERRIDE(this.createPayload);
        this.$refs['new-override-modal'].hide();
        this.resetNewFormState();
      } catch (error) {
        log.error('Error adding new stage direction style override:', error);
        this.$toast.error('Failed to add new override');
        event.preventDefault();
      } finally {
        this.isSubmittingNew = false;
      }
    },
    async onSubmitEditOverride(event) {
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
        await this.UPDATE_STAGE_DIRECTION_STYLE_OVERRIDE(this.editPayload);
        this.$refs['edit-override-modal'].hide();
        this.resetEditFormState();
      } catch (error) {
        log.error('Error updating stage direction style override:', error);
        this.$toast.error('Failed to update override');
        event.preventDefault();
      } finally {
        this.isSubmittingEdit = false;
      }
    },
    validateNewStyleState(name) {
      const { $dirty, $error } = this.$v.newStyleFormState[name];
      return $dirty ? !$error : null;
    },
    validateEditStyleState(name) {
      const { $dirty, $error } = this.$v.editStyleFormState[name];
      return $dirty ? !$error : null;
    },
    async deleteStyleOverride(style) {
      if (this.isDeleting) {
        return;
      }

      const msg = 'Are you sure you want to delete this override?';
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.isDeleting = true;
        try {
          await this.DELETE_STAGE_DIRECTION_STYLE_OVERRIDE(style.item.id);
        } catch (error) {
          log.error('Error deleting stage direction style override:', error);
          this.$toast.error('Failed to delete override');
        } finally {
          this.isDeleting = false;
        }
      }
    },
    openEditStyleForm(style) {
      if (style != null) {
        const { settings } = style.item;
        this.editStyleFormState.id = style.item.id;
        this.editStyleFormState.styleOptions = [
          { caption: 'Bold', state: settings.bold },
          { caption: 'Italic', state: settings.italic },
          { caption: 'Underline', state: settings.underline },
        ];
        this.editStyleFormState.textFormat = settings.text_format;
        this.editStyleFormState.textColour = settings.text_colour;
        this.editStyleFormState.enableBackgroundColour = settings.enable_background_colour;
        this.editStyleFormState.backgroundColour = settings.background_colour;
        this.$bvModal.show('edit-override-modal');
      }
    },
    ...mapActions(['GET_SHOW_DETAILS', 'GET_STAGE_DIRECTION_STYLES',
      'GET_STAGE_DIRECTION_STYLE_OVERRIDES', 'ADD_STAGE_DIRECTION_STYLE_OVERRIDE',
      'DELETE_STAGE_DIRECTION_STYLE_OVERRIDE', 'UPDATE_STAGE_DIRECTION_STYLE_OVERRIDE']),
  },
  validations: {
    newStyleFormState: {
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
};
</script>
