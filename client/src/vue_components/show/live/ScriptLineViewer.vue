<template>
  <b-container
    v-once
    ref="lineContainer"
    class="mx-0"
    style="margin: 0; padding: 0"
    fluid
  >
    <b-row v-if="needsActSceneLabel" class="act-scene">
      <b-col
        cols="2"
        class="cue-column text-right font-weight-bold cue"
      >
        <span>{{ actLabel }}</span>
      </b-col>
      <b-col class="line-part text-left font-weight-bold cue">
        <span>{{ sceneLabel }} </span>
      </b-col>
    </b-row>
    <b-row>
      <template v-for="cue in cues">
        <b-col
          cols="2"
          class="cue-column line-part text-right font-weight-bold cue"
          :style="{color: cueBackgroundColour(cue)}"
        >
          <span>
            {{ cuePrefix(cue) }}
          </span>
        </b-col>
        <b-col
          cols="10"
          class="line-part text-left font-weight-bold cue"
          :style="{color: cueBackgroundColour(cue)}"
        >
          <span>
            {{ cue.ident }}
          </span>
        </b-col>
      </template>
      <template v-if="line.stage_direction">
        <b-col cols="2" class="cue-column" />
        <b-col
          :key="`line_${lineIndex}_stage_direction`"
          class="line-part text-left"
        >
          <i
            class="viewable-line"
            style="background-color: darkslateblue"
          >{{ line.line_parts[0].line_text }}</i>
        </b-col>
      </template>
      <template v-else>
        <template
          v-for="(part, index) in line.line_parts"
          :key="`heading_${lineIndex}_part_${index}`"
        >
          <template v-if="characters.find((char) => (char.id === part.character_id)).name !== 'CUE' || part.line_text.replace(/\s/g, '')">
            <b-col cols="2" class="cue-column line-part text-right" :class="{'cut-line-part': cuts.indexOf(part.id) !== -1, 'line-part-a': lineIndex%2==0, 'line-part-b': lineIndex%2==1}">
              <p v-if="needsHeadings[index]">
                <template v-if="part.character_id != null">
                  {{ characters.find((char) => (char.id === part.character_id)).name }}
                </template>
                <template v-else>
                  {{ characterGroups.find((char) => (char.id === part.character_group_id)).name }}
                </template>
              </p>
            </b-col>
            <b-col cols="10" class="line-part text-left" :class="{'cut-line-part': cuts.indexOf(part.id) !== -1, 'line-part-a': lineIndex%2==0, 'line-part-b': lineIndex%2==1}">
              <p
                class="viewable-line"
              >
                {{ part.line_text }}
              </p>
            </b-col>
          </template>
        </template>
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
    cuePrefix(cue) {
      const cueType = this.cueTypes.find((cT) => (cT.id === cue.cue_type_id));
      return cueType.prefix;
    },
    cueLabel(cue) {
      return `${this.cuePrefix(cue)} ${cue.ident}`;
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
    ...mapGetters(['GET_SCRIPT_PAGE', 'SCRIPT_CUTS']),
  },
};
</script>
<style scoped>
  .cue-column {
    border-right: .1rem solid #3498db;
  }
  .cut-line-part {
    text-decoration: line-through;
  }
  .line-part {
    font-size: 1.5rem;
  }
  .cue {
    font-size: 2rem;
  }
  .line-part-a {
    color: white;
  }
  .line-part-b {
    color: gray;
  }
  .act-scene {
    color: #f401fe;
  }
</style>
