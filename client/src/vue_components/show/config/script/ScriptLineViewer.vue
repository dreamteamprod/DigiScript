<template>
  <b-row
    :class="{
      'stage-direction': line.stage_direction,
      'heading-padding': !line.stage_direction && needsHeadingsAll
    }"
  >
    <b-col cols="1">
      <p
        v-if="needsActSceneLabel"
        class="viewable-line"
      >
        {{ actLabel }}
      </p>
    </b-col>
    <b-col cols="1">
      <p
        v-if="needsActSceneLabel"
        class="viewable-line"
      >
        {{ sceneLabel }}
      </p>
    </b-col>
    <template v-if="!line.stage_direction">
      <b-col>
        <b-row v-if="needsHeadingsAny">
          <b-col
            v-for="(part, index) in line.line_parts"
            :key="`heading_${lineIndex}_part_${index}`"
            style="text-align: center"
          >
            <template v-if="needsHeadings[index]">
              <b>
                <template v-if="part.character_id != null">
                  {{ characters.find((char) => (char.id === part.character_id)).name }}
                </template>
                <template v-else>
                  {{ characterGroups.find((char) => (char.id === part.character_group_id)).name }}
                </template>
              </b>
            </template>
          </b-col>
        </b-row>
        <b-row>
          <b-col
            v-for="(part, index) in line.line_parts"
            :key="`line_${lineIndex}_part_${index}`"
            style="text-align: center"
          >
            <p
              v-if="(canEdit && !IS_CUT_MODE) || !canEdit"
              class="viewable-line"
              :class="{'cut-line-part': linePartCuts.indexOf(part.id) !== -1}"
            >
              {{ part.line_text }}
            </p>
            <a
              v-else
              class="viewable-line-cut"
              :class="{'cut-line-part': linePartCuts.indexOf(part.id) !== -1}"
              @click.stop="cutLinePart(index)"
            >
              {{ part.line_text }}
            </a>
          </b-col>
        </b-row>
      </b-col>
    </template>
    <template v-else>
      <b-col
        :key="`line_${lineIndex}_stage_direction`"
        style="text-align: center"
      >
        <i
          v-if="(canEdit && !IS_CUT_MODE) || !canEdit"
          class="viewable-line"
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
        <a
          v-else
          class="viewable-line-cut"
          :style="stageDirectionStyling"
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
    <b-col
      cols="1"
      align-self="end"
    >
      <b-button
        v-show="canEdit && !IS_CUT_MODE"
        variant="link"
        style="padding: 0"
        @click.capture.stop="editLine"
      >
        <template v-if="insertMode">
          Insert
        </template>
        <template v-else-if="insertSDMode">
          Insert Stage Direction
        </template>
        <template v-else>
          Edit
        </template>
      </b-button>
    </b-col>
  </b-row>
</template>

<script>
import { mapGetters } from 'vuex';

export default {
  name: 'ScriptLineViewer',
  events: ['editLine', 'cutLinePart', 'insertLine', 'insertStageDirection'],
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
    insertMode: {
      required: true,
      type: Boolean,
      default: false,
    },
    insertSDMode: {
      required: true,
      type: Boolean,
      default: false,
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
  computed: {
    needsHeadings() {
      let { previousLine } = this;
      let previousLineIndex = this.lineIndex - 1;
      while (previousLine != null && previousLine.stage_direction === true) {
        if (previousLineIndex === 0) {
          break;
        }
        previousLineIndex -= 1;
        previousLine = this.page[previousLineIndex];
      }

      const ret = [];
      this.line.line_parts.forEach(function checkLinePartNeedsHeading(part) {
        if (previousLine == null
          || previousLine.line_parts.length !== this.line.line_parts.length) {
          ret.push(true);
        } else {
          const matchingIndex = previousLine.line_parts.find((prevPart) => (
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
    needsHeadingsAll() {
      return this.needsHeadings.every((x) => (x === true));
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
      if (this.line.stage_direction) {
        return override ? override.settings : sdStyle;
      }
      return null;
    },
    stageDirectionStyling() {
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
      if (this.insertMode) {
        this.$emit('insertLine');
      } else if (this.insertSDMode) {
        this.$emit('insertStageDirection');
      } else {
        this.$emit('editLine');
      }
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
  margin-top: .5rem;
}
.cut-line-part {
  text-decoration: line-through;
}
</style>
