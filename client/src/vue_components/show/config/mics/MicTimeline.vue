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

<script lang="ts">
import { defineComponent } from 'vue';
import { mapGetters } from 'vuex';
import timelineMixin from '@/mixins/timelineMixin';

export default defineComponent({
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
      viewMode: 'mic',
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
    hasData(): boolean {
      return this.scenes.length > 0 && this.rows.length > 0;
    },
    scenes(): any[] {
      return (this as any).MIC_TIMELINE_DATA.scenes || [];
    },
    allocations(): Record<string, any> {
      return (this as any).MIC_TIMELINE_DATA.allocations || {};
    },
    microphones(): any[] {
      return (this as any).MIC_TIMELINE_DATA.microphones || [];
    },
    characters(): any[] {
      return (this as any).MIC_TIMELINE_DATA.characters || [];
    },
    rows(): any[] {
      if (this.viewMode === 'mic') {
        return this.microphones.map((mic: any) => ({
          id: mic.id,
          name: mic.name || `Mic ${mic.id}`,
          type: 'mic',
        }));
      }
      if (this.viewMode === 'character') {
        return this.characters
          .filter((char: any) => this.hasCharacterAllocations(char.id))
          .map((char: any) => ({
            id: char.id,
            name: char.name,
            type: 'character',
          }));
      }
      return ((this as any).CAST_LIST as any[])
        .filter((cast: any) => this.hasCastAllocations(cast.id))
        .map((cast: any) => ({
          id: cast.id,
          name: `${cast.first_name} ${cast.last_name}`.trim() || `Cast ${cast.id}`,
          type: 'cast',
        }));
    },
    allocationBars(): any[] {
      const bars: any[] = [];

      this.rows.forEach((row: any, rowIndex: number) => {
        if (this.viewMode === 'mic') {
          this.generateBarsForMic(row.id, rowIndex, bars);
        } else if (this.viewMode === 'character') {
          this.generateBarsForCharacter(row.id, rowIndex, bars);
        } else {
          this.generateBarsForCast(row.id, rowIndex, bars);
        }
      });

      return bars;
    },
  },
  watch: {
    viewMode(): void {
      this.$forceUpdate();
    },
  },
  methods: {
    hasCharacterAllocations(characterId: number): boolean {
      return Object.values(this.allocations).some((micAllocs) => {
        if (!Array.isArray(micAllocs)) return false;
        return (micAllocs as any[]).some((alloc) => alloc.character_id === characterId);
      });
    },
    hasCastAllocations(castId: number): boolean {
      const castCharacters = this.characters.filter((char: any) => char.cast_member?.id === castId);
      return castCharacters.some((char: any) => this.hasCharacterAllocations(char.id));
    },
    generateBarsForMic(micId: number, rowIndex: number, bars: any[]): void {
      const micAllocs = this.allocations[micId];
      if (!Array.isArray(micAllocs)) return;

      const segments: any[] = [];
      let currentSegment: any = null;

      this.scenes.forEach((scene: any, sceneIndex: number) => {
        const alloc = micAllocs.find((a: any) => a.scene_id === scene.id);
        const characterId = alloc?.character_id;

        if (characterId) {
          if (currentSegment && currentSegment.characterId === characterId) {
            currentSegment.endIndex = sceneIndex;
          } else {
            if (currentSegment) segments.push(currentSegment);
            currentSegment = {
              characterId,
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

      segments.forEach((segment: any, segmentIndex: number) => {
        const character = (this as any).CHARACTER_BY_ID(segment.characterId);
        const startX = (this as any).getSceneX(segment.startIndex);
        const width = (this as any).sceneWidth * (segment.endIndex - segment.startIndex + 1);

        bars.push({
          id: `mic-${micId}-seg-${segmentIndex}`,
          x: startX,
          y: (this as any).getRowY(rowIndex) + (this as any).barPadding,
          width,
          height: (this as any).rowHeight - 2 * (this as any).barPadding,
          color: (this as any).getColorForEntity(segment.characterId, 'character'),
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
    generateBarsForCharacter(characterId: number, rowIndex: number, bars: any[]): void {
      const segmentsByMic = new Map<number, any[]>();

      Object.keys(this.allocations).forEach((micId) => {
        const micAllocs = this.allocations[micId];
        if (!Array.isArray(micAllocs)) return;

        const segments: any[] = [];
        let currentSegment: any = null;

        this.scenes.forEach((scene: any, sceneIndex: number) => {
          const alloc = micAllocs.find(
            (a: any) => a.scene_id === scene.id && a.character_id === characterId
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

      const micIds = Array.from(segmentsByMic.keys());
      const barHeightPerMic =
        ((this as any).rowHeight - 2 * (this as any).barPadding) / Math.max(micIds.length, 1);

      micIds.forEach((micId: number, micIndex: number) => {
        const segments = segmentsByMic.get(micId)!;
        segments.forEach((segment: any, segmentIndex: number) => {
          const mic = (this as any).MICROPHONE_BY_ID(segment.micId);
          const startX = (this as any).getSceneX(segment.startIndex);
          const width = (this as any).sceneWidth * (segment.endIndex - segment.startIndex + 1);
          const yOffset = micIndex * barHeightPerMic;

          bars.push({
            id: `char-${characterId}-mic-${micId}-seg-${segmentIndex}`,
            x: startX,
            y: (this as any).getRowY(rowIndex) + (this as any).barPadding + yOffset,
            width,
            height: barHeightPerMic,
            color: (this as any).getColorForEntity(characterId, 'character'),
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
    generateBarsForCast(castId: number, rowIndex: number, bars: any[]): void {
      const castCharacters = this.characters.filter((char: any) => char.cast_member?.id === castId);

      const segmentsByMic = new Map<number, any[]>();

      Object.keys(this.allocations).forEach((micId) => {
        const micAllocs = this.allocations[micId];
        if (!Array.isArray(micAllocs)) return;

        const segments: any[] = [];
        let currentSegment: any = null;

        this.scenes.forEach((scene: any, sceneIndex: number) => {
          const alloc = micAllocs.find(
            (a: any) =>
              a.scene_id === scene.id &&
              castCharacters.some((char: any) => char.id === a.character_id)
          );

          if (alloc) {
            if (currentSegment && currentSegment.micId === parseInt(micId, 10)) {
              currentSegment.endIndex = sceneIndex;
              currentSegment.characterIds.add(alloc.character_id);
            } else {
              if (currentSegment) segments.push(currentSegment);
              currentSegment = {
                micId: parseInt(micId, 10),
                startIndex: sceneIndex,
                endIndex: sceneIndex,
                characterIds: new Set([alloc.character_id]),
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

      const micIds = Array.from(segmentsByMic.keys());
      const barHeightPerMic =
        ((this as any).rowHeight - 2 * (this as any).barPadding) / Math.max(micIds.length, 1);

      micIds.forEach((micId: number, micIndex: number) => {
        const segments = segmentsByMic.get(micId)!;
        segments.forEach((segment: any, segmentIndex: number) => {
          const mic = (this as any).MICROPHONE_BY_ID(segment.micId);
          const characterNames = Array.from(segment.characterIds as Set<number>)
            .map((charId) => (this as any).CHARACTER_BY_ID(charId)?.name || 'Unknown')
            .join(', ');
          const startX = (this as any).getSceneX(segment.startIndex);
          const width = (this as any).sceneWidth * (segment.endIndex - segment.startIndex + 1);
          const yOffset = micIndex * barHeightPerMic;

          bars.push({
            id: `cast-${castId}-mic-${micId}-seg-${segmentIndex}`,
            x: startX,
            y: (this as any).getRowY(rowIndex) + (this as any).barPadding + yOffset,
            width,
            height: barHeightPerMic,
            color: (this as any).getColorForEntity(castId, 'cast'),
            cssClass: '',
            label: mic?.name || `Mic ${segment.micId}`,
            tooltip: `${mic?.name || `Mic ${segment.micId}`} - ${characterNames} (Scenes ${segment.startIndex + 1}-${segment.endIndex + 1})`,
            data: {
              castId,
              micId: segment.micId,
              characterIds: Array.from(segment.characterIds as Set<number>),
              startScene: segment.startIndex,
              endScene: segment.endIndex,
            },
          });
        });
      });
    },
    handleExport(): void {
      const viewModeNames: Record<string, string> = {
        mic: 'Microphone',
        character: 'Character',
        cast: 'Cast',
      };
      (this as any).exportTimeline('mic-timeline', viewModeNames[this.viewMode]);
    },
    handleBarClick(bar: any): void {
      this.$emit('bar-click', bar.data);
    },
    handleBarHover(bar: any, event: Event): void {
      this.$emit('bar-hover', { bar: bar.data, event });
    },
    handleBarLeave(): void {
      this.$emit('bar-leave');
    },
  },
});
</script>

<style lang="scss">
@use '@/assets/styles/timeline';
</style>
