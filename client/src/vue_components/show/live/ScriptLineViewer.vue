<template>
  <b-container ref="lineContainer" class="mx-0" style="margin: 0; padding: 0" fluid v-once>
    <b-row v-if="needsActSceneLabel">
      <b-col cols="3" class="cue-column" />
      <b-col cols="9">
        <h4> {{ actLabel }} - {{ sceneLabel }}</h4>
      </b-col>
    </b-row>
    <b-row :class="{'stage-direction': line.stage_direction}">
      <b-col cols="3" class="cue-column">
        <b-button-group>
          <b-button v-for="cue in cues" :key="cue.id"
                    class="cue-button"
                    :style="{backgroundColor: cueBackgroundColour(cue),
                    color: contrastColor({'bgColor': cueBackgroundColour(cue)})}">
            {{ cueLabel(cue) }}
          </b-button>
        </b-button-group>
      </b-col>
      <template v-if="line.stage_direction">
        <b-col :key="`line_${lineIndex}_stage_direction`" style="text-align: center">
          <i class="viewable-line">{{ line.line_parts[0].line_text }}</i>
        </b-col>
      </template>
      <template v-else>
        <b-col v-for="(part, index) in line.line_parts"
             :key="`line_${lineIndex}_part_${index}`"
             style="text-align: center">
            <template v-if="needsHeadings[index]">
              <b v-if="part.character_id != null">
                {{ characters.find((char) => (char.id === part.character_id)).name }}
              </b>
              <b v-else>
                {{ characterGroups.find((char) => (char.id === part.character_group_id)).name }}
              </b>
            </template>
            <p class="viewable-line">
              {{ part.line_text }}
            </p>
        </b-col>
      </template>
    </b-row>
  </b-container>
</template>

<script>
import { contrastColor } from 'contrast-color';

export default {
  name: 'ScriptLineViewer',
  events: ['last-line-page', 'first-page'],
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
    cueTypes: {
      required: true,
    },
    cues: {
      required: true,
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
    onClassChange(classAttrValue) {
      const classList = classAttrValue.split(' ');
      if (classList.includes('last-script-element')) {
        this.$emit('last-line-page', this.line.page);
      }
      if (classList.includes('first-script-element')) {
        this.$emit('first-page', this.line.page);
      }
    },
    cueLabel(cue) {
      const cueType = this.cueTypes.find((cT) => (cT.id === cue.cue_type_id));
      return `${cueType.prefix} ${cue.ident}`;
    },
    cueBackgroundColour(cue) {
      return this.cueTypes.find((cueType) => (cueType.id === cue.cue_type_id)).colour;
    },
  },
  computed: {
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
</style>
