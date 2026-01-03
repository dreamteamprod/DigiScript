<template>
  <b-container
    v-once
    ref="lineContainer"
    class="mx-0"
    style="margin: 0; padding: 0"
    fluid
    :style="{paddingTop: spacingBefore + 'rem', '--spacing-before': spacingBefore + 'rem'}"
  >
    <b-row
      v-if="needsIntervalBanner"
      class="interval-header"
    >
      <b-col
        cols="12"
        class="interval-banner"
      >
        <b-alert
          show
          variant="warning"
          style="margin: 0"
        >
          <h3> {{ previousActLabel }} - Interval</h3>
        </b-alert>
      </b-col>
      <b-col
        v-if="isScriptLeader"
        cols="12"
        class="d-flex align-items-center justify-content-center"
        style="padding-top: 0.5rem; padding-bottom: 0.5rem;"
      >
        <b-button
          variant="primary"
          @click.stop="startInterval"
        >
          Start Interval
        </b-button>
      </b-col>
    </b-row>
    <b-row
      v-if="needsActSceneLabel"
      class="act-scene"
    >
      <b-col
        cols="2"
        :class="['cue-column', 'text-right', 'font-weight-bold', 'cue', {'first-row': isFirstRowActScene}]"
      >
        <span>{{ actLabel }}</span>
      </b-col>
      <b-col
        :cols="cueAddMode ? 9 : 10"
        class="line-part text-left font-weight-bold cue"
      >
        <span>{{ sceneLabel }}</span>
      </b-col>
      <b-col
        v-if="cueAddMode"
        cols="1"
        class="cue-add-column"
      />
    </b-row>
    <template v-for="(cue, cueIndex) in cues">
      <b-row :key="`cue_${cue.id}`">
        <b-col
          cols="2"
          :class="['cue-column', 'line-part', 'text-right', 'font-weight-bold', 'cue', {'first-row': isFirstRowCues && cueIndex === 0}]"
          :style="{color: cueBackgroundColour(cue)}"
        >
          <span>
            {{ cuePrefix(cue) }}
          </span>
        </b-col>
        <b-col
          :cols="cueAddMode ? 9 : 10"
          class="line-part text-left font-weight-bold cue"
          :style="{color: cueBackgroundColour(cue)}"
        >
          <span>
            {{ cue.ident }}
          </span>
        </b-col>
        <b-col
          v-if="cueAddMode"
          cols="1"
          class="cue-add-column"
        />
      </b-row>
    </template>
    <b-row>
      <template v-if="line.line_type === 2">
        <b-col
          cols="2"
          class="cue-column"
        />
        <b-col
          :key="`line_${lineIndex}_stage_direction`"
          :cols="cueAddMode ? 9 : 10"
          class="line-part text-left"
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
        <b-col
          v-if="cueAddMode"
          cols="1"
          class="cue-add-column d-flex align-items-center justify-content-center"
        >
          <b-button
            variant="success"
            size="sm"
            @click.stop="addNewCue"
          >
            <b-icon-plus-square-fill />
          </b-button>
        </b-col>
      </template>
      <template v-else-if="line.line_type === 3">
        <b-col
          cols="2"
          class="cue-column"
        />
        <b-col
          :key="`line_${lineIndex}_cue_line`"
          :cols="cueAddMode ? 9 : 10"
          class="line-part text-left"
        />
        <b-col
          v-if="cueAddMode"
          cols="1"
          class="cue-add-column d-flex align-items-center justify-content-center"
        >
          <b-button
            variant="success"
            size="sm"
            @click.stop="addNewCue"
          >
            <b-icon-plus-square-fill />
          </b-button>
        </b-col>
      </template>
      <template v-else-if="line.line_type === 1">
        <template
          v-for="(part, index) in line.line_parts"
        >
          <b-col
            :key="`char_${lineIndex}_part_${index}`"
            cols="2"
            class="cue-column line-part text-right"
            :class="{
              'cut-line-part': cuts.indexOf(part.id) !== -1,
              'line-part-a': lineIndex%2===0,
              'line-part-b': lineIndex%2===1,
              'first-row': isFirstRowContent && index === 0
            }"
          >
            <p v-if="needsHeadings[index]">
              <template v-if="part.character_id != null">
                {{ characters.find((char) => (char.id === part.character_id)).name }}
              </template>
              <template v-else>
                {{ characterGroups.find((char) => (char.id === part.character_group_id)).name }}
              </template>
            </p>
          </b-col>
          <b-col
            :key="`text_${lineIndex}_part_${index}`"
            :cols="cueAddMode ? 9 : 10"
            class="line-part text-left"
            :class="{
              'cut-line-part': cuts.indexOf(part.id) !== -1,
              'line-part-a': lineIndex%2===0,
              'line-part-b': lineIndex%2===1
            }"
          >
            <p class="viewable-line">
              {{ part.line_text }}
            </p>
          </b-col>
        </template>
        <b-col
          v-if="cueAddMode && !isWholeLineCut(line)"
          cols="1"
          class="cue-add-column d-flex align-items-center justify-content-center"
        >
          <b-button
            variant="success"
            size="sm"
            @click.stop="addNewCue"
          >
            <b-icon-plus-square-fill />
          </b-button>
        </b-col>
      </template>
    </b-row>
  </b-container>
</template>

<script>
import cueDisplayMixin from '@/mixins/cueDisplayMixin';
import scriptNavigationMixin from '@/mixins/scriptNavigationMixin';
import scriptDisplayMixin from '@/mixins/scriptDisplayMixin';

export default {
  name: 'ScriptLineViewerCompact',
  mixins: [cueDisplayMixin, scriptNavigationMixin, scriptDisplayMixin],
  events: ['last-line-change', 'first-line-change', 'start-interval'],
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
    previousLineIndex: {
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
    cueTypes: {
      required: true,
      type: Array,
    },
    cues: {
      required: true,
      type: Array,
    },
    cuts: {
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
    isScriptLeader: {
      required: true,
      type: Boolean,
    },
    cueAddMode: {
      required: true,
      type: Boolean,
    },
    spacingBefore: {
      required: false,
      type: Number,
      default: 0,
    },
  },
  computed: {
    isFirstRowActScene() {
      return this.needsActSceneLabel;
    },
    isFirstRowCues() {
      return !this.needsActSceneLabel && this.cues.length > 0;
    },
    isFirstRowContent() {
      return !this.needsActSceneLabel && this.cues.length === 0;
    },
  },
  methods: {
    addNewCue() {
      this.$emit('add-cue', this.line.id);
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

  .cue-column.first-row {
    margin-top: calc(-1rem - var(--spacing-before, 0rem));
    padding-top: calc(1rem + var(--spacing-before, 0rem));
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

  .current-line {
    background: #3498db54;
  }

  .interval-header {
    background: var(--body-background);
    margin-top: 1rem;
    padding-bottom: 1rem;
  }

  .interval-banner {
    margin-top: -1rem;
    margin-bottom: -1rem;
    padding-top: 1rem;
    padding-bottom: 1rem;
  }

  .cue-add-column {
    border-left: .1rem solid #3498db;
  }
</style>
