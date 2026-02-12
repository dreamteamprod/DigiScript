<template>
  <b-form-row>
    <b-col cols="2">
      <b-form-row>
        <b-col cols="6">
          <b-form-group id="act-input-group" label-size="sm" label=" " label-for="act-input">
            <b-form-select
              id="act-input"
              v-model="$v.state.act_id.$model"
              name="act-input"
              :options="actOptions"
              :state="validateState('act_id')"
              @change="stateChange"
            />
          </b-form-group>
        </b-col>
        <b-col cols="6">
          <b-form-group id="scene-input-group" label-size="sm" label=" " label-for="scene-input">
            <b-form-select
              id="scene-input"
              v-model="$v.state.scene_id.$model"
              name="scene-input"
              :options="sceneOptions"
              :state="validateState('scene_id')"
              @change="stateChange"
            />
          </b-form-group>
        </b-col>
      </b-form-row>
      <b-form-row>
        <b-col style="align-content: center">
          <b-button-group>
            <b-button variant="success" :disabled="!lineValid" @click="doneEditing">
              Done
            </b-button>
            <b-button variant="danger" @click.stop.prevent="deleteLine"> Delete </b-button>
          </b-button-group>
        </b-col>
      </b-form-row>
    </b-col>
    <template v-if="lineType === LINE_TYPES.DIALOGUE || lineType === LINE_TYPES.STAGE_DIRECTION">
      <template v-if="state.line_parts.length > 0">
        <script-line-part
          v-for="(part, index) in state.line_parts"
          :key="`line_${lineIndex}_part_${index}`"
          v-model="$v.state.line_parts.$model[index]"
          :y-part-map="getYPartMap(index)"
          :focus-input="index === 0"
          :characters="characters"
          :character-groups="characterGroups"
          :show-add-button="
            index === state.line_parts.length - 1 &&
            lineType === LINE_TYPES.DIALOGUE &&
            CURRENT_SHOW.script_mode === 1
          "
          :enable-add-button="state.line_parts.length < 4 && lineType === LINE_TYPES.DIALOGUE"
          :line-type="lineType"
          :line-parts="state.line_parts"
          @input="stateChange"
          @addLinePart="addLinePart"
          @tryFinishLine="tryFinishLine"
        />
        <b-col
          v-if="lineType === LINE_TYPES.STAGE_DIRECTION && stageDirectionStyles.length > 0"
          cols="2"
        >
          <b-form-select
            id="stage-direction-style"
            v-model="$v.state.stage_direction_style_id.$model"
            name="stage-direction-style"
            :options="stageDirectionStylesOptions"
            :state="validateState('stage_direction_style_id')"
            @change="stateChange"
          />
        </b-col>
      </template>
      <b-col v-else cols="10" style="text-align: right">
        <b-button v-b-popover.hover.top="'Add line part'" @click="addLinePart">
          <b-icon-plus-square-fill variant="success" />
        </b-button>
      </b-col>
    </template>
    <template v-else>
      <b-col>
        <b-alert variant="secondary" show>
          <p class="text-muted small" style="margin: 0">
            <template v-if="lineType === LINE_TYPES.CUE_LINE">
              Cue Lines have no editable content.
            </template>
            <template v-else-if="lineType === LINE_TYPES.SPACING">
              Spacing Lines have no editable content.
            </template>
            <template v-else> This line type is not recognized. </template>
          </p>
        </b-alert>
      </b-col>
    </template>
  </b-form-row>
</template>

<script>
import * as Y from 'yjs';
import { mapGetters } from 'vuex';
import { required, requiredIf } from 'vuelidate/lib/validators';
import ScriptLinePart from '@/vue_components/show/config/script/ScriptLinePart.vue';
import { notNull, notNullAndGreaterThanZero } from '@/js/customValidators';
import { LINE_TYPES } from '@/constants/lineTypes';
import { nullToZero, zeroToNull } from '@/utils/yjs/yjsBridge';

