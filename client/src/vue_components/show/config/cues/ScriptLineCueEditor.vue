<template>
  <b-container
    ref="lineContainer"
    class="mx-0"
    style="margin: 0; padding: 0 0 .2rem;"
    fluid
  >
    <b-row v-if="needsActSceneLabel">
      <b-col cols="3" />
      <b-col cols="9">
        <h4> {{ actLabel }} - {{ sceneLabel }}</h4>
      </b-col>
    </b-row>
    <b-row :class="{'stage-direction': line.line_type === 2}">
      <b-col
        cols="3"
        class="cue-column"
        style="text-align: right"
      >
        <b-button-group v-if="line.line_type !== 4">
          <b-button
            v-for="cue in cues"
            :key="cue.id"
            :disabled="!IS_CUE_EDITOR"
            class="cue-button"
            :style="{backgroundColor: cueBackgroundColour(cue),
                     color: contrastColor({'bgColor': cueBackgroundColour(cue)})}"
            @click.stop="openEditForm(cue)"
          >
            {{ cueLabel(cue) }}
          </b-button>
          <b-button
            v-if="IS_CUE_EDITOR"
            class="cue-button"
            :disabled="isWholeLineCut(line)"
            @click.stop="openNewForm"
          >
            <b-icon-plus-square-fill variant="success" />
          </b-button>
        </b-button-group>
      </b-col>
      <template v-if="line.line_type === 1">
        <b-col
          v-for="(part, index) in line.line_parts"
          :key="`line_${lineIndex}_part_${index}`"
          style="text-align: center"
        >
          <template v-if="needsHeadings[index]">
            <b v-if="part.character_id != null">
              {{ characters.find((char) => (char.id === part.character_id)).name }}
            </b>
            <b v-else>
              {{ characterGroups.find((char) => (char.id === part.character_group_id)).name }}
            </b>
          </template>
          <b v-else-if="needsHeadingsAny">&nbsp;</b>
          <p
            class="viewable-line"
            :class="{'cut-line-part': linePartCuts.indexOf(part.id) !== -1}"
          >
            {{ part.line_text }}
          </p>
        </b-col>
      </template>
      <template v-else-if="line.line_type === 2">
        <b-col
          :key="`line_${lineIndex}_stage_direction`"
          style="text-align: center"
        >
          <i
            class="viewable-line"
            :class="{'cut-line-part': linePartCuts.indexOf(line.line_parts[0].id) !== -1}"
            :style="stageDirectionStyling"
          >
            <template
              v-if="stageDirectionStyle != null && stageDirectionStyle.text_format === 'upper'"
            >
              {{ line.line_parts[0].line_text | uppercase }}
            </template>
            <template
              v-else-if="stageDirectionStyle != null && stageDirectionStyle.text_format === 'lower'"
            >
              {{ line.line_parts[0].line_text | lowercase }}
            </template>
            <template v-else>
              {{ line.line_parts[0].line_text }}
            </template>
          </i>
        </b-col>
      </template>
      <template v-else-if="line.line_type === 3">
        <b-col
          :key="`line_${lineIndex}_cue_line`"
          style="text-align: center"
        >
          <b-alert
            variant="secondary"
            show
          >
            <p
              class="text-muted small"
              style="margin: 0"
            >
              Cue Line
            </p>
          </b-alert>
        </b-col>
      </template>
      <template v-else-if="line.line_type === 4">
        <b-col
          :key="`line_${lineIndex}_spacing`"
          style="text-align: center"
        >
          <b-alert
            variant="secondary"
            show
          >
            <p
              class="text-muted small"
              style="margin: 0"
            >
              Spacing Line
            </p>
          </b-alert>
        </b-col>
      </template>
    </b-row>
    <b-modal
      :id="`line_${lineIndex}_-new-cue`"
      title="Add New Cue"
      size="md"
      :ok-disabled="$v.newFormState.$invalid || submittingNewCue"
      @hidden="resetNewForm"
      @ok="onSubmitNew"
    >
      <b-form
        ref="new-cue-form"
        @submit.stop.prevent="onSubmitNew"
      >
        <b-form-group
          id="type-input-group"
          label="Cue Type"
          label-for="type-input"
        >
          <b-form-select
            id="act-input"
            v-model="$v.newFormState.cueType.$model"
            :options="cueTypeOptions"
            :state="validateNewState('cueType')"
            aria-describedby="cue-type-feedback"
          />
          <b-form-invalid-feedback
            id="cue-type-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="ident-input-group"
          label="Identifier"
          label-for="ident-input"
        >
          <b-form-input
            id="ident-input"
            v-model="$v.newFormState.ident.$model"
            name="ident-input"
            :state="validateNewState('ident')"
            aria-describedby="ident-feedback"
          />
          <b-form-invalid-feedback
            id="ident-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group>
          <b-form-text
            v-if="isDuplicateNewCue"
            class="text-warning"
          >
            ⚠️ A cue with this identifier already exists for this cue type
          </b-form-text>
        </b-form-group>
        <template v-if="line.line_type === 1 || line.line_type === 2">
          <hr>
          <b-form-group
            id="line-render-group"
            label="Script Line"
            label-for="line-render"
          >
            <b-form-text id="line-render">
              <b-row>
                <template v-if="line.line_type === 2">
                  <b-col
                    :key="`line_${lineIndex}_stage_direction`"
                    style="text-align: center"
                  >
                    <i
                      class="viewable-line"
                      :class="{'cut-line-part': linePartCuts.indexOf(line.line_parts[0].id) !== -1}"
                      :style="stageDirectionStyling"
                    >
                      <template
                        v-if="stageDirectionStyle != null && stageDirectionStyle.text_format === 'upper'"
                      >
                        {{ line.line_parts[0].line_text | uppercase }}
                      </template>
                      <template
                        v-else-if="stageDirectionStyle != null && stageDirectionStyle.text_format === 'lower'"
                      >
                        {{ line.line_parts[0].line_text | lowercase }}
                      </template>
                      <template v-else>
                        {{ line.line_parts[0].line_text }}
                      </template>
                    </i>
                  </b-col>
                </template>
                <template v-else>
                  <b-col
                    v-for="(part, index) in line.line_parts"
                    :key="`line_${lineIndex}_part_${index}`"
                    style="text-align: center"
                  >
                    <b v-if="part.character_id != null">
                      {{ characters.find((char) => (char.id === part.character_id)).name }}
                    </b>
                    <b v-else>
                      {{ characterGroups.find((char) => (char.id === part.character_group_id)).name }}
                    </b>

                    <p
                      class="viewable-line"
                      :class="{'cut-line-part': linePartCuts.indexOf(part.id) !== -1}"
                    >
                      {{ part.line_text }}
                    </p>
                  </b-col>
                </template>
              </b-row>
            </b-form-text>
          </b-form-group>
        </template>
      </b-form>
    </b-modal>
    <b-modal
      :id="`line_${lineIndex}_-edit-cue`"
      title="Edit Cue"
      size="md"
      :ok-disabled="$v.editFormState.$invalid || submittingEditCue"
      @hidden="resetEditForm"
      @ok="onSubmitEdit"
    >
      <b-form
        ref="edit-cue-form"
        @submit.stop.prevent="onSubmitEdit"
      >
        <b-form-group
          id="type-input-group"
          label="Cue Type"
          label-for="type-input"
        >
          <b-form-select
            id="act-input"
            v-model="$v.editFormState.cueType.$model"
            :options="cueTypeOptions"
            :state="validateEditState('cueType')"
            aria-describedby="cue-type-feedback"
          />
          <b-form-invalid-feedback
            id="cue-type-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group
          id="ident-input-group"
          label="Identifier"
          label-for="ident-input"
        >
          <b-form-input
            id="ident-input"
            v-model="$v.editFormState.ident.$model"
            name="ident-input"
            :state="validateEditState('ident')"
            aria-describedby="ident-feedback"
          />
          <b-form-invalid-feedback
            id="ident-feedback"
          >
            This is a required field.
          </b-form-invalid-feedback>
          <b-form-text
            v-if="isDuplicateEditCue"
            class="text-warning"
          >
            ⚠️ A cue with this identifier already exists for this cue type
          </b-form-text>
        </b-form-group>
      </b-form>
      <template #modal-footer="{ ok, cancel }">
        <b-button
          variant="secondary"
          :disabled="submittingEditCue || deletingCue"
          @click="cancel()"
        >
          Cancel
        </b-button>
        <b-button
          variant="danger"
          :disabled="submittingEditCue || deletingCue"
          @click.stop="deleteCue"
        >
          Delete
        </b-button>
        <b-button
          variant="primary"
          :disabled="$v.editFormState.$invalid || submittingEditCue || deletingCue"
          @click="ok()"
        >
          Save
        </b-button>
      </template>
    </b-modal>
  </b-container>
