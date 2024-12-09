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
    <b-row :class="{'stage-direction': line.stage_direction}">
      <b-col
        cols="3"
        class="cue-column"
        style="text-align: right"
      >
        <b-button-group>
          <b-button
            v-for="cue in cues"
            :key="cue.id"
            class="cue-button"
            :style="{backgroundColor: cueBackgroundColour(cue),
                     color: contrastColor({'bgColor': cueBackgroundColour(cue)})}"
            @click.stop="openEditForm(cue)"
          >
            {{ cueLabel(cue) }}
          </b-button>
          <b-button
            class="cue-button"
            :disabled="isWholeLineCut(line)"
            @click.stop="openNewForm"
          >
            <b-icon-plus-square-fill variant="success" />
          </b-button>
        </b-button-group>
      </b-col>
      <template v-if="line.stage_direction">
        <b-col
          :key="`line_${lineIndex}_stage_direction`"
          style="text-align: center"
        >
          <i
            class="viewable-line"
            style="background-color: darkslateblue"
          >
            {{ line.line_parts[0].line_text }}
          </i>
        </b-col>
      </template>
      <template v-else>
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
          <p
            class="viewable-line"
            :class="{'cut-line-part': linePartCuts.indexOf(part.id) !== -1}"
          >
            {{ part.line_text }}
          </p>
        </b-col>
      </template>
    </b-row>
    <b-modal
      :id="`line_${lineIndex}_-new-cue`"
      title="Add New Cue"
      size="md"
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
      </b-form>
    </b-modal>
    <b-modal
      :id="`line_${lineIndex}_-edit-cue`"
      title="Edit Cue"
      size="md"
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
        </b-form-group>
      </b-form>
      <template #modal-footer="{ ok, cancel }">
        <b-button
          variant="secondary"
          @click="cancel()"
        >
          Cancel
        </b-button>
        <b-button
          variant="danger"
          @click.stop="deleteCue"
        >
          Delete
        </b-button>
        <b-button
          variant="primary"
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
import { mapActions } from 'vuex';
import { contrastColor } from 'contrast-color';

export default {
  name: 'ScriptLineCueEditor',
  props: {
    line: {
      required: true,
    },
    lineIndex: {
      required: true,
      type: Number,
    },
    previousLine: {
      required: true,
    },
    acts: {
      required: true,
    },
    scenes: {
      required: true,
    },
    characters: {
      required: true,
    },
    characterGroups: {
      required: true,
    },
    cues: {
      required: true,
    },
    cueTypes: {
      required: true,
    },
    linePartCuts: {
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
      if (this.$v.newFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.ADD_NEW_CUE(this.newFormState);
        this.resetNewForm();
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
      if (this.$v.editFormState.$anyError) {
        event.preventDefault();
      } else {
        await this.EDIT_CUE(this.editFormState);
        this.$bvModal.hide(`line_${this.lineIndex}_-edit-cue`);
        this.resetEditForm();
      }
    },
    async deleteCue(event) {
      this.$v.editFormState.$touch();
      if (this.$v.editFormState.$anyError) {
        event.preventDefault();
      } else {
        const msg = 'Are you sure you want to delete this cue?';
        const action = await this.$bvModal.msgBoxConfirm(msg, {});
        if (action === true) {
          await this.DELETE_CUE({
            cueId: this.editFormState.cueId,
            lineId: this.editFormState.lineId,
          });
          this.$bvModal.hide(`line_${this.lineIndex}_-edit-cue`);
          this.resetEditForm();
        }
      }
    },
    cueLabel(cue) {
      const cueType = this.cueTypes.find((cT) => (cT.id === cue.cue_type_id));
      return `${cueType.prefix} ${cue.ident}`;
    },
    cueBackgroundColour(cue) {
      return this.cueTypes.find((cueType) => (cueType.id === cue.cue_type_id)).colour;
    },
    isWholeLineCut(line) {
      return line.line_parts.every((linePart) => (this.linePartCuts.includes(linePart.id)), this);
    },
    ...mapActions(['ADD_NEW_CUE', 'EDIT_CUE', 'DELETE_CUE']),
  },
  computed: {
    cueTypeOptions() {
      return [
        { value: null, text: 'N/A' },
        ...this.cueTypes.map((cueType) => ({ value: cueType.id, text: `${cueType.prefix}: ${cueType.description}` })),
      ];
    },
    needsHeadings() {
      const ret = [];
      this.line.line_parts.forEach(function (part) {
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
