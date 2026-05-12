<template>
  <b-container ref="lineContainer" class="mx-0" style="margin: 0; padding: 0 0 0.2rem" fluid>
    <b-row v-if="needsActSceneLabelSimple">
      <b-col cols="3" />
      <b-col cols="9">
        <h4>{{ actLabel }} - {{ sceneLabel }}</h4>
      </b-col>
    </b-row>
    <b-row :class="{ 'stage-direction': line.line_type === LINE_TYPES.STAGE_DIRECTION }">
      <b-col cols="3" class="cue-column" style="text-align: right">
        <b-button-group v-if="line.line_type !== LINE_TYPES.SPACING">
          <b-button
            v-for="cue in cues"
            :key="cue.id"
            :disabled="!IS_CUE_EDITOR"
            class="cue-button"
            :style="{
              backgroundColor: cueBackgroundColour(cue),
              color: contrastColor({ bgColor: cueBackgroundColour(cue) }),
            }"
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
      <template v-if="line.line_type === LINE_TYPES.DIALOGUE">
        <b-col
          v-for="(part, index) in line.line_parts"
          :key="`line_${lineIndex}_part_${index}`"
          :style="headingStyle"
        >
          <template v-if="needsHeadings[index]">
            <b v-if="part.character_id != null">
              {{ characters.find((char) => char.id === part.character_id).name }}
            </b>
            <b v-else>
              {{ characterGroups.find((char) => char.id === part.character_group_id).name }}
            </b>
          </template>
          <b v-else-if="needsHeadingsAny">&nbsp;</b>
          <p
            class="viewable-line"
            :class="{ 'cut-line-part': linePartCuts.indexOf(part.id) !== -1 }"
          >
            {{ part.line_text }}
          </p>
        </b-col>
      </template>
      <template v-else-if="line.line_type === LINE_TYPES.STAGE_DIRECTION">
        <b-col :key="`line_${lineIndex}_stage_direction`" :style="{ textAlign: scriptTextAlign }">
          <i
            class="viewable-line"
            :class="{ 'cut-line-part': linePartCuts.indexOf(line.line_parts[0].id) !== -1 }"
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
      <template v-else-if="line.line_type === LINE_TYPES.CUE_LINE">
        <b-col :key="`line_${lineIndex}_cue_line`" :style="dialogueStyle">
          <b-alert variant="secondary" show>
            <p class="text-muted small" style="margin: 0">Cue Line</p>
          </b-alert>
        </b-col>
      </template>
      <template v-else-if="line.line_type === LINE_TYPES.SPACING">
        <b-col :key="`line_${lineIndex}_spacing`" :style="dialogueStyle">
          <b-alert variant="secondary" show>
            <p class="text-muted small" style="margin: 0">Spacing Line</p>
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
      <b-form ref="new-cue-form" @submit.stop.prevent="onSubmitNew">
        <b-form-group id="new-type-input-group" label="Cue Type" label-for="new-type-input">
          <b-form-select
            id="new-type-input"
            v-model="$v.newFormState.cueType.$model"
            :options="cueTypeOptions"
            :state="validateNewState('cueType')"
            aria-describedby="new-cue-type-feedback"
          />
          <b-form-invalid-feedback id="new-cue-type-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group id="new-ident-input-group" label="Identifier" label-for="new-ident-input">
          <b-form-input
            id="new-ident-input"
            v-model="$v.newFormState.ident.$model"
            name="new-ident-input"
            :state="validateNewState('ident')"
            aria-describedby="new-ident-feedback"
          />
          <b-form-invalid-feedback id="new-ident-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group>
          <b-form-text v-if="isDuplicateNewCue" class="text-warning">
            ⚠️ A cue with this identifier already exists for this cue type
          </b-form-text>
        </b-form-group>
        <template
          v-if="
            line.line_type === LINE_TYPES.DIALOGUE || line.line_type === LINE_TYPES.STAGE_DIRECTION
          "
        >
          <hr />
          <b-form-group id="line-render-group" label="Script Line" label-for="line-render">
            <b-form-text id="line-render">
              <b-row>
                <template v-if="line.line_type === LINE_TYPES.STAGE_DIRECTION">
                  <b-col
                    :key="`line_${lineIndex}_stage_direction`"
                    :style="{ textAlign: scriptTextAlign }"
                  >
                    <i
                      class="viewable-line"
                      :class="{
                        'cut-line-part': linePartCuts.indexOf(line.line_parts[0].id) !== -1,
                      }"
                      :style="stageDirectionStyling"
                    >
                      <template
                        v-if="
                          stageDirectionStyle != null && stageDirectionStyle.text_format === 'upper'
                        "
                      >
                        {{ line.line_parts[0].line_text | uppercase }}
                      </template>
                      <template
                        v-else-if="
                          stageDirectionStyle != null && stageDirectionStyle.text_format === 'lower'
                        "
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
                    :style="headingStyle"
                  >
                    <b v-if="part.character_id != null">
                      {{ characters.find((char) => char.id === part.character_id).name }}
                    </b>
                    <b v-else>
                      {{ characterGroups.find((char) => char.id === part.character_group_id).name }}
                    </b>

                    <p
                      class="viewable-line"
                      :class="{ 'cut-line-part': linePartCuts.indexOf(part.id) !== -1 }"
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
      <b-form ref="edit-cue-form" @submit.stop.prevent="onSubmitEdit">
        <b-form-group id="edit-type-input-group" label="Cue Type" label-for="edit-type-input">
          <b-form-select
            id="edit-type-input"
            v-model="$v.editFormState.cueType.$model"
            :options="cueTypeOptions"
            :state="validateEditState('cueType')"
            aria-describedby="edit-cue-type-feedback"
          />
          <b-form-invalid-feedback id="edit-cue-type-feedback">
            This is a required field.
          </b-form-invalid-feedback>
        </b-form-group>
        <b-form-group id="edit-ident-input-group" label="Identifier" label-for="edit-ident-input">
          <b-form-input
            id="edit-ident-input"
            v-model="$v.editFormState.ident.$model"
            name="edit-ident-input"
            :state="validateEditState('ident')"
            aria-describedby="edit-ident-feedback"
          />
          <b-form-invalid-feedback id="edit-ident-feedback">
            This is a required field.
          </b-form-invalid-feedback>
          <b-form-text v-if="isDuplicateEditCue" class="text-warning">
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

