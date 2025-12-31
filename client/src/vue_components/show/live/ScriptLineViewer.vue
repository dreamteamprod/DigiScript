<template>
  <b-container
    v-once
    ref="lineContainer"
    class="mx-0"
    style="margin: 0; padding: 0"
    fluid
  >
    <b-row
      v-if="needsIntervalBanner"
      class="interval-header"
    >
      <template v-if="USER_SETTINGS.cue_position_right">
        <b-col
          cols="9"
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
          cols="3"
          class="cue-column-right d-flex align-items-center justify-content-center"
        >
          <b-button
            v-if="isScriptLeader"
            variant="primary"
            @click.stop="startInterval"
          >
            Start Interval
          </b-button>
        </b-col>
      </template>
      <template v-else>
        <b-col
          cols="3"
          class="cue-column d-flex align-items-center justify-content-center"
        >
          <b-button
            v-if="isScriptLeader"
            variant="primary"
            @click.stop="startInterval"
          >
            Start Interval
          </b-button>
        </b-col>
        <b-col
          cols="9"
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
      </template>
    </b-row>
    <b-row
      v-if="needsActSceneLabel"
      class="act-scene-header"
    >
      <template v-if="USER_SETTINGS.cue_position_right">
        <b-col cols="9">
          <h4> {{ actLabel }} - {{ sceneLabel }}</h4>
        </b-col>
        <b-col
          cols="3"
          class="cue-column-right"
        />
      </template>
      <template v-else>
        <b-col
          cols="3"
          class="cue-column"
        />
        <b-col cols="9">
          <h4> {{ actLabel }} - {{ sceneLabel }}</h4>
        </b-col>
      </template>
    </b-row>
    <b-row
      :class="{
        'stage-direction': line.stage_direction,
        'heading-padding': !line.stage_direction && needsHeadingsAll
      }"
    >
      <template v-if="USER_SETTINGS.cue_position_right">
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
                <b v-else>&nbsp;</b>
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
        <b-col
          cols="3"
          class="cue-column-right"
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
            <b-button
              v-if="cueAddMode"
              class="cue-button"
              :disabled="isWholeLineCut(line)"
              @click.stop="addNewCue"
            >
              <b-icon-plus-square-fill variant="success" />
            </b-button>
          </b-button-group>
        </b-col>
      </template>
      <template v-else>
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
            <b-button
              v-if="cueAddMode"
              class="cue-button"
              :disabled="isWholeLineCut(line)"
              @click.stop="addNewCue"
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
                <b v-else>&nbsp;</b>
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
      </template>
    </b-row>
  </b-container>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';
import cueDisplayMixin from '@/mixins/cueDisplayMixin';
import scriptNavigationMixin from '@/mixins/scriptNavigationMixin';
import scriptDisplayMixin from '@/mixins/scriptDisplayMixin';

export default {
  name: 'ScriptLineViewer',
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
  },
  computed: {
    needsHeadingsAny() {
      return this.needsHeadings.some((x) => (x === true));
    },
    needsHeadingsAll() {
      return this.needsHeadings.every((x) => (x === true));
    },
    ...mapGetters(['USER_SETTINGS']),
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

  .cue-column-right {
    border-left: .1rem solid #3498db;
    margin-top: -1rem;
    margin-bottom: -1rem;
    padding-top: 1rem;
    padding-bottom: 1rem;
  }
  .interval-banner {
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

  .current-line {
    background: #3498db54;
  }

  .interval-header, .act-scene-header {
    background: var(--body-background);
  }
  .interval-header {
    margin-top: 1rem;
    padding-bottom: 1rem;
  }
</style>
