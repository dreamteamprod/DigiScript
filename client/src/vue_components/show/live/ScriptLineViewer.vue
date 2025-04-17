<template>
  <b-container
    v-once
    ref="lineContainer"
    class="mx-0"
    style="margin: 0; padding: 0"
    fluid
  >
    <b-row v-if="needsActSceneLabel">
      <b-col
        cols="3"
        class="cue-column"
      />
      <b-col cols="9">
        <h4> {{ actLabel }} - {{ sceneLabel }}</h4>
      </b-col>
    </b-row>
    <b-row
      :class="{
        'stage-direction': line.stage_direction,
        'heading-padding': !line.stage_direction && needsHeadingsAll
      }"
    >
      <b-col
        cols="3"
        class="cue-column"
      >
        <b-button-group>
          <b-button
            v-for="cue in cues"
            :key="cue.id"
            class="cue-button"
            :style="{backgroundColor: cueBackgroundColour(cue),
                     color: contrastColor({'bgColor': cueBackgroundColour(cue)})}"
          >
            {{ cueLabel(cue) }}
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
                class="viewable-line"
                :class="{'cut-line-part': cuts.indexOf(part.id) !== -1}"
              >
                {{ part.line_text }}
              </p>
            </b-col>
          </b-row>
        </b-col>
      </template>
    </b-row>
  </b-container>
</template>

<script>
import { mapGetters } from 'vuex';
import { contrastColor } from 'contrast-color';

export default {
  name: 'ScriptLineViewer',
  events: ['last-line-change', 'first-line-change'],
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
    previousLineIndex: {
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
    cueTypes: {
      required: true,
    },
    cues: {
      required: true,
    },
    cuts: {
      required: true,
      type: Array,
    },
    stageDirectionStyles: {
      required: true,
      type: Array,
    },
  },
  data() {
    return {
      observer: null,
    };
  },
  mounted() {
    /* eslint-disable no-restricted-syntax */
    this.observer = new MutationObserver((mutations) => {
      for (const m of mutations) {
        const newValue = m.target.getAttribute(m.attributeName);
        this.$nextTick(() => {
          this.onClassChange(newValue, m.oldValue);
        });
      }
    });
    /* eslint-enable no-restricted-syntax */

    this.observer.observe(this.$refs.lineContainer, {
      attributes: true,
      attributeOldValue: true,
      attributeFilter: ['class'],
    });
  },
  destroyed() {
    this.observer.disconnect();
  },
  methods: {
    contrastColor,
    onClassChange(classAttrValue, oldClassAttrValue) {
      const classList = classAttrValue.split(' ');
      const oldClassList = oldClassAttrValue.split(' ');
      if (classList.includes('last-script-element') && !oldClassList.includes('last-script-element')) {
        this.$emit('last-line-change', this.line.page, this.lineIndex);
      }
      if (classList.includes('first-script-element') && !oldClassList.includes('first-script-element')) {
        let previousLine = null;
        if (this.previousLine != null) {
          previousLine = `page_${this.previousLine.page}_line_${this.previousLineIndex}`;
        }
        this.$emit('first-line-change', this.line.page, this.lineIndex, previousLine);
      }
    },
    cueLabel(cue) {
      const cueType = this.cueTypes.find((cT) => (cT.id === cue.cue_type_id));
      return `${cueType.prefix} ${cue.ident}`;
    },
    cueBackgroundColour(cue) {
      return this.cueTypes.find((cueType) => (cueType.id === cue.cue_type_id)).colour;
    },
    getPreviousLineForIndex(pageIndex, lineIndex) {
      if (lineIndex > 0) {
        return [lineIndex - 1, this.GET_SCRIPT_PAGE(pageIndex)[lineIndex - 1]];
      }
      let loopPageNo = pageIndex - 1;
      while (loopPageNo >= 1) {
        const loopPage = this.GET_SCRIPT_PAGE(loopPageNo);
        if (loopPage.length > 0) {
          return [loopPage.length - 1, loopPage[loopPage.length - 1]];
        }
        loopPageNo -= 1;
      }
      return [null, null];
    },
    isWholeLineCut(line) {
      return line.line_parts.every((linePart) => (this.SCRIPT_CUTS.includes(linePart.id)
          || linePart.line_text == null || linePart.line_text.trim().length === 0), this);
    },
  },
  computed: {
    needsHeadings() {
      let { previousLine, lineIndex } = this;
      while (previousLine != null && (previousLine.stage_direction === true
          || this.isWholeLineCut(previousLine))) {
        [lineIndex, previousLine] = this.getPreviousLineForIndex(previousLine.page, lineIndex);
      }

      const ret = [];
      this.line.line_parts.forEach(function (part) {
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
      if (this.line.stage_direction) {
        return sdStyle;
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
    ...mapGetters(['GET_SCRIPT_PAGE', 'SCRIPT_CUTS']),
  },
};
</script>

<style scoped>
  .cue-column {
    border-right: .1rem solid #3498db;
    margin-top: -1rem;
    margin-bottom: -1rem;
    padding-top: 1rem;
    padding-bottom: 1rem;
  }
  .cue-button {
    padding: .2rem;
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
