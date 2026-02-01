<template>
  <div class="timeline-container">
    <div v-if="loading" class="text-center py-5">
      <b-spinner label="Loading timeline..." />
    </div>
    <div v-else class="timeline-wrapper">
      <!-- Controls -->
      <div class="timeline-controls-bar">
        <b-button-group>
          <b-button
            :variant="viewMode === 'mic' ? 'primary' : 'outline-primary'"
            size="sm"
            @click="viewMode = 'mic'"
          >
            By Microphone
          </b-button>
          <b-button
            :variant="viewMode === 'character' ? 'primary' : 'outline-primary'"
            size="sm"
            @click="viewMode = 'character'"
          >
            By Character
          </b-button>
          <b-button
            :variant="viewMode === 'cast' ? 'primary' : 'outline-primary'"
            size="sm"
            @click="viewMode = 'cast'"
          >
            By Cast
          </b-button>
        </b-button-group>

        <b-button size="sm" variant="outline-secondary" title="Export as PNG" @click="handleExport">
          <b-icon-download />
        </b-button>
      </div>

      <!-- SVG Container - scrollable -->
      <div class="svg-container">
        <!-- No Data Message -->
        <div v-if="!hasData" class="text-center py-5 text-muted">
          No allocation data to display for this view
        </div>

        <!-- SVG Timeline -->
        <svg v-else ref="svg" :width="totalWidth" :height="totalHeight" class="timeline-svg">
          <!-- Act labels (top) -->
          <g class="act-labels" :transform="`translate(${margin.left},0)`">
            <g v-for="actGroup in actGroups" :key="`act-${actGroup.actId}`">
              <rect
                :x="actGroup.startX"
                :y="5"
                :width="actGroup.width"
                :height="25"
                class="act-header"
              />
              <text
                :x="actGroup.startX + actGroup.width / 2"
                :y="22"
                class="act-label"
                text-anchor="middle"
              >
                {{ actGroup.actName }}
              </text>
            </g>
          </g>

          <!-- Scene labels (below act labels) -->
          <g class="scene-labels" :transform="`translate(${margin.left},${margin.top})`">
            <text
              v-for="(scene, index) in scenes"
              :key="`scene-label-${scene.id}`"
              :x="getSceneX(index) + sceneWidth / 2"
              :y="-10"
              class="scene-label"
              text-anchor="middle"
            >
              {{ scene.name }}
            </text>
          </g>

          <!-- Main content group -->
          <g :transform="`translate(${margin.left},${margin.top})`">
            <!-- Scene dividers (vertical lines) -->
            <g class="scene-dividers">
              <line
                v-for="(scene, index) in scenes"
                :key="`divider-${scene.id}`"
                :x1="getSceneX(index)"
                :y1="0"
                :x2="getSceneX(index)"
                :y2="contentHeight"
                class="scene-divider"
              />
            </g>

            <!-- Allocation bars -->
            <g class="allocation-bars">
              <g v-for="bar in allocationBars" :key="bar.id">
                <rect
                  :x="bar.x"
                  :y="bar.y"
                  :width="bar.width"
                  :height="bar.height"
                  :fill="bar.color"
                  :class="bar.cssClass"
                  class="allocation-bar"
                  @click="handleBarClick(bar)"
                  @mouseenter="handleBarHover(bar, $event)"
                  @mouseleave="handleBarLeave()"
                />
                <title>{{ bar.tooltip }}</title>
                <!-- Bar label - only show if bar is wide enough -->
                <text
                  v-if="bar.width >= 30"
                  :x="bar.x + bar.width / 2"
                  :y="bar.y + bar.height / 2"
                  class="bar-label"
                  text-anchor="middle"
                  dominant-baseline="middle"
                  pointer-events="none"
                  :style="{ fontSize: Math.min(12, (bar.width / bar.label.length) * 1.5) + 'px' }"
                >
                  {{ bar.label }}
                </text>
              </g>
            </g>

            <!-- Row separators (horizontal lines) -->
            <g class="row-separators">
              <line
                v-for="(row, index) in rows"
                :key="`separator-${row.id}`"
                :x1="0"
                :y1="getRowY(index) + rowHeight"
                :x2="contentWidth"
                :y2="getRowY(index) + rowHeight"
                class="row-separator"
              />
            </g>

            <!-- Row labels (left side) -->
            <g class="row-labels">
              <text
                v-for="(row, index) in rows"
                :key="`row-label-${row.id}`"
                :x="-10"
                :y="getRowY(index) + rowHeight / 2"
                class="row-label"
                text-anchor="end"
                dominant-baseline="middle"
              >
                {{ row.name }}
              </text>
            </g>
          </g>
        </svg>
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import timelineMixin from '@/mixins/timelineMixin';

