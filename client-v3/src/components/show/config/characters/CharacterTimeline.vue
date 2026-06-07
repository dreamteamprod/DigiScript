<template>
  <div class="timeline-container">
    <div v-if="loading" class="text-center py-5">
      <BSpinner label="Loading timeline..." />
    </div>
    <div v-else class="timeline-wrapper">
      <div class="timeline-controls-bar">
        <BButton
          v-b-tooltip.hover.top="'Export as PNG'"
          size="sm"
          variant="outline-secondary"
          @click="handleExport"
        >
          <IMdiDownload /> Export
        </BButton>
      </div>

      <div class="svg-container">
        <div v-if="!hasData" class="text-center py-5 text-muted">
          No character line data to display. Ensure the script has dialogue lines assigned to
          characters.
        </div>
        <svg v-else ref="svgRef" :width="totalWidth" :height="totalHeight" class="timeline-svg">
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

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import log from 'loglevel';
import { makeURL } from '@/js/utils';
import { useShowStore } from '@/stores/show';
import { useTimeline, type TimelineRow } from '@/composables/useTimeline';

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

type LineCounts = Record<string, Record<string, Record<string, number>>>;

const showStore = useShowStore();
const loading = ref(true);
const characterStats = ref<{ line_counts?: LineCounts }>({});
const svgRef = ref<SVGSVGElement | null>(null);

const scenes = computed(() => showStore.orderedScenes);

function getSceneLineCount(characterId: number, actId: number | null, sceneId: number): number {
  const lineCounts = characterStats.value.line_counts;
  if (!lineCounts) return 0;
  return lineCounts[characterId]?.[actId ?? '']?.[sceneId] ?? 0;
}

function hasAnyLines(characterId: number): boolean {
  const lineCounts = characterStats.value.line_counts;
  if (!lineCounts) return false;
  const charCounts = lineCounts[characterId];
  if (!charCounts) return false;
  return Object.values(charCounts).some((actCounts) =>
    Object.values(actCounts).some((count) => count > 0)
  );
}

const rows = computed((): TimelineRow[] =>
  showStore.characterList
    .filter((char) => hasAnyLines(char.id))
    .map((char) => ({ id: char.id, name: char.name ?? `Char ${char.id}`, type: 'character' }))
);

const {
  margin,
  sceneWidth,
  rowHeight,
  barPadding,
  contentWidth,
  contentHeight,
  totalWidth,
  totalHeight,
  actGroups,
  getSceneX,
  getRowY,
  getColorForEntity,
  groupConsecutiveScenes,
  exportTimeline,
} = useTimeline(scenes, rows);

const allocationBars = computed((): AllocationBar[] => {
  const bars: AllocationBar[] = [];
  rows.value.forEach((row, rowIndex) => {
    const presenceEntries = scenes.value
      .filter((scene) => getSceneLineCount(row.id, scene.act, scene.id) > 0)
      .map((scene): Record<string, unknown> => ({ scene_id: scene.id }));

    const segments = groupConsecutiveScenes(presenceEntries);
    const color = getColorForEntity(row.id, 'character');

    segments.forEach((seg, segIdx) => {
      bars.push({
        id: `char-${row.id}-seg-${segIdx}`,
        x: getSceneX(seg.startIndex),
        y: getRowY(rowIndex) + barPadding,
        width: sceneWidth * (seg.endIndex - seg.startIndex + 1),
        height: rowHeight - 2 * barPadding,
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
});

const hasData = computed(() => scenes.value.length > 0 && rows.value.length > 0);

function handleExport(): void {
  exportTimeline(svgRef, 'character-timeline', 'Character');
}

onMounted(async () => {
  await Promise.all([
    showStore.getActList(),
    showStore.getSceneList(),
    showStore.getCharacterList(),
  ]);
  const response = await fetch(makeURL('/api/v1/show/character/stats'));
  if (response.ok) {
    characterStats.value = await response.json();
  } else {
    log.error('Unable to get character stats!');
  }
  loading.value = false;
});
</script>

<style lang="scss">
@use '@/assets/styles/timeline';
</style>
