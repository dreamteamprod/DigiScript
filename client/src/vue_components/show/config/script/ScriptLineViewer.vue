<template>
  <b-row :class="{'stage-direction': line.stage_direction}">
    <b-col cols="1">
      <p v-if="needsActSceneLabel" class="viewable-line">
        {{ actLabel }}
      </p>
    </b-col>
    <b-col cols="1">
      <p v-if="needsActSceneLabel" class="viewable-line">
        {{ sceneLabel }}
      </p>
    </b-col>
    <template v-if="!line.stage_direction">
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
    <template v-else>
      <b-col :key="`line_${lineIndex}_stage_direction`" style="text-align: center">
        <i class="viewable-line">{{ line.line_parts[0].line_text }}</i>
      </b-col>
    </template>
    <b-col cols="1" align-self="end">
      <b-button v-show="canEdit" variant="link" style="padding: 0"
                @click.stop="editLine">
        Edit
      </b-button>
    </b-col>
  </b-row>
</template>

<script>
export default {
  name: 'ScriptLineViewer',
  events: ['editLine'],
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
    canEdit: {
      required: true,
      type: Boolean,
    },
  },
  methods: {
    editLine() {
      this.$emit('editLine');
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
.viewable-line {
  margin: 0;
}
.stage-direction {
  margin-top: 1rem;
  margin-bottom: 1rem;
}
</style>
