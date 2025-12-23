<template>
  <div class="mic-timeline-container">
    <div
      v-if="loading"
      class="text-center py-5"
    >
      <b-spinner label="Loading timeline..." />
    </div>
    <div
      v-else
      class="timeline-wrapper"
    >
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

        <b-button
          size="sm"
          variant="outline-secondary"
          title="Export as PNG"
          @click="exportTimeline"
        >
          <b-icon-download />
        </b-button>
      </div>

      <!-- SVG Container - scrollable -->
      <div class="svg-container">
        <!-- No Data Message -->
        <div
          v-if="!hasData"
          class="text-center py-5 text-muted"
        >
          No allocation data to display for this view
        </div>

        <!-- SVG Timeline -->
        <svg
          v-else
          ref="svg"
          :width="totalWidth"
          :height="totalHeight"
          class="mic-timeline"
        >
          <!-- Act labels (top) -->
          <g
            class="act-labels"
            :transform="`translate(${margin.left},0)`"
          >
            <g
              v-for="actGroup in actGroups"
              :key="`act-${actGroup.actId}`"
            >
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
          <g
            class="scene-labels"
            :transform="`translate(${margin.left},${margin.top})`"
          >
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
              <g
                v-for="bar in allocationBars"
                :key="bar.id"
              >
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
                  :style="{ fontSize: Math.min(12, bar.width / bar.label.length * 1.5) + 'px' }"
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