<script lang="ts">
import { defineComponent } from 'vue';
import { required } from 'vuelidate/lib/validators';
import { mapActions, mapGetters } from 'vuex';
import { contrastColor } from 'contrast-color';
import log from 'loglevel';
import { LINE_TYPES } from '@/constants/lineTypes';
import { isWholeLineCut as isWholeLineCutUtil } from '@/js/scriptUtils';
import scriptDisplayMixin from '@/mixins/scriptDisplayMixin';

export default defineComponent({
  name: 'ScriptLineCueEditor',
  mixins: [scriptDisplayMixin],
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
      LINE_TYPES,
      newFormState: {
        cueType: null as number | null,
        ident: null as string | null,
        lineId: null as number | null,
      },
      editFormState: {
        cueId: null as number | null,
        cueType: null as number | null,
        ident: null as string | null,
        lineId: null as number | null,
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
    ...mapGetters([
      'IS_CUE_EDITOR',
      'RBAC_ROLES',
      'CURRENT_USER_RBAC',
      'IS_ADMIN_USER',
      'SCRIPT_CUES',
      'CUE_COLOUR_OVERRIDES',
    ]),
    cueTypeOptions(): unknown[] {
      if ((this as any).IS_ADMIN_USER) {
        return [
          { value: null, text: 'N/A' },
          ...(this.cueTypes as any[]).map((cueType) => ({
            value: cueType.id,
            text: `${cueType.prefix}: ${cueType.description}`,
          })),
        ];
      }
      const writeMask = ((this as any).RBAC_ROLES as any[]).find(
        (x: any) => x.key === 'WRITE'
      ).value;

      const allowableCueTypes = (this as any).CURRENT_USER_RBAC.cuetypes
        .filter((x: any) => (x[1] & writeMask) !== 0)
        .map((x: any) => x[0].id);
      return [
        { value: null, text: 'N/A' },
        ...(this.cueTypes as any[])
          .filter((cueType) => allowableCueTypes.includes(cueType.id))
          .map((cueType) => ({
            value: cueType.id,
            text: `${cueType.prefix}: ${cueType.description}`,
          })),
      ];
    },
    needsHeadings(): boolean[] {
      const ret: boolean[] = [];
      (this.line as any).line_parts.forEach((part: any) => {
        if (
          this.previousLine == null ||
          (this.previousLine as any).line_parts.length !== (this.line as any).line_parts.length
        ) {
          ret.push(true);
        } else {
          const matchingIndex = (this.previousLine as any).line_parts.find(
            (prevPart: any) => prevPart.part_index === part.part_index
          );
          if (matchingIndex == null) {
            ret.push(true);
          } else {
            ret.push(
              !(
                matchingIndex.character_id === part.character_id &&
                matchingIndex.character_group_id === part.character_group_id
              )
            );
          }
        }
      });
      return ret;
    },
    needsActSceneLabelSimple(): boolean {
      if (this.previousLine == null) {
        return true;
      }
      return !(
        (this.previousLine as any).act_id === (this.line as any).act_id &&
        (this.previousLine as any).scene_id === (this.line as any).scene_id
      );
    },
    flatScriptCues(): any[] {
      return Object.keys((this as any).SCRIPT_CUES)
        .map((key) => (this as any).SCRIPT_CUES[key])
        .flat();
    },
    isDuplicateNewCue(): boolean {
      if (this.newFormState.ident == null || this.newFormState.cueType == null) {
        return false;
      }
      return this.flatScriptCues.some(
        (cue) =>
          cue.cue_type_id === this.newFormState.cueType && cue.ident === this.newFormState.ident
      );
    },
    isDuplicateEditCue(): boolean {
      if (this.editFormState.ident == null || this.editFormState.cueType == null) {
        return false;
      }
      return this.flatScriptCues.some(
        (cue) =>
          cue.cue_type_id === this.editFormState.cueType &&
          cue.ident === this.editFormState.ident &&
          cue.id !== this.editFormState.cueId
      );
    },
  },
  methods: {
    contrastColor,
    openNewForm(): void {
      this.resetNewForm();
      this.newFormState.lineId = (this.line as any).id;
      (this as any).$bvModal.show(`line_${this.lineIndex}_-new-cue`);
    },
    resetNewForm(): void {
      this.newFormState = {
        cueType: null,
        ident: null,
        lineId: null,
      };
      this.submittingNewCue = false;

      this.$nextTick(() => {
        (this as any).$v.$reset();
      });
    },
    validateNewState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.newFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitNew(event: Event): Promise<void> {
      (this as any).$v.newFormState.$touch();
      if ((this as any).$v.newFormState.$anyError || this.submittingNewCue) {
        event.preventDefault();
        return;
      }

      this.submittingNewCue = true;
      try {
        await (this as any).ADD_NEW_CUE(this.newFormState);
        (this as any).$bvModal.hide(`line_${this.lineIndex}_-new-cue`);
        this.resetNewForm();
      } catch (error) {
        log.error('Error submitting new cue:', error);
        event.preventDefault();
      } finally {
        this.submittingNewCue = false;
      }
    },
    openEditForm(cue: any): void {
      this.resetEditForm();
      this.editFormState.cueId = cue.id;
      this.editFormState.cueType = cue.cue_type_id;
      this.editFormState.ident = cue.ident;
      this.editFormState.lineId = (this.line as any).id;
      (this as any).$bvModal.show(`line_${this.lineIndex}_-edit-cue`);
    },
    resetEditForm(): void {
      this.editFormState = {
        cueId: null,
        cueType: null,
        ident: null,
        lineId: null,
      };
      this.submittingEditCue = false;
      this.deletingCue = false;

      this.$nextTick(() => {
        (this as any).$v.$reset();
      });
    },
    validateEditState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.editFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitEdit(event: Event): Promise<void> {
      (this as any).$v.editFormState.$touch();
      if ((this as any).$v.editFormState.$anyError || this.submittingEditCue) {
        event.preventDefault();
        return;
      }

      this.submittingEditCue = true;
      try {
        await (this as any).EDIT_CUE(this.editFormState);
        (this as any).$bvModal.hide(`line_${this.lineIndex}_-edit-cue`);
        this.resetEditForm();
      } catch (error) {
        log.error('Error submitting edit cue:', error);
        event.preventDefault();
      } finally {
        this.submittingEditCue = false;
      }
    },
    async deleteCue(event: Event): Promise<void> {
      (this as any).$v.editFormState.$touch();
      if ((this as any).$v.editFormState.$anyError || this.deletingCue) {
        event.preventDefault();
        return;
      }

      const msg = 'Are you sure you want to delete this cue?';
      const action = await (this as any).$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.deletingCue = true;
        try {
          await (this as any).DELETE_CUE({
            cueId: this.editFormState.cueId,
            lineId: this.editFormState.lineId,
          });
          (this as any).$bvModal.hide(`line_${this.lineIndex}_-edit-cue`);
          this.resetEditForm();
        } catch (error) {
          log.error('Error deleting cue:', error);
        } finally {
          this.deletingCue = false;
        }
      }
    },
    cueLabel(cue: any): string {
      const cueType = (this.cueTypes as any[]).find((cT) => cT.id === cue.cue_type_id);
      return `${cueType.prefix} ${cue.ident}`;
    },
    cueBackgroundColour(cue: any): string {
      const cueType = (this.cueTypes as any[]).find((ct) => ct.id === cue.cue_type_id);
      if (!cueType) return '#000000';

      const override = ((this as any).CUE_COLOUR_OVERRIDES as any[]).find(
        (o) => o.settings.id === cueType.id
      );
      if (override) {
        return override.settings.colour;
      }

      return cueType.colour;
    },
    isWholeLineCut(line: any): boolean {
      return isWholeLineCutUtil(line, this.linePartCuts as any[]);
    },
    ...mapActions(['ADD_NEW_CUE', 'EDIT_CUE', 'DELETE_CUE']),
  },
});
</script>

<style scoped>
.viewable-line {
  margin: 0;
}
.cue-button {
  padding: 0.2rem;
}
.stage-direction {
  margin-top: 1rem;
  margin-bottom: 1rem;
}
.cut-line-part {
  text-decoration: line-through;
}
</style>
