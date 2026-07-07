<template>
  <div>
    <!-- Default stage direction style section -->
    <b-card class="mb-3">
      <template #header>
        <strong>Default Stage Direction Style</strong>
      </template>
      <p class="text-muted small mb-2">
        Applied to stage direction lines that have no specific style assigned.
      </p>
      <div class="d-flex align-items-center flex-wrap" style="gap: 0.75rem">
        <i class="example-stage-direction" :style="defaultExampleCss">
          {{ exampleText }}
        </i>
        <b-button variant="outline-primary" @click="openDefaultModal">Customise</b-button>
        <b-button
          v-if="hasDefaultOverride"
          variant="outline-secondary"
          :disabled="isSubmittingDefault"
          @click="resetDefaultStyle"
        >
          Reset to Default
        </b-button>
      </div>
    </b-card>

    <b-modal
      id="default-sd-style-modal"
      ref="default-sd-style-modal"
      title="Customise Default Stage Direction Style"
      size="lg"
      :ok-disabled="isSubmittingDefault"
      @ok="onSubmitDefaultStyle"
    >
      <div class="mb-3">
        <h4>Preview</h4>
        <i class="example-stage-direction" :style="defaultFormExampleCss">
          {{ exampleText }}
        </i>
      </div>
      <b-form-group label="Background Colour" label-for="default-bg-colour-input">
        <b-form-input
          id="default-bg-colour-input"
          v-model="defaultFormState.backgroundColour"
          type="color"
        />
      </b-form-group>
      <b-form-group label="Text Colour">
        <b-form-checkbox v-model="defaultFormState.enableTextColour" :switch="true" class="mb-1">
          Override text colour
        </b-form-checkbox>
        <b-form-input
          v-if="defaultFormState.enableTextColour"
          id="default-text-colour-input"
          v-model="defaultFormState.textColour"
          type="color"
        />
      </b-form-group>
    </b-modal>

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
            <b-form-select v-model="newStyleFormState.styleId" :options="overrideChoices" />
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
            <b-form ref="new-config-form" @ok="onSubmitNewOverride">
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
            <b-form ref="edit-config-form" @ok="onSubmitEditOverride">
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
      <template #cell(description)="data">
        {{ STAGE_DIRECTION_STYLES.find((elem) => elem.id === data.item.settings.id).description }}
      </template>
      <template #cell(example)="data">
        <i class="example-stage-direction" :style="exampleCss(data.item.settings)">
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
    <b-alert v-else variant="danger"> No show loaded. </b-alert>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapGetters, mapActions } from 'vuex';
import { required } from 'vuelidate/lib/validators';
import log from 'loglevel';
import { makeURL } from '@/js/utils';
import paginationMixin from '@/mixins/paginationMixin';

interface StyleOption {
  caption: string;
  state: boolean;
}

interface StyleFormState {
  styleId: number | null;
  styleOptions: StyleOption[];
  textFormat: string;
  textColour: string;
  enableBackgroundColour: boolean;
  backgroundColour: string;
}

interface EditStyleFormState {
  id: number | null;
  styleOptions: StyleOption[];
  textFormat: string;
  textColour: string;
  enableBackgroundColour: boolean;
  backgroundColour: string;
}

