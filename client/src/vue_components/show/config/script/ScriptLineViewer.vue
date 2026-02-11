<template>
  <b-row
    :class="{
      'stage-direction': line.line_type === LINE_TYPES.STAGE_DIRECTION,
      'heading-padding': line.line_type === LINE_TYPES.DIALOGUE && needsHeadingsAll,
      'editing-indicator': editingUsers.length > 0,
    }"
    :style="editingBorderStyle"
  >
    <b-col cols="1">
      <p v-if="needsActSceneLabelSimple" class="viewable-line">
        {{ actLabel }}
      </p>
    </b-col>
    <b-col cols="1">
      <p v-if="needsActSceneLabelSimple" class="viewable-line">
        {{ sceneLabel }}
      </p>
    </b-col>
    <template v-if="line.line_type === LINE_TYPES.DIALOGUE">
      <b-col>
        <b-row v-if="needsHeadingsAny">
          <b-col
            v-for="(part, index) in line.line_parts"
            :key="`heading_${lineIndex}_part_${index}`"
            :style="headingStyle"
          >
            <template v-if="needsHeadings[index]">
              <b>
                <template v-if="part.character_id != null">
                  {{ characters.find((char) => char.id === part.character_id).name }}
                </template>
                <template v-else>
                  {{ characterGroups.find((char) => char.id === part.character_group_id).name }}
                </template>
              </b>
            </template>
            <b v-else>&nbsp;</b>
          </b-col>
        </b-row>
        <b-row>
          <b-col
            v-for="(part, index) in line.line_parts"
            :key="`line_${lineIndex}_part_${index}`"
            :style="dialogueStyle"
          >
            <p
              v-if="(canEdit && !IS_CUT_MODE) || !canEdit"
              class="viewable-line"
              :class="{ 'cut-line-part': linePartCuts.indexOf(part.id) !== -1 }"
            >
              {{ part.line_text }}
            </p>
            <a
              v-else
              class="viewable-line-cut"
              :class="{ 'cut-line-part': linePartCuts.indexOf(part.id) !== -1 }"
              @click.stop="cutLinePart(index)"
            >
              {{ part.line_text }}
            </a>
          </b-col>
        </b-row>
      </b-col>
    </template>
    <template v-else-if="line.line_type === LINE_TYPES.STAGE_DIRECTION">
      <b-col :key="`line_${lineIndex}_stage_direction`" :style="{ textAlign: scriptTextAlign }">
        <i
          v-if="(canEdit && !IS_CUT_MODE) || !canEdit"
          class="viewable-line"
          :style="stageDirectionStylingWithCuts"
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
        <a
          v-else
          class="viewable-line-cut"
          :style="stageDirectionStylingWithCuts"
          @click.stop="cutLinePart(0)"
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
        </a>
      </b-col>
    </template>
    <template v-else-if="line.line_type === LINE_TYPES.CUE_LINE">
      <b-col :key="`line_${lineIndex}_cue_line`" style="text-align: center">
        <b-alert variant="secondary" show>
          <p class="text-muted small" style="margin: 0">Cue Line</p>
        </b-alert>
      </b-col>
    </template>
    <template v-else-if="line.line_type === LINE_TYPES.SPACING">
      <b-col :key="`line_${lineIndex}_spacing`" style="text-align: center">
        <b-alert variant="secondary" show>
          <p class="text-muted small" style="margin: 0">Spacing Line</p>
        </b-alert>
      </b-col>
    </template>
    <b-col cols="1" align-self="end">
      <span v-if="editingUsers.length > 0" class="editing-badge" :title="editingTooltip">
        {{ editingUsers.map((u) => u.username).join(', ') }}
      </span>
      <b-dropdown
        v-show="canEdit && !IS_CUT_MODE"
        split
        text="Edit"
        right
        boundary="window"
        style="padding: 0"
        variant="link"
        @click.prevent.stop="editLine"
      >
        <b-dropdown-item-btn @click.prevent.stop="insertDialogue">
          Insert Dialogue
        </b-dropdown-item-btn>
        <b-dropdown-item-btn @click.prevent.stop="insertStageDirection">
          Insert Stage Direction
        </b-dropdown-item-btn>
        <b-dropdown-item-btn @click.prevent.stop="insertCueLine">
          Insert Cue Line
        </b-dropdown-item-btn>
        <b-dropdown-item-btn @click.prevent.stop="insertSpacing">
          Insert Spacing
        </b-dropdown-item-btn>
        <b-dropdown-item-btn variant="danger" @click.prevent.stop="deleteLine">
          Delete
        </b-dropdown-item-btn>
      </b-dropdown>
    </b-col>
  </b-row>
