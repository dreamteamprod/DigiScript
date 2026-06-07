<template>
  <div class="timeline-container">
    <div v-if="loading" class="text-center py-5">
      <b-spinner label="Loading timeline..." />
    </div>
    <div v-else class="timeline-wrapper">
      <div class="timeline-controls-bar">
        <b-button size="sm" variant="outline-secondary" title="Export as PNG" @click="handleExport">
          <b-icon-download />
        </b-button>
      </div>

      <div class="svg-container">
        <div v-if="!hasData" class="text-center py-5 text-muted">
          No character line data to display. Ensure the script has dialogue lines assigned to
          characters.
        </div>

        <svg v-else ref="svg" :width="totalWidth" :height="totalHeight" class="timeline-svg">
          <!-- Act labels -->
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

          <!-- Scene labels -->
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

            <g class="allocation-bars">
              <g v-for="bar in allocationBars" :key="bar.id">
                <rect
                  :x="bar.x"
                  :y="bar.y"
                  :width="bar.width"
                  :height="bar.height"
                  :fill="bar.color"
                  class="allocation-bar"
                >
                  <title>{{ bar.tooltip }}</title>
                </rect>
                <text
                  v-if="bar.width >= 30"
                  :x="bar.x + bar.width / 2"
                  :y="bar.y + bar.height / 2"
                  class="bar-label"
                  text-anchor="middle"
                  dominant-baseline="middle"
                  pointer-events="none"
                  :style="{
                    fontSize: Math.min(12, (bar.width / bar.label.length) * 1.5) + 'px',
                  }"
                >
                  {{ bar.label }}
                </text>
              </g>
            </g>

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
import { mapGetters, mapActions } from 'vuex';
import { makeURL } from '@/js/utils';
import log from 'loglevel';
import timelineMixin from '@/mixins/timelineMixin';
import type { Scene } from '@/types/api/show';

interface TimelineRow {
  id: number;
  name: string;
  type: string;
}

interface AllocationBar {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
  label: string;
  tooltip: string;
}

export default defineComponent({
  name: 'CharacterTimeline',
  mixins: [timelineMixin],
  data() {
    return {
      loading: true,
      characterStats: {} as Record<string, any>,
    };
  },
  computed: {
    ...mapGetters(['ORDERED_SCENES', 'CHARACTER_LIST']),
    hasData(): boolean {
      return (this as any).scenes.length > 0 && (this as any).rows.length > 0;
    },
    scenes(): Scene[] {
      return (this as any).ORDERED_SCENES || [];
    },
    rows(): TimelineRow[] {
      return ((this as any).CHARACTER_LIST as any[])
        .filter((char: any) => (this as any).hasAnyLines(char.id))
        .map((char: any) => ({
          id: char.id,
          name: char.name ?? `Char ${char.id}`,
          type: 'character',
        }));
    },
    allocationBars(): AllocationBar[] {
      const bars: AllocationBar[] = [];
      (this as any).rows.forEach((row: TimelineRow, rowIndex: number) => {
        const presenceEntries = (this as any).scenes
          .filter(
            (scene: Scene) => (this as any).getSceneLineCount(row.id, scene.act, scene.id) > 0
          )
          .map((scene: Scene) => ({ scene_id: scene.id }));

        const segments = (this as any).groupConsecutiveScenes(presenceEntries);
        const color = (this as any).getColorForEntity(row.id, 'character');

        segments.forEach((seg: any, segIdx: number) => {
          bars.push({
            id: `char-${row.id}-seg-${segIdx}`,
            x: (this as any).getSceneX(seg.startIndex),
            y: (this as any).getRowY(rowIndex) + (this as any).barPadding,
            width: (this as any).sceneWidth * (seg.endIndex - seg.startIndex + 1),
            height: (this as any).rowHeight - 2 * (this as any).barPadding,
            color,
            label: row.name,
            tooltip:
              seg.startScene === seg.endScene
                ? `${row.name} (${seg.startScene})`
                : `${row.name} (${seg.startScene} – ${seg.endScene})`,
          });
        });
      });
      return bars;
    },
  },
  async mounted(): Promise<void> {
    await Promise.all([
      (this as any).GET_ACT_LIST(),
      (this as any).GET_SCENE_LIST(),
      (this as any).GET_CHARACTER_LIST(),
    ]);
    await (this as any).getStats();
    this.loading = false;
  },
  methods: {
    ...mapActions(['GET_ACT_LIST', 'GET_SCENE_LIST', 'GET_CHARACTER_LIST']),
    hasAnyLines(characterId: number): boolean {
      const lineCounts = this.characterStats.line_counts;
      if (!lineCounts) return false;
      const charCounts = lineCounts[characterId];
      if (!charCounts) return false;
      return Object.values(charCounts).some((actCounts: any) =>
        Object.values(actCounts).some((count: any) => count > 0)
      );
    },
    getSceneLineCount(characterId: number, actId: number | null, sceneId: number): number {
      const lineCounts = this.characterStats.line_counts;
      if (!lineCounts) return 0;
      return lineCounts[characterId]?.[actId ?? '']?.[sceneId] ?? 0;
    },
    async getStats(): Promise<void> {
      const response = await fetch(`${makeURL('/api/v1/show/character/stats')}`);
      if (response.ok) {
        this.characterStats = await response.json();
      } else {
        log.error('Unable to get character stats!');
      }
    },
    handleExport(): void {
      (this as any).exportTimeline('character-timeline', 'Character');
    },
  },
});
</script>

<style lang="scss">
@use '@/assets/styles/timeline';
</style>