export default defineComponent({
  name: 'StageDirectionStyles',
  mixins: [paginationMixin],
  data() {
    return {
      tableKey: 'user_stage_direction_styles',
      exampleText: 'Your stage direction will look like this when formatted in the script!',
      columns: [
        'description',
        { key: 'example', label: 'Example Stage Direction' },
        { key: 'btn', label: '' },
      ],
      newStyleFormState: {
        styleId: null as number | null,
        styleOptions: [
          { caption: 'Bold', state: false },
          { caption: 'Italic', state: false },
          { caption: 'Underline', state: false },
        ] as StyleOption[],
        textFormat: 'default',
        textColour: '#FFFFFF',
        enableBackgroundColour: false,
        backgroundColour: '#000000',
      } as StyleFormState,
      editStyleFormState: {
        id: null as number | null,
        styleOptions: [
          { caption: 'Bold', state: false },
          { caption: 'Italic', state: false },
          { caption: 'Underline', state: false },
        ] as StyleOption[],
        textFormat: 'default',
        textColour: '#FFFFFF',
        enableBackgroundColour: false,
        backgroundColour: '#000000',
      } as EditStyleFormState,
      isSubmittingNew: false,
      isSubmittingEdit: false,
      isSubmittingDefault: false,
      isDeleting: false,
      defaultFormState: {
        backgroundColour: '#2f4f4f',
        enableTextColour: false,
        textColour: '#FFFFFF',
      },
    };
  },
  computed: {
    overrideChoices(): unknown[] {
      return [
        { value: null, text: 'Please select an option', disabled: true },
        ...(this as any).STAGE_DIRECTION_STYLES.filter(
          (item: any) =>
            !(this as any).STAGE_DIRECTION_STYLE_OVERRIDES.map(
              (elem: any) => elem.settings.id
            ).includes(item.id)
        ).map((item: any) => ({ value: item.id, text: item.description })),
      ];
    },
    tableData(): unknown[] {
      return (this as any).STAGE_DIRECTION_STYLE_OVERRIDES.filter((item: any) =>
        (this as any).STAGE_DIRECTION_STYLES.map((elem: any) => elem.id).includes(item.settings.id)
      );
    },
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
    createPayload(): Record<string, unknown> {
      return {
        styleId: this.newStyleFormState.styleId,
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
    editPayload(): Record<string, unknown> {
      return {
        id: this.editStyleFormState.id,
        bold: this.editStyleFormState.styleOptions.find((el) => el.caption === 'Bold')!.state,
        italic: this.editStyleFormState.styleOptions.find((el) => el.caption === 'Italic')!.state,
        underline: this.editStyleFormState.styleOptions.find((el) => el.caption === 'Underline')!
          .state,
        text_format: this.editStyleFormState.textFormat,
        text_colour: this.editStyleFormState.textColour,
        enable_background_colour: this.editStyleFormState.enableBackgroundColour,
        background_colour: this.editStyleFormState.backgroundColour,
      };
    },
    hasDefaultOverride(): boolean {
      const s = (this as any).USER_SETTINGS ?? {};
      return s.default_sd_background_colour != null || s.default_sd_text_colour != null;
    },
    defaultExampleCss(): Record<string, string> {
      const s = (this as any).USER_SETTINGS ?? {};
      const result: Record<string, string> = {
        'background-color': s.default_sd_background_colour ?? 'darkslateblue',
        'font-style': 'italic',
      };
      if (s.default_sd_text_colour) result['color'] = s.default_sd_text_colour;
      return result;
    },
    defaultFormExampleCss(): Record<string, string> {
      const result: Record<string, string> = {
        'background-color': this.defaultFormState.backgroundColour,
        'font-style': 'italic',
      };
      if (this.defaultFormState.enableTextColour) {
        result['color'] = this.defaultFormState.textColour;
      }
      return result;
    },
    ...mapGetters([
      'CURRENT_SHOW',
      'STAGE_DIRECTION_STYLES',
      'STAGE_DIRECTION_STYLE_OVERRIDES',
      'USER_SETTINGS',
    ]),
  },
  async beforeMount(): Promise<void> {
    await (this as any).GET_SHOW_DETAILS();
    if ((this as any).CURRENT_SHOW != null) {
      await (this as any).GET_STAGE_DIRECTION_STYLES();
      await (this as any).GET_STAGE_DIRECTION_STYLE_OVERRIDES();
    }
  },
  methods: {
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
    resetOverrideSelect(): void {
      this.newStyleFormState.styleId = null;
    },
    openNewOverrideModal(event: Event): void {
      const styleToOverride = (this as any).STAGE_DIRECTION_STYLES.find(
        (item: any) => item.id === this.newStyleFormState.styleId
      );
      if (styleToOverride == null) {
        log.error('Could not find style to override!');
        (this as any).$toast.error('Could not find style to override!');
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
        (this as any).$bvModal.show('new-override-modal');
      }
    },
    resetNewFormState(): void {
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
        (this as any).$v.$reset();
      });
    },
    resetEditFormState(): void {
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
        (this as any).$v.$reset();
      });
    },
    async onSubmitNewOverride(event: Event): Promise<void> {
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
        await (this as any).ADD_STAGE_DIRECTION_STYLE_OVERRIDE(this.createPayload);
        (this.$refs['new-override-modal'] as any).hide();
        this.resetNewFormState();
      } catch (error) {
        log.error('Error adding new stage direction style override:', error);
        (this as any).$toast.error('Failed to add new override');
        event.preventDefault();
      } finally {
        this.isSubmittingNew = false;
      }
    },
    async onSubmitEditOverride(event: Event): Promise<void> {
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
        await (this as any).UPDATE_STAGE_DIRECTION_STYLE_OVERRIDE(this.editPayload);
        (this.$refs['edit-override-modal'] as any).hide();
        this.resetEditFormState();
      } catch (error) {
        log.error('Error updating stage direction style override:', error);
        (this as any).$toast.error('Failed to update override');
        event.preventDefault();
      } finally {
        this.isSubmittingEdit = false;
      }
    },
    validateNewStyleState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.newStyleFormState[name];
      return $dirty ? !$error : null;
    },
    validateEditStyleState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.editStyleFormState[name];
      return $dirty ? !$error : null;
    },
    async deleteStyleOverride(style: any): Promise<void> {
      if (this.isDeleting) {
        return;
      }

      const msg = 'Are you sure you want to delete this override?';
      const action = await (this as any).$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.isDeleting = true;
        try {
          await (this as any).DELETE_STAGE_DIRECTION_STYLE_OVERRIDE(style.item.id);
        } catch (error) {
          log.error('Error deleting stage direction style override:', error);
          (this as any).$toast.error('Failed to delete override');
        } finally {
          this.isDeleting = false;
        }
      }
    },
    openEditStyleForm(style: any): void {
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
        (this as any).$bvModal.show('edit-override-modal');
      }
    },
    openDefaultModal(): void {
      const s = (this as any).USER_SETTINGS ?? {};
      this.defaultFormState.backgroundColour = s.default_sd_background_colour ?? '#2f4f4f';
      this.defaultFormState.enableTextColour = s.default_sd_text_colour != null;
      this.defaultFormState.textColour = s.default_sd_text_colour ?? '#FFFFFF';
      (this as any).$bvModal.show('default-sd-style-modal');
    },
    async onSubmitDefaultStyle(event: Event): Promise<void> {
      if (this.isSubmittingDefault) {
        event.preventDefault();
        return;
      }
      this.isSubmittingDefault = true;
      try {
        await fetch(makeURL('/api/v1/user/settings'), {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            default_sd_background_colour: this.defaultFormState.backgroundColour,
            default_sd_text_colour: this.defaultFormState.enableTextColour
              ? this.defaultFormState.textColour
              : null,
          }),
        });
      } catch (error) {
        log.error('Error updating default stage direction style:', error);
        (this as any).$toast.error('Failed to update default stage direction style');
        event.preventDefault();
      } finally {
        this.isSubmittingDefault = false;
      }
    },
    async resetDefaultStyle(): Promise<void> {
      if (this.isSubmittingDefault) return;
      this.isSubmittingDefault = true;
      try {
        await fetch(makeURL('/api/v1/user/settings'), {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            default_sd_background_colour: null,
            default_sd_text_colour: null,
          }),
        });
      } catch (error) {
        log.error('Error resetting default stage direction style:', error);
        (this as any).$toast.error('Failed to reset default stage direction style');
      } finally {
        this.isSubmittingDefault = false;
      }
    },
    ...mapActions([
      'GET_SHOW_DETAILS',
      'GET_STAGE_DIRECTION_STYLES',
      'GET_STAGE_DIRECTION_STYLE_OVERRIDES',
      'ADD_STAGE_DIRECTION_STYLE_OVERRIDE',
      'DELETE_STAGE_DIRECTION_STYLE_OVERRIDE',
      'UPDATE_STAGE_DIRECTION_STYLE_OVERRIDE',
    ]),
  },
  validations: {
    newStyleFormState: {
      styleOptions: { required },
      textFormat: { required },
      textColour: { required },
      enableBackgroundColour: { required },
      backgroundColour: { required },
    },
    editStyleFormState: {
      styleOptions: { required },
      textFormat: { required },
      textColour: { required },
      enableBackgroundColour: { required },
      backgroundColour: { required },
    },
  },
});
</script>
