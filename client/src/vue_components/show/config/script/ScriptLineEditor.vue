<template>
  <b-form-row>
    <b-col cols="2">
      <b-form-row>
        <b-col cols="6">
          <b-form-group id="act-input-group" label-size="sm" label=" " label-for="act-input">
            <b-form-select id="act-input" name="act-input" :options="actOptions"
                           v-model="$v.state.act_id.$model"
                           :state="validateState('act_id')"
                           @change="stateChange"/>
          </b-form-group>
        </b-col>
        <b-col cols="6">
          <b-form-group id="scene-input-group" label-size="sm" label=" " label-for="scene-input">
            <b-form-select id="scene-input" name="scene-input" :options="sceneOptions"
                           v-model="$v.state.scene_id.$model"
                           :state="validateState('scene_id')"
                           @change="stateChange"/>
          </b-form-group>
        </b-col>
      </b-form-row>
      <b-form-row>
        <b-col style="align-content: center">
          <b-button-group>
            <b-button variant="success" @click="doneEditing" :disabled="!lineValid">
              Done
            </b-button>
            <b-button variant="danger" @click.stop.prevent="deleteLine">
              Delete
            </b-button>
          </b-button-group>
        </b-col>
      </b-form-row>
    </b-col>
    <template v-if="state.line_parts.length > 0">
      <script-line-part
        v-for="(part, index) in state.line_parts"
        :key="`line_${lineIndex}_part_${index}`"
        v-model="$v.state.line_parts.$model[index]"
        :characters="characters"
        :character-groups="characterGroups"
        :show-add-button="index === state.line_parts.length - 1 && !isStageDirection"
        :enable-add-button="state.line_parts.length < 4 && !isStageDirection"
        :is-stage-direction="isStageDirection"
        @input="stateChange"
        @addLinePart="addLinePart" />
    </template>
    <b-col cols="10" style="text-align: right" v-else>
      <b-button v-b-popover.hover.top="'Add line part'" @click="addLinePart">
        <b-icon-plus-square-fill variant="success" />
      </b-button>
    </b-col>
  </b-form-row>
</template>

<script>
import { required, requiredIf } from 'vuelidate/lib/validators';
import ScriptLinePart from '@/vue_components/show/config/script/ScriptLinePart.vue';
import { notNull, notNullAndGreaterThanZero } from '@/js/customValidators';

export default {
  name: 'ScriptLineEditor',
  components: { ScriptLinePart },
  events: ['input', 'doneEditing', 'deleteLine'],
  props: {
    lineIndex: {
      required: true,
      type: Number,
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
    previousLineFn: {
      required: true,
      type: Function,
    },
    nextLineFn: {
      required: true,
      type: Function,
    },
    isStageDirection: {
      required: true,
      type: Boolean,
    },
    value: {
      required: true,
    },
  },
  data() {
    return {
      state: this.value,
      blankLinePartObj: {
        id: null,
        line_id: null,
        part_index: null,
        character_id: null,
        character_group_id: null,
        line_text: null,
      },
      previousLine: null,
      nextLine: null,
    };
  },
  validations: {
    state: {
      act_id: {
        required,
        notNull,
        notNullAndGreaterThanZero,
      },
      scene_id: {
        required,
        notNull,
        notNullAndGreaterThanZero,
      },
      line_parts: {
        required,
        $each: {
          character_id: {
            required: requiredIf(function (m) {
              return this.isStageDirection === false && m.character_group_id == null;
            }),
          },
          character_group_id: {
            required: requiredIf(function (m) {
              return this.isStageDirection === false && m.character_id == null;
            }),
          },
          line_text: {
            required,
          },
        },
      },
    },
  },
  async created() {
    this.previousLine = await this.previousLineFn(this.lineIndex);
    this.nextLine = await this.nextLineFn(this.lineIndex);
    if (this.state.line_parts.length === 0) {
      this.addLinePart();
    }
  },
  mounted() {
    this.$v.state.$touch();
  },
  methods: {
    validateState(name) {
      const { $dirty, $error } = this.$v.state[name];
      return $dirty ? !$error : null;
    },
    doneEditing() {
      this.$emit('doneEditing');
    },
    stateChange() {
      this.$v.state.$touch();
      this.$emit('input', this.state);
    },
    addLinePart() {
      const blankLine = JSON.parse(JSON.stringify(this.blankLinePartObj));
      blankLine.line_id = this.state.id;
      blankLine.part_index = this.state.line_parts.length;
      this.state.line_parts.push(blankLine);
      this.stateChange();
    },
    deleteLine() {
      this.$emit('deleteLine');
    },
  },
  computed: {
    nextActs() {
      // Start act is either the first act for the show, or the act of the previous line if there
      // is one
      let startAct = this.acts.find((act) => (act.previous_act == null));
      if (this.previousLine != null) {
        startAct = this.acts.find((act) => (act.id === this.previousLine.act_id));
      }
      const validActs = [];
      let nextAct = startAct;
      // Find all valid acts, if there is no next line then this is all acts after the start act.
      // If there is a next line, this is all acts up to and including the act of the next line
      while (nextAct != null) {
        validActs.push(JSON.parse(JSON.stringify(nextAct)));
        if (this.nextLine != null && this.nextLine.act_id === nextAct.id) {
          break;
        }
        nextAct = nextAct.next_act;
      }
      return validActs;
    },
    actOptions() {
      return [
        { value: null, text: 'N/A', disabled: true },
        ...this.nextActs.map((act) => ({ value: act.id, text: act.name })),
      ];
    },
    nextScenes() {
      if (this.state.act_id == null) {
        return [];
      }
      const scenes = this.scenes.filter((scene) => (scene.act.id === this.state.act_id));
      // Start scene is either the first scene of the act, or the scene of the previous line if
      // there is one
      let startScene = scenes.find((scene) => (scene.previous_scene == null));
      if (this.previousLine != null && this.previousLine.act_id === this.state.act_id) {
        startScene = scenes.find((scene) => (scene.id === this.previousLine.scene_id));
      }
      const validScenes = [];
      let nextScene = startScene;
      // Find all valid scenes, if there is no next line then this is all scenes after the start
      // scene. If there is a next line, this is all scenes up to and including the scene of the
      // next line
      while (nextScene != null) {
        validScenes.push(JSON.parse(JSON.stringify(nextScene)));
        if (this.nextLine != null && this.nextLine.scene_id === nextScene.id) {
          break;
        }
        nextScene = nextScene.next_scene;
      }
      return validScenes;
    },
    sceneOptions() {
      return [
        { value: null, text: 'N/A', disabled: true },
        ...this.nextScenes.map((scene) => ({ value: scene.id, text: scene.name })),
      ];
    },
    lineValid() {
      return !this.$v.state.$anyError;
    },
  },
};
</script>

<style scoped>

</style>