export default {
  name: 'ScriptLineEditor',
  components: { ScriptLinePart },
  events: ['input', 'doneEditing', 'deleteLine'],
  props: {
    lineIndex: {
      required: true,
      type: Number,
    },
    currentEditPage: {
      required: true,
      type: Number,
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
    previousLineFn: {
      required: true,
      type: Function,
    },
    nextLineFn: {
      required: true,
      type: Function,
    },
    lineType: {
      required: true,
      type: Number,
    },
    stageDirectionStyles: {
      required: true,
      type: Array,
    },
    value: {
      required: true,
      type: Object,
    },
    yLineMap: {
      type: Object,
      default: null,
    },
  },
  data() {
    return {
      LINE_TYPES,
      state: this.value,
      blankLinePartObj: {
        id: null,
        line_id: null,
        part_index: null,
        character_id: null,
        character_group_id: null,
        line_text: '',
      },
      previousLine: null,
      nextLine: null,
      recalculationTimeout: null,
      abortController: null,
      /** @type {Function|null} Y.Map observer cleanup */
      ymapObserverCleanup: null,
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
        required: requiredIf(function isLinePartsRequired() {
          return (
            this.lineType === LINE_TYPES.DIALOGUE || this.lineType === LINE_TYPES.STAGE_DIRECTION
          );
        }),
        $each: {
          character_id: {
            required: requiredIf(function isCharacterRequired(m) {
              return this.lineType === LINE_TYPES.DIALOGUE && m.character_group_id == null;
            }),
          },
          character_group_id: {
            required: requiredIf(function isCharacterGroupRequired(m) {
              return this.lineType === LINE_TYPES.DIALOGUE && m.character_id == null;
            }),
          },
          line_text: {
            required: requiredIf(function isLineTextRequired() {
              return (
                (this.lineType === LINE_TYPES.DIALOGUE ||
                  this.lineType === LINE_TYPES.STAGE_DIRECTION) &&
                (this.state.line_parts.length <= 1 ||
                  !this.state.line_parts.some((x) => x.line_text !== ''))
              );
            }),
          },
        },
      },
      stage_direction_style_id: {},
    },
  },
  computed: {
    ...mapGetters(['SCENE_BY_ID', 'ACT_BY_ID', 'TMP_SCRIPT', 'ALL_DELETED_LINES', 'CURRENT_SHOW']),
    currentPageScript() {
      return this.TMP_SCRIPT[this.currentEditPage.toString()] || [];
    },
    currentPageDeletedLines() {
      return this.ALL_DELETED_LINES[this.currentEditPage.toString()] || [];
    },
    nextActs() {
      // Start act is either the first act for the show, or the act of the previous line if there
      // is one
      let startAct = this.acts.find((act) => act.previous_act == null);
      if (this.previousLine != null) {
        startAct = this.acts.find((act) => act.id === this.previousLine.act_id);
      }
      const validActs = [];
      let nextAct = startAct;
      let loopCount = 0;
      // Find all valid acts, if there is no next line then this is all acts after the start act.
      // If there is a next line, this is all acts up to and including the act of the next line
      while (nextAct != null) {
        loopCount++;
        if (loopCount > this.acts.length) break;
        validActs.push(JSON.parse(JSON.stringify(nextAct)));
        if (this.nextLine != null && this.nextLine.act_id === nextAct.id) {
          break;
        }
        nextAct = this.ACT_BY_ID(nextAct.next_act);
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
      const scenes = this.scenes.filter((scene) => scene.act === this.state.act_id);
      // Start scene is either the first scene of the act, or the scene of the previous line if
      // there is one
      let startScene = scenes.find((scene) => scene.previous_scene == null);
      if (this.previousLine != null && this.previousLine.act_id === this.state.act_id) {
        startScene = scenes.find((scene) => scene.id === this.previousLine.scene_id);
      }
      const validScenes = [];
      let nextScene = startScene;
      let loopCount = 0;
      // Find all valid scenes, if there is no next line then this is all scenes after the start
      // scene. If there is a next line, this is all scenes up to and including the scene of the
      // next line
      while (nextScene != null) {
        loopCount++;
        if (loopCount > scenes.length) break;
        validScenes.push(JSON.parse(JSON.stringify(nextScene)));
        if (this.nextLine != null && this.nextLine.scene_id === nextScene.id) {
          break;
        }
        nextScene = this.SCENE_BY_ID(nextScene.next_scene);
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
    stageDirectionStylesOptions() {
      return [
        { value: null, text: 'N/A' },
        ...this.stageDirectionStyles.map((style) => ({ value: style.id, text: style.description })),
      ];
    },
  },
  watch: {
    currentPageScript: {
      handler() {
        this.scheduleRecalculation();
      },
      deep: true,
    },
    currentPageDeletedLines: {
      handler() {
        this.scheduleRecalculation();
      },
      deep: true,
    },
    lineIndex() {
      this.scheduleRecalculation();
    },
    ALL_DELETED_LINES: {
      handler() {
        this.scheduleRecalculation();
      },
      deep: true,
    },
    yLineMap(newVal, oldVal) {
      if (oldVal) this.teardownYLineObservers();
      if (newVal) this.setupYLineObservers();
    },
  },
  async created() {
    if (this.yLineMap) {
      this.setupYLineObservers();
    }
    this.previousLine = await this.previousLineFn(this.lineIndex);
    this.nextLine = await this.nextLineFn(this.lineIndex);
    if (
      this.state.line_parts.length === 0 &&
      (this.lineType === LINE_TYPES.DIALOGUE || this.lineType === LINE_TYPES.STAGE_DIRECTION)
    ) {
      this.addLinePart();
    }
  },
  mounted() {
    this.$v.state.$touch();
  },
  beforeDestroy() {
    this.teardownYLineObservers();
    if (this.recalculationTimeout) {
      clearTimeout(this.recalculationTimeout);
    }
    if (this.abortController) {
      this.abortController.abort();
    }
  },
  methods: {
    scheduleRecalculation() {
      // Cancel any pending recalculation
      if (this.recalculationTimeout) {
        clearTimeout(this.recalculationTimeout);
      }

      // Debounce recalculation by 100ms
      this.recalculationTimeout = setTimeout(() => {
        this.recalculatePreviousNextLines();
      }, 100);
    },
    async recalculatePreviousNextLines() {
      // Cancel any in-flight async operations
      if (this.abortController) {
        this.abortController.abort();
      }

      // Create new abort controller for this operation
      this.abortController = new AbortController();
      const { signal } = this.abortController;

      try {
        const prevLine = await this.previousLineFn(this.lineIndex);
        if (signal.aborted) return;
        this.previousLine = prevLine;

        const nxtLine = await this.nextLineFn(this.lineIndex);
        if (signal.aborted) return;
        this.nextLine = nxtLine;
      } catch (error) {
        if (error.name !== 'AbortError') {
          console.error('Error recalculating previous/next lines:', error);
        }
      }
    },
    validateState(name) {
      const { $dirty, $error } = this.$v.state[name];
      return $dirty ? !$error : null;
    },
    doneEditing() {
      this.$emit('doneEditing');
    },
    /**
     * Called on dropdown changes and when child ScriptLinePart emits input.
     * In collab mode, writes line-level fields to Y.Map.
     */
    stateChange() {
      this.$v.state.$touch();
      if (this.yLineMap && this.yLineMap.doc) {
        this.yLineMap.doc.transact(() => {
          this.yLineMap.set('act_id', nullToZero(this.state.act_id));
          this.yLineMap.set('scene_id', nullToZero(this.state.scene_id));
          this.yLineMap.set(
            'stage_direction_style_id',
            nullToZero(this.state.stage_direction_style_id)
          );
        }, 'local-edit');
      }
      this.$emit('input', this.state);
    },
    addLinePart() {
      const blankLine = JSON.parse(JSON.stringify(this.blankLinePartObj));
      blankLine.line_id = this.state.id;
      blankLine.part_index = this.state.line_parts.length;
      this.state.line_parts.push(blankLine);
      if (this.lineType === LINE_TYPES.DIALOGUE && this.previousLine != null) {
        const newPartIndex = this.state.line_parts.length - 1;
        const newPart = this.state.line_parts[newPartIndex];
        if (this.previousLine.line_parts.length >= newPartIndex + 1) {
          const previousPart = this.previousLine.line_parts[newPartIndex];
          if (previousPart.character_id != null) {
            newPart.character_id = previousPart.character_id;
          } else if (previousPart.character_group_id != null) {
            newPart.character_group_id = previousPart.character_group_id;
          }
        }
      }
      // Sync new part to Y.Doc for collaborative editing
      if (this.yLineMap) {
        this.addPartToYDoc(
          this.state.line_parts[this.state.line_parts.length - 1],
          this.state.line_parts.length - 1
        );
      }
      this.stateChange();
    },
    /**
     * Create a Y.Map for a new line part in the Y.Doc parts array.
     * @param {object} partObj - The plain part object
     * @param {number} index - The part index
     */
    addPartToYDoc(partObj, index) {
      const partsArray = this.yLineMap.get('parts');
      if (!partsArray || !this.yLineMap.doc) return;
      this.yLineMap.doc.transact(() => {
        const partMap = new Y.Map();
        partsArray.push([partMap]);
        partMap.set('_id', 0);
        partMap.set('character_id', nullToZero(partObj.character_id));
        partMap.set('character_group_id', nullToZero(partObj.character_group_id));
        partMap.set('part_index', partObj.part_index ?? index);
        const ytext = new Y.Text();
        partMap.set('line_text', ytext);
        if (partObj.line_text) {
          ytext.insert(0, partObj.line_text);
        }
      }, 'local-edit');
    },
    /**
     * Get the Y.Map for a specific line part from the Y.Doc.
     * Returns null when not in collab mode or if the part doesn't exist.
     * @param {number} index - Part index
     * @returns {import('yjs').Map|null}
     */
    getYPartMap(index) {
      if (!this.yLineMap) return null;
      const parts = this.yLineMap.get('parts');
      if (!parts || index >= parts.length) return null;
      return parts.get(index);
    },
    /**
     * Set up Y.Map observer for remote changes to line-level fields.
     */
    setupYLineObservers() {
      const mapObserver = (event) => {
        if (event.transaction.origin === 'local-edit') return;
        for (const key of event.keysChanged) {
          if (key === 'act_id') {
            this.state.act_id = zeroToNull(this.yLineMap.get('act_id'));
          } else if (key === 'scene_id') {
            this.state.scene_id = zeroToNull(this.yLineMap.get('scene_id'));
          } else if (key === 'stage_direction_style_id') {
            this.state.stage_direction_style_id = zeroToNull(
              this.yLineMap.get('stage_direction_style_id')
            );
          }
        }
      };
      this.yLineMap.observe(mapObserver);
      this.ymapObserverCleanup = () => this.yLineMap.unobserve(mapObserver);
    },
    /**
     * Remove Y.Map observer.
     */
    teardownYLineObservers() {
      if (this.ymapObserverCleanup) {
        this.ymapObserverCleanup();
        this.ymapObserverCleanup = null;
      }
    },
    deleteLine() {
      this.$emit('deleteLine');
    },
    tryFinishLine() {
      this.$v.state.$touch();
      if (this.lineValid) {
        this.doneEditing();
      }
    },
  },
};
</script>

<style scoped></style>