export default {
  name: 'MicTimeline',
  props: {
    loading: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      viewMode: 'mic', // 'mic', 'character', or 'cast'
      margin: {
        top: 75, right: 20, bottom: 20, left: 150,
      },
      sceneWidth: 100,
      rowHeight: 50,
      barPadding: 6,
    };
  },
  computed: {
    ...mapGetters([
      'MIC_TIMELINE_DATA',
      'MICROPHONE_BY_ID',
      'CHARACTER_BY_ID',
      'ACT_BY_ID',
      'SCENE_BY_ID',
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
      return this.CAST_LIST
        .filter((cast) => this.hasCastAllocations(cast.id))
        .map((cast) => ({
          id: cast.id,
          name: `${cast.first_name} ${cast.last_name}`.trim() || `Cast ${cast.id}`,
          type: 'cast',
        }));
    },
    contentWidth() {
      return this.scenes.length * this.sceneWidth;
    },
    contentHeight() {
      return this.rows.length * this.rowHeight;
    },
    totalWidth() {
      return this.margin.left + this.contentWidth + this.margin.right;
    },
    totalHeight() {
      return this.margin.top + this.contentHeight + this.margin.bottom;
    },
    actGroups() {
      const groups = [];
      let currentAct = null;
      let startIndex = 0;

      this.scenes.forEach((scene, index) => {
        const act = this.ACT_BY_ID(scene.act);
        if (!act) return;

        if (currentAct !== act.id) {
          if (currentAct !== null) {
            groups.push({
              actId: currentAct,
              actName: this.ACT_BY_ID(currentAct)?.name || 'Unknown',
              startX: this.getSceneX(startIndex),
              width: this.getSceneX(index) - this.getSceneX(startIndex),
            });
          }
          currentAct = act.id;
          startIndex = index;
        }
      });

      // Push final group
      if (currentAct !== null) {
        groups.push({
          actId: currentAct,
          actName: this.ACT_BY_ID(currentAct)?.name || 'Unknown',
          startX: this.getSceneX(startIndex),
          width: this.getSceneX(this.scenes.length) - this.getSceneX(startIndex),
        });
      }

      return groups;
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
    getSceneX(sceneIndex) {
      return sceneIndex * this.sceneWidth;
    },
    getRowY(rowIndex) {
      return rowIndex * this.rowHeight;
    },
    getColorForEntity(entityId, entityType) {
      // Generate unique, consistent color for any entity (mic, character, or cast)
      // Use HSL color space for visually distinct colors

      // Use a prime number multiplier to spread IDs evenly across hue spectrum
      // Golden ratio angle (137.5°) provides optimal distribution
      const GOLDEN_RATIO_CONJUGATE = 137.508;

      // Different offsets for different entity types to avoid collisions
      const typeOffsets = {
        mic: 0,
        character: 120,
        cast: 240,
      };

      const offset = typeOffsets[entityType] || 0;
      const hue = (entityId * GOLDEN_RATIO_CONJUGATE + offset) % 360;

      // Use high saturation and medium lightness for vibrant, visible colors
      return `hsl(${hue}, 70%, 50%)`;
    },
    hasCharacterAllocations(characterId) {
      return Object.values(this.allocations).some((micAllocs) => {
        if (!Array.isArray(micAllocs)) return false;
        return micAllocs.some((alloc) => alloc.character_id === characterId);
      });
    },
    hasCastAllocations(castId) {
      // Check if any character played by this cast member has allocations
      const castCharacters = this.characters.filter(
        (char) => char.cast_member?.id === castId,
      );
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
      const segments = [];

      Object.keys(this.allocations).forEach((micId) => {
        const micAllocs = this.allocations[micId];
        if (!Array.isArray(micAllocs)) return;

        let currentSegment = null;

        this.scenes.forEach((scene, sceneIndex) => {
          const alloc = micAllocs.find((a) => a.scene_id === scene.id && a.character_id === characterId);

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
      });

      // Create bars
      segments.forEach((segment, segmentIndex) => {
        const mic = this.MICROPHONE_BY_ID(segment.micId);
        const startX = this.getSceneX(segment.startIndex);
        const width = this.sceneWidth * (segment.endIndex - segment.startIndex + 1);

        bars.push({
          id: `char-${characterId}-seg-${segmentIndex}`,
          x: startX,
          y: this.getRowY(rowIndex) + this.barPadding,
          width,
          height: this.rowHeight - 2 * this.barPadding,
          color: this.getColorForEntity(segment.micId, 'mic'),
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
    },
    generateBarsForCast(castId, rowIndex, bars) {
      // Find all characters played by this cast member
      const castCharacters = this.characters.filter(
        (char) => char.cast_member?.id === castId,
      );

      const segments = [];

      // For each mic, find allocations for any character played by this cast member
      Object.keys(this.allocations).forEach((micId) => {
        const micAllocs = this.allocations[micId];
        if (!Array.isArray(micAllocs)) return;

        let currentSegment = null;

        this.scenes.forEach((scene, sceneIndex) => {
          // Check if any of this cast member's characters uses this mic in this scene
          const alloc = micAllocs.find((a) => a.scene_id === scene.id
            && castCharacters.some((char) => char.id === a.character_id));

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
      });

      // Create bars
      segments.forEach((segment, segmentIndex) => {
        const mic = this.MICROPHONE_BY_ID(segment.micId);
        const characterNames = Array.from(segment.characterIds)
          .map((charId) => this.CHARACTER_BY_ID(charId)?.name || 'Unknown')
          .join(', ');
        const startX = this.getSceneX(segment.startIndex);
        const width = this.sceneWidth * (segment.endIndex - segment.startIndex + 1);

        bars.push({
          id: `cast-${castId}-seg-${segmentIndex}`,
          x: startX,
          y: this.getRowY(rowIndex) + this.barPadding,
          width,
          height: this.rowHeight - 2 * this.barPadding,
          color: this.getColorForEntity(segment.micId, 'mic'),
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
    },
    exportTimeline() {
      const svgElement = this.$refs.svg;
      if (!svgElement) return;

      // Create a clone of the SVG to avoid modifying the original
      const svgClone = svgElement.cloneNode(true);

      // Inline critical styles for export (for print-friendly output)
      // This is necessary because XMLSerializer doesn't preserve CSS from stylesheets

      // Style scene dividers (vertical grid lines)
      svgClone.querySelectorAll('.scene-divider').forEach((el) => {
        el.setAttribute('stroke', '#495057');
        el.setAttribute('stroke-width', '1');
        el.setAttribute('opacity', '0.4');
      });

      // Style row separators (horizontal grid lines)
      svgClone.querySelectorAll('.row-separator').forEach((el) => {
        el.setAttribute('stroke', '#495057');
        el.setAttribute('stroke-width', '1');
        el.setAttribute('opacity', '0.3');
      });

      // Style act headers and labels
      svgClone.querySelectorAll('.act-header').forEach((el) => {
        el.setAttribute('fill', '#e9ecef');
        el.setAttribute('stroke', '#495057');
        el.setAttribute('stroke-width', '1');
      });

      svgClone.querySelectorAll('.act-label').forEach((el) => {
        el.setAttribute('fill', '#212529');
        el.setAttribute('font-size', '14');
        el.setAttribute('font-weight', '600');
      });

      // Style scene labels
      svgClone.querySelectorAll('.scene-label').forEach((el) => {
        el.setAttribute('fill', '#495057');
        el.setAttribute('font-size', '11');
      });

      // Style row labels
      svgClone.querySelectorAll('.row-label').forEach((el) => {
        el.setAttribute('fill', '#212529');
        el.setAttribute('font-size', '12');
        el.setAttribute('font-weight', '500');
      });

      // Style allocation bars (keep their colors but add stroke)
      svgClone.querySelectorAll('.allocation-bar').forEach((el) => {
        el.setAttribute('stroke', '#212529');
        el.setAttribute('stroke-width', '1');
      });

      // Style bar labels
      svgClone.querySelectorAll('.bar-label').forEach((el) => {
        el.setAttribute('fill', '#ffffff');
        el.setAttribute('font-weight', '600');
        el.setAttribute('style', 'text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8)');
      });

      // Serialize the SVG to a string
      const serializer = new XMLSerializer();
      const svgString = serializer.serializeToString(svgClone);

      // Create a blob and download link
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const img = new Image();

      // Set canvas size to SVG size
      canvas.width = this.totalWidth;
      canvas.height = this.totalHeight;

      img.onload = () => {
        // Draw white background for print-friendly output
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Draw the SVG image
        ctx.drawImage(img, 0, 0);

        // Convert canvas to blob and download
        canvas.toBlob((blob) => {
          const url = URL.createObjectURL(blob);
          const link = document.createElement('a');

          // Determine view mode name for filename
          let viewModeName = 'Cast';
          if (this.viewMode === 'mic') {
            viewModeName = 'Microphone';
          } else if (this.viewMode === 'character') {
            viewModeName = 'Character';
          }

          link.download = `mic-timeline-${viewModeName}-${new Date().toISOString().slice(0, 10)}.png`;
          link.href = url;
          link.click();
          URL.revokeObjectURL(url);
        });
      };

      // Create a data URL from the SVG string
      const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
      const svgUrl = URL.createObjectURL(svgBlob);
      img.src = svgUrl;
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

<style scoped>
.mic-timeline-container {
  position: relative;
  background-color: var(--body-background);
  border: 1px solid #dee2e6;
  border-radius: 0.25rem;
  overflow: hidden;
  min-height: 400px;
  height: calc(100vh - 200px);
}

.timeline-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.timeline-controls-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  background-color: rgba(52, 58, 64, 0.95);
  border-bottom: 1px solid #6c757d;
  z-index: 10;
  flex-shrink: 0;
}

.svg-container {
  flex: 1;
  overflow: auto;
  position: relative;
  min-height: 0;
}

.mic-timeline {
  display: block;
  background-color: var(--body-background);
}

/* Scene dividers */
.scene-divider {
  stroke: #6c757d;
  stroke-width: 1;
  opacity: 0.6;
  shape-rendering: crispEdges;
}

/* Act labels */
.act-header {
  fill: #343a40;
  stroke: #6c757d;
  stroke-width: 1px;
}

.act-label {
  fill: #dee2e6;
  font-size: 14px;
  font-weight: 600;
  pointer-events: none;
  user-select: none;
}

/* Scene labels */
.scene-label {
  fill: #adb5bd;
  font-size: 11px;
  pointer-events: none;
  user-select: none;
}

/* Row labels */
.row-label {
  fill: #dee2e6;
  font-size: 12px;
  font-weight: 500;
  pointer-events: none;
  user-select: none;
}

/* Row separators */
.row-separator {
  stroke: #6c757d;
  stroke-width: 1px;
  opacity: 0.5;
}

/* Allocation bars */
.allocation-bar {
  stroke: #212529;
  stroke-width: 1px;
  cursor: pointer;
  transition: opacity 0.2s ease, stroke-width 0.2s ease;
}

.allocation-bar:hover {
  opacity: 0.8;
  stroke-width: 2px;
  stroke: #fff;
}

.bar-label {
  fill: #fff;
  font-size: 12px;
  font-weight: 600;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8);
  user-select: none;
}
</style>