export default {
  name: 'MicTimeline',
  mixins: [timelineMixin],
  props: {
    loading: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      viewMode: 'mic', // 'mic', 'character', or 'cast'
    };
  },
  computed: {
    ...mapGetters([
      'MIC_TIMELINE_DATA',
      'MICROPHONE_BY_ID',
      'CHARACTER_BY_ID',
      'CAST_BY_ID',
      'CAST_LIST',
    ]),
    hasData() {
      return this.scenes.length > 0 && this.rows.length > 0;
    },
    scenes() {
      return this.MIC_TIMELINE_DATA.scenes || [];
    },
    allocations() {
      return this.MIC_TIMELINE_DATA.allocations || {};
    },
    microphones() {
      return this.MIC_TIMELINE_DATA.microphones || [];
    },
    characters() {
      return this.MIC_TIMELINE_DATA.characters || [];
    },
    rows() {
      if (this.viewMode === 'mic') {
        return this.microphones.map((mic) => ({
          id: mic.id,
          name: mic.name || `Mic ${mic.id}`,
          type: 'mic',
        }));
      }
      if (this.viewMode === 'character') {
        return this.characters
          .filter((char) => this.hasCharacterAllocations(char.id))
          .map((char) => ({
            id: char.id,
            name: char.name,
            type: 'character',
          }));
      }
      // Cast-centric view
      return this.CAST_LIST.filter((cast) => this.hasCastAllocations(cast.id)).map((cast) => ({
        id: cast.id,
        name: `${cast.first_name} ${cast.last_name}`.trim() || `Cast ${cast.id}`,
        type: 'cast',
      }));
    },
    allocationBars() {
      const bars = [];

      this.rows.forEach((row, rowIndex) => {
        if (this.viewMode === 'mic') {
          this.generateBarsForMic(row.id, rowIndex, bars);
        } else if (this.viewMode === 'character') {
          this.generateBarsForCharacter(row.id, rowIndex, bars);
        } else {
          // Cast view
          this.generateBarsForCast(row.id, rowIndex, bars);
        }
      });

      return bars;
    },
  },
  watch: {
    viewMode() {
      // Re-render when view mode changes
      this.$forceUpdate();
    },
  },
  methods: {
    hasCharacterAllocations(characterId) {
      return Object.values(this.allocations).some((micAllocs) => {
        if (!Array.isArray(micAllocs)) return false;
        return micAllocs.some((alloc) => alloc.character_id === characterId);
      });
    },
    hasCastAllocations(castId) {
      // Check if any character played by this cast member has allocations
      const castCharacters = this.characters.filter((char) => char.cast_member?.id === castId);
      return castCharacters.some((char) => this.hasCharacterAllocations(char.id));
    },
    generateBarsForMic(micId, rowIndex, bars) {
      const micAllocs = this.allocations[micId];
      if (!Array.isArray(micAllocs)) return;

      // Group consecutive scenes with same character
      const segments = [];
      let currentSegment = null;

      this.scenes.forEach((scene, sceneIndex) => {
        const alloc = micAllocs.find((a) => a.scene_id === scene.id);
        const characterId = alloc?.character_id;

        if (characterId) {
          if (currentSegment && currentSegment.characterId === characterId) {
            // Extend current segment
            currentSegment.endIndex = sceneIndex;
          } else {
            // Start new segment
            if (currentSegment) segments.push(currentSegment);
            currentSegment = {
              characterId,
              startIndex: sceneIndex,
              endIndex: sceneIndex,
            };
          }
        } else if (currentSegment) {
          // End current segment
          segments.push(currentSegment);
          currentSegment = null;
        }
      });

      // Push final segment
      if (currentSegment) segments.push(currentSegment);

      // Create bars for segments
      segments.forEach((segment, segmentIndex) => {
        const character = this.CHARACTER_BY_ID(segment.characterId);
        const startX = this.getSceneX(segment.startIndex);
        const width = this.sceneWidth * (segment.endIndex - segment.startIndex + 1);

        bars.push({
          id: `mic-${micId}-seg-${segmentIndex}`,
          x: startX,
          y: this.getRowY(rowIndex) + this.barPadding,
          width,
          height: this.rowHeight - 2 * this.barPadding,
          color: this.getColorForEntity(segment.characterId, 'character'),
          cssClass: '',
          label: character?.name || 'Unknown',
          tooltip: `${character?.name || 'Unknown'} (Scenes ${segment.startIndex + 1}-${segment.endIndex + 1})`,
          data: {
            micId,
            characterId: segment.characterId,
            startScene: segment.startIndex,
            endScene: segment.endIndex,
          },
        });
      });
    },
    generateBarsForCharacter(characterId, rowIndex, bars) {
      // Find all mics allocated to this character
      const segmentsByMic = new Map();

      Object.keys(this.allocations).forEach((micId) => {
        const micAllocs = this.allocations[micId];
        if (!Array.isArray(micAllocs)) return;

        const segments = [];
        let currentSegment = null;

        this.scenes.forEach((scene, sceneIndex) => {
          const alloc = micAllocs.find(
            (a) => a.scene_id === scene.id && a.character_id === characterId
          );

          if (alloc) {
            if (currentSegment && currentSegment.micId === parseInt(micId, 10)) {
              currentSegment.endIndex = sceneIndex;
            } else {
              if (currentSegment) segments.push(currentSegment);
              currentSegment = {
                micId: parseInt(micId, 10),
                startIndex: sceneIndex,
                endIndex: sceneIndex,
              };
            }
          } else if (currentSegment) {
            segments.push(currentSegment);
            currentSegment = null;
          }
        });

        if (currentSegment) segments.push(currentSegment);

        if (segments.length > 0) {
          segmentsByMic.set(parseInt(micId, 10), segments);
        }
      });

      // Create bars with vertical stacking for multiple mics
      const micIds = Array.from(segmentsByMic.keys());
      const barHeightPerMic = (this.rowHeight - 2 * this.barPadding) / Math.max(micIds.length, 1);

      micIds.forEach((micId, micIndex) => {
        const segments = segmentsByMic.get(micId);
        segments.forEach((segment, segmentIndex) => {
          const mic = this.MICROPHONE_BY_ID(segment.micId);
          const startX = this.getSceneX(segment.startIndex);
          const width = this.sceneWidth * (segment.endIndex - segment.startIndex + 1);
          const yOffset = micIndex * barHeightPerMic;

          bars.push({
            id: `char-${characterId}-mic-${micId}-seg-${segmentIndex}`,
            x: startX,
            y: this.getRowY(rowIndex) + this.barPadding + yOffset,
            width,
            height: barHeightPerMic,
            color: this.getColorForEntity(characterId, 'character'),
            cssClass: '',
            label: mic?.name || `Mic ${segment.micId}`,
            tooltip: `${mic?.name || `Mic ${segment.micId}`} (Scenes ${segment.startIndex + 1}-${segment.endIndex + 1})`,
            data: {
              characterId,
              micId: segment.micId,
              startScene: segment.startIndex,
              endScene: segment.endIndex,
            },
          });
        });
      });
    },
    generateBarsForCast(castId, rowIndex, bars) {
      // Find all characters played by this cast member
      const castCharacters = this.characters.filter((char) => char.cast_member?.id === castId);

      const segmentsByMic = new Map();

      // For each mic, find allocations for any character played by this cast member
      Object.keys(this.allocations).forEach((micId) => {
        const micAllocs = this.allocations[micId];
        if (!Array.isArray(micAllocs)) return;

        const segments = [];
        let currentSegment = null;

        this.scenes.forEach((scene, sceneIndex) => {
          // Check if any of this cast member's characters uses this mic in this scene
          const alloc = micAllocs.find(
            (a) =>
              a.scene_id === scene.id && castCharacters.some((char) => char.id === a.character_id)
          );

          if (alloc) {
            if (currentSegment && currentSegment.micId === parseInt(micId, 10)) {
              // Extend current segment
              currentSegment.endIndex = sceneIndex;
              currentSegment.characterIds.add(alloc.character_id);
            } else {
              // Start new segment
              if (currentSegment) segments.push(currentSegment);
              currentSegment = {
                micId: parseInt(micId, 10),
                startIndex: sceneIndex,
                endIndex: sceneIndex,
                characterIds: new Set([alloc.character_id]),
              };
            }
          } else if (currentSegment) {
            // End current segment
            segments.push(currentSegment);
            currentSegment = null;
          }
        });

        if (currentSegment) segments.push(currentSegment);

        if (segments.length > 0) {
          segmentsByMic.set(parseInt(micId, 10), segments);
        }
      });

      // Create bars with vertical stacking for multiple mics
      const micIds = Array.from(segmentsByMic.keys());
      const barHeightPerMic = (this.rowHeight - 2 * this.barPadding) / Math.max(micIds.length, 1);

      micIds.forEach((micId, micIndex) => {
        const segments = segmentsByMic.get(micId);
        segments.forEach((segment, segmentIndex) => {
          const mic = this.MICROPHONE_BY_ID(segment.micId);
          const characterNames = Array.from(segment.characterIds)
            .map((charId) => this.CHARACTER_BY_ID(charId)?.name || 'Unknown')
            .join(', ');
          const startX = this.getSceneX(segment.startIndex);
          const width = this.sceneWidth * (segment.endIndex - segment.startIndex + 1);
          const yOffset = micIndex * barHeightPerMic;

          bars.push({
            id: `cast-${castId}-mic-${micId}-seg-${segmentIndex}`,
            x: startX,
            y: this.getRowY(rowIndex) + this.barPadding + yOffset,
            width,
            height: barHeightPerMic,
            color: this.getColorForEntity(castId, 'cast'),
            cssClass: '',
            label: mic?.name || `Mic ${segment.micId}`,
            tooltip: `${mic?.name || `Mic ${segment.micId}`} - ${characterNames} (Scenes ${segment.startIndex + 1}-${segment.endIndex + 1})`,
            data: {
              castId,
              micId: segment.micId,
              characterIds: Array.from(segment.characterIds),
              startScene: segment.startIndex,
              endScene: segment.endIndex,
            },
          });
        });
      });
    },
    handleExport() {
      const viewModeNames = {
        mic: 'Microphone',
        character: 'Character',
        cast: 'Cast',
      };
      this.exportTimeline('mic-timeline', viewModeNames[this.viewMode]);
    },
    handleBarClick(bar) {
      this.$emit('bar-click', bar.data);
    },
    handleBarHover(bar, event) {
      this.$emit('bar-hover', { bar: bar.data, event });
    },
    handleBarLeave() {
      this.$emit('bar-leave');
    },
  },
};
</script>

<style lang="scss">
@use '@/assets/styles/timeline';
</style>