</template>

<script>
import { mapGetters } from 'vuex';
import { LINE_TYPES } from '@/constants/lineTypes';
import scriptDisplayMixin from '@/mixins/scriptDisplayMixin';

export default {
  name: 'ScriptLineViewer',
  mixins: [scriptDisplayMixin],
  events: [
    'editLine',
    'cutLinePart',
    'insertDialogue',
    'insertStageDirection',
    'insertCueLine',
    'insertSpacing',
    'deleteLine',
  ],
  props: {
    line: {
      required: true,
      type: Object,
    },
    lineIndex: {
      required: true,
      type: Number,
    },
    page: {
      required: true,
      type: Array,
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
    canEdit: {
      required: true,
      type: Boolean,
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
    editingUsers: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      LINE_TYPES,
    };
  },
  computed: {
    editingBorderStyle() {
      if (this.editingUsers.length === 0) return {};
      const COLLAB_COLORS = [
        '#e74c3c',
        '#3498db',
        '#2ecc71',
        '#f39c12',
        '#9b59b6',
        '#1abc9c',
        '#e67e22',
        '#e91e63',
      ];
      const color = COLLAB_COLORS[this.editingUsers[0].userId % COLLAB_COLORS.length];
      return { borderLeft: `3px solid ${color}`, paddingLeft: '5px' };
    },
    editingTooltip() {
      if (this.editingUsers.length === 0) return '';
      const names = this.editingUsers.map((u) => u.username).join(', ');
      return `${names} ${this.editingUsers.length === 1 ? 'is' : 'are'} editing this line`;
    },
    needsHeadings() {
      let { previousLine } = this;
      let previousLineIndex = this.lineIndex - 1;
      while (previousLine != null && previousLine.line_type === LINE_TYPES.STAGE_DIRECTION) {
        if (previousLineIndex === 0) {
          break;
        }
        previousLineIndex -= 1;
        previousLine = this.page[previousLineIndex];
      }

      const ret = [];
      this.line.line_parts.forEach(function checkLinePartNeedsHeading(part) {
        if (
          previousLine == null ||
          previousLine.line_parts.length !== this.line.line_parts.length
        ) {
          ret.push(true);
        } else {
          const matchingIndex = previousLine.line_parts.find(
            (prevPart) => prevPart.part_index === part.part_index
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
      }, this);
      return ret;
    },
    needsActSceneLabelSimple() {
      if (this.previousLine == null) {
        return true;
      }
      return !(
        this.previousLine.act_id === this.line.act_id &&
        this.previousLine.scene_id === this.line.scene_id
      );
    },
    stageDirectionStylingWithCuts() {
      if (this.line.stage_direction_style_id == null || this.stageDirectionStyle == null) {
        const style = {
          'background-color': 'darkslateblue',
          'font-style': 'italic',
        };
        if (this.linePartCuts.indexOf(this.line.line_parts[0].id) !== -1) {
          style['text-decoration'] = 'line-through';
        }
        return style;
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
      if (this.linePartCuts.indexOf(this.line.line_parts[0].id) !== -1) {
        style['text-decoration-line'] = `${style['text-decoration-line']} line-through`;
      }
      return style;
    },
    ...mapGetters(['IS_CUT_MODE']),
  },
  methods: {
    editLine() {
      this.$emit('editLine');
    },
    insertDialogue() {
      this.$emit('insertDialogue');
    },
    insertStageDirection() {
      this.$emit('insertStageDirection');
    },
    insertCueLine() {
      this.$emit('insertCueLine');
    },
    insertSpacing() {
      this.$emit('insertSpacing');
    },
    deleteLine() {
      this.$emit('deleteLine');
    },
    cutLinePart(partIndex) {
      if (partIndex < this.line.line_parts.length && this.line.line_parts[partIndex] != null) {
        const linePart = this.line.line_parts[partIndex];
        if (linePart.id != null && linePart.line_id != null) {
          this.$emit('cutLinePart', linePart.id);
          return;
        }
      }
      this.$toast.error('Unable to cut line part');
    },
  },
};
</script>

<style scoped>
.viewable-line {
  margin: 0;
}
.viewable-line-cut {
  margin: 0;
  cursor: pointer;
}
.stage-direction {
  margin-top: 1rem;
  margin-bottom: 1rem;
}
.heading-padding {
  margin-top: 0.5rem;
}
.cut-line-part {
  text-decoration: line-through;
}
.editing-indicator {
  transition: border-left 0.2s ease;
}
.editing-badge {
  display: block;
  font-size: 0.7rem;
  opacity: 0.8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: default;
}
</style>