</template>

<script>
import { required } from 'vuelidate/lib/validators';
import { mapActions, mapGetters } from 'vuex';
import { contrastColor } from 'contrast-color';
import log from 'loglevel';

export default {
  name: 'ScriptLineCueEditor',
  props: {
    line: {
      required: true,
      type: Object,
    },
    lineIndex: {
      required: true,
      type: Number,
    },
    previousLine: {
      required: true,
      type: Object,
    },
    acts: {
      required: true,
      type: Array,
    },
    scenes: {
      required: true,
      type: Array,
    },
    characters: {
      required: true,
      type: Array,
    },
    characterGroups: {
      required: true,
      type: Array,
    },
    cues: {
      required: true,
      type: Array,
    },
    cueTypes: {
      required: true,
      type: Array,
    },
    linePartCuts: {
      required: true,
      type: Array,
    },
    stageDirectionStyles: {
      required: true,
      type: Array,
    },
    stageDirectionStyleOverrides: {
      required: true,
      type: Array,
    },
  },
  data() {
    return {
      newFormState: {
        cueType: null,
        ident: null,
        lineId: null,
      },
      editFormState: {
        cueId: null,
        cueType: null,
        ident: null,
        lineId: null,
      },
      submittingNewCue: false,
      submittingEditCue: false,
      deletingCue: false,
    };
  },
  validations: {
    newFormState: {
      cueType: {
        required,
      },
      ident: {
        required,
      },
      lineId: {
        required,
      },
    },
    editFormState: {
      cueId: {
        required,
      },
      cueType: {
        required,
      },
      ident: {
        required,
      },
      lineId: {
        required,
      },
    },
  },
  computed: {
    ...mapGetters(['IS_CUE_EDITOR', 'RBAC_ROLES', 'CURRENT_USER_RBAC', 'IS_ADMIN_USER', 'SCRIPT_CUES', 'CUE_COLOUR_OVERRIDES']),
    cueTypeOptions() {
      if (this.IS_ADMIN_USER) {
        return [
          { value: null, text: 'N/A' },
          ...this.cueTypes.map((cueType) => ({ value: cueType.id, text: `${cueType.prefix}: ${cueType.description}` })),
        ];
      }
      const writeMask = this.RBAC_ROLES.find((x) => x.key === 'WRITE').value;
      // eslint-disable-next-line no-bitwise
      const allowableCueTypes = this.CURRENT_USER_RBAC.cuetypes.filter((x) => (x[1] & writeMask) !== 0).map((x) => x[0].id);
      return [
        { value: null, text: 'N/A' },
        ...this.cueTypes.filter((cueType) => allowableCueTypes.includes(cueType.id)).map((cueType) => ({ value: cueType.id, text: `${cueType.prefix}: ${cueType.description}` })),
      ];
    },
    needsHeadings() {
      const ret = [];
      this.line.line_parts.forEach(function checkLinePartNeedsHeading(part) {
        if (this.previousLine == null
          || this.previousLine.line_parts.length !== this.line.line_parts.length) {
          ret.push(true);
        } else {
          const matchingIndex = this.previousLine.line_parts.find((prevPart) => (
            prevPart.part_index === part.part_index));
          if (matchingIndex == null) {
            ret.push(true);
          } else {
            ret.push(!(matchingIndex.character_id === part.character_id
              && matchingIndex.character_group_id === part.character_group_id));
          }
        }
      }, this);
      return ret;
    },
    needsHeadingsAny() {
      return this.needsHeadings.some((x) => (x === true));
    },
    needsActSceneLabel() {
      if (this.previousLine == null) {
        return true;
      }
      return !(this.previousLine.act_id === this.line.act_id
        && this.previousLine.scene_id === this.line.scene_id);
    },
    actLabel() {
      return this.acts.find((act) => (act.id === this.line.act_id)).name;
    },
    sceneLabel() {
      return this.scenes.find((scene) => (scene.id === this.line.scene_id)).name;
    },
    stageDirectionStyle() {
      const sdStyle = this.stageDirectionStyles.find(
        (style) => (style.id === this.line.stage_direction_style_id),
      );
      const override = this.stageDirectionStyleOverrides
        .find((elem) => elem.settings.id === sdStyle.id);
      if (this.line.line_type === 2) {
        return override ? override.settings : sdStyle;
      }
      return null;
    },
    stageDirectionStyling() {
      if (this.line.stage_direction_style_id == null || this.stageDirectionStyle == null) {
        return {
          'background-color': 'darkslateblue',
          'font-style': 'italic',
        };
      }
      const style = {
        'font-weight': this.stageDirectionStyle.bold ? 'bold' : 'normal',
        'font-style': this.stageDirectionStyle.italic ? 'italic' : 'normal',
        'text-decoration-line': this.stageDirectionStyle.underline ? 'underline' : 'none',
        color: this.stageDirectionStyle.text_colour,
      };
      if (this.stageDirectionStyle.enable_background_colour) {
        style['background-color'] = this.stageDirectionStyle.background_colour;
      }
      return style;
    },
    flatScriptCues() {
      return Object.keys(this.SCRIPT_CUES).map((key) => this.SCRIPT_CUES[key]).flat();
    },
    isDuplicateNewCue() {
      if (this.newFormState.ident == null || this.newFormState.cueType == null) {
        return false;
      }
      return this.flatScriptCues.some((cue) => cue.cue_type_id === this.newFormState.cueType
        && cue.ident === this.newFormState.ident);
    },
    isDuplicateEditCue() {
      if (this.editFormState.ident == null || this.editFormState.cueType == null) {
        return false;
      }
      return this.flatScriptCues.some((cue) => cue.cue_type_id === this.editFormState.cueType
        && cue.ident === this.editFormState.ident
        && cue.id !== this.editFormState.cueId);
    },
  },
  methods: {
    contrastColor,
    openNewForm() {
      this.resetNewForm();
      this.newFormState.lineId = this.line.id;
      this.$bvModal.show(`line_${this.lineIndex}_-new-cue`);
    },
    resetNewForm() {
      this.newFormState = {
        cueType: null,
        ident: null,
        lineId: null,
      };
      this.submittingNewCue = false;

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    validateNewState(name) {
      const { $dirty, $error } = this.$v.newFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitNew(event) {
      this.$v.newFormState.$touch();
      if (this.$v.newFormState.$anyError || this.submittingNewCue) {
        event.preventDefault();
        return;
      }

      this.submittingNewCue = true;
      try {
        await this.ADD_NEW_CUE(this.newFormState);
        this.$bvModal.hide(`line_${this.lineIndex}_-new-cue`);
        this.resetNewForm();
      } catch (error) {
        log.error('Error submitting new cue:', error);
        event.preventDefault();
      } finally {
        this.submittingNewCue = false;
      }
    },
    openEditForm(cue) {
      this.resetEditForm();
      this.editFormState.cueId = cue.id;
      this.editFormState.cueType = cue.cue_type_id;
      this.editFormState.ident = cue.ident;
      this.editFormState.lineId = this.line.id;
      this.$bvModal.show(`line_${this.lineIndex}_-edit-cue`);
    },
    resetEditForm() {
      this.editFormState = {
        cueId: null,
        cueType: null,
        ident: null,
        lineId: null,
      };
      this.submittingEditCue = false;
      this.deletingCue = false;

      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    validateEditState(name) {
      const { $dirty, $error } = this.$v.editFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitEdit(event) {
      this.$v.editFormState.$touch();
      if (this.$v.editFormState.$anyError || this.submittingEditCue) {
        event.preventDefault();
        return;
      }

      this.submittingEditCue = true;
      try {
        await this.EDIT_CUE(this.editFormState);
        this.$bvModal.hide(`line_${this.lineIndex}_-edit-cue`);
        this.resetEditForm();
      } catch (error) {
        log.error('Error submitting edit cue:', error);
        event.preventDefault();
      } finally {
        this.submittingEditCue = false;
      }
    },
    async deleteCue(event) {
      this.$v.editFormState.$touch();
      if (this.$v.editFormState.$anyError || this.deletingCue) {
        event.preventDefault();
        return;
      }

      const msg = 'Are you sure you want to delete this cue?';
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.deletingCue = true;
        try {
          await this.DELETE_CUE({
            cueId: this.editFormState.cueId,
            lineId: this.editFormState.lineId,
          });
          this.$bvModal.hide(`line_${this.lineIndex}_-edit-cue`);
          this.resetEditForm();
        } catch (error) {
          log.error('Error deleting cue:', error);
        } finally {
          this.deletingCue = false;
        }
      }
    },
    cueLabel(cue) {
      const cueType = this.cueTypes.find((cT) => (cT.id === cue.cue_type_id));
      return `${cueType.prefix} ${cue.ident}`;
    },
    cueBackgroundColour(cue) {
      const cueType = this.cueTypes.find((ct) => ct.id === cue.cue_type_id);
      if (!cueType) return '#000000'; // Fallback

      // Check if user has an override for this cue type
      const override = this.CUE_COLOUR_OVERRIDES.find((o) => o.settings.id === cueType.id);
      if (override) {
        return override.settings.colour;
      }

      return cueType.colour;
    },
    isWholeLineCut(line) {
      if (line.line_type === 3) {
        return false;
      }
      if (line.line_type === 4) {
        return true;
      }
      return line.line_parts.every((linePart) => (this.linePartCuts.includes(linePart.id)
            || linePart.line_text == null || linePart.line_text.trim().length === 0), this);
    },
    ...mapActions(['ADD_NEW_CUE', 'EDIT_CUE', 'DELETE_CUE']),
  },
};
</script>

<style scoped>
  .viewable-line {
    margin: 0;
  }
  .cue-button {
    padding: .2rem;
  }
  .stage-direction {
    margin-top: 1rem;
    margin-bottom: 1rem;
  }
  .cut-line-part {
    text-decoration: line-through;
  }
</style>
