<template>
  <div class="timeline-container">
    <div v-if="!dataLoaded" class="text-center py-5">
      <BSpinner label="Loading timeline..." />
    </div>
    <div v-else class="timeline-with-panel">
      <div class="timeline-wrapper">
        <div class="timeline-controls-bar">
          <BButtonGroup>
            <BButton
              :variant="viewMode === 'combined' ? 'primary' : 'outline-primary'"
              size="sm"
              @click="viewMode = 'combined'"
            >
              Combined
            </BButton>
            <BButton
              :variant="viewMode === 'props' ? 'primary' : 'outline-primary'"
              size="sm"
              @click="viewMode = 'props'"
            >
              Props
            </BButton>
            <BButton
              :variant="viewMode === 'scenery' ? 'primary' : 'outline-primary'"
              size="sm"
              @click="viewMode = 'scenery'"
            >
              Scenery
            </BButton>
          </BButtonGroup>
          <BButton
            size="sm"
            variant="outline-secondary"
            title="Export as PNG"
            @click="handleExport"
          >
            &#8659;
          </BButton>
        </div>
        <div class="svg-container">
          <div v-if="!hasData" class="text-center py-5 text-muted">
            No allocation data to display for this view
          </div>
          <svg v-else ref="svgRef" :width="totalWidth" :height="totalHeight" class="timeline-svg">
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
                    :class="['allocation-bar', { selected: isBarSelected(bar) }]"
                    @click="handleBarClick(bar)"
                  />
                  <title>{{ bar.tooltip }}</title>
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
      <TimelineSidePanel
        :selected-item="selectedItem"
        :is-open="sidePanelOpen"
        @close="closeSidePanel"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import type { TimelineRow } from '@/composables/useTimeline';
import { useTimeline } from '@/composables/useTimeline';
import { useStageStore } from '@/stores/stage';
import { useShowStore } from '@/stores/show';
import TimelineSidePanel from './TimelineSidePanel.vue';

interface BarData {
  type: 'prop' | 'scenery';
  itemId: number;
  startScene: number;
  endScene: number;
}

interface TimelineBar {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
  label: string;
  tooltip: string;
  data: BarData;
}

const stageStore = useStageStore();
const showStore = useShowStore();

const svgRef = ref<SVGSVGElement | null>(null);
const dataLoaded = ref(false);
const viewMode = ref<'combined' | 'props' | 'scenery'>('combined');
const selectedItem = ref<BarData | null>(null);
const sidePanelOpen = ref(false);

const scenes = computed(() => showStore.orderedScenes);

const rows = computed((): TimelineRow[] => {
  const propRows = stageStore.propsList
    .filter((p) => (stageStore.propsAllocationsByItem[p.id] ?? []).length > 0)
    .map((p): TimelineRow => ({ id: p.id, name: p.name, type: 'prop' }));

  const sceneryRows = stageStore.sceneryList
    .filter((s) => (stageStore.sceneryAllocationsByItem[s.id] ?? []).length > 0)
    .map((s): TimelineRow => ({ id: s.id, name: s.name, type: 'scenery' }));

  if (viewMode.value === 'props') return propRows;
  if (viewMode.value === 'scenery') return sceneryRows;
  return [...propRows, ...sceneryRows];
});

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

const hasData = computed(() => scenes.value.length > 0 && rows.value.length > 0);

const allocationBars = computed((): TimelineBar[] => {
  const bars: TimelineBar[] = [];
  rows.value.forEach((row, rowIndex) => {
    const allocations =
      row.type === 'prop'
        ? (stageStore.propsAllocationsByItem[row.id] ?? [])
        : (stageStore.sceneryAllocationsByItem[row.id] ?? []);

    const segments = groupConsecutiveScenes(
      allocations as Array<Record<string, unknown>>,
      'scene_id'
    );

    segments.forEach((segment, idx) => {
      const startX = getSceneX(segment.startIndex);
      const width = sceneWidth * (segment.endIndex - segment.startIndex + 1);
      const sceneRange =
        segment.startScene === segment.endScene
          ? segment.startScene
          : `${segment.startScene} - ${segment.endScene}`;

      bars.push({
        id: `${row.type}-${row.id}-seg-${idx}`,
        x: startX,
        y: getRowY(rowIndex) + barPadding,
        width,
        height: rowHeight - 2 * barPadding,
        color: getColorForEntity(row.id, row.type),
        label: row.name,
        tooltip: `${row.name} (${sceneRange})`,
        data: {
          type: row.type as 'prop' | 'scenery',
          itemId: row.id,
          startScene: segment.startIndex,
          endScene: segment.endIndex,
        },
      });
    });
  });
  return bars;
});

function isBarSelected(bar: TimelineBar): boolean {
  if (!selectedItem.value) return false;
  return (
    selectedItem.value.type === bar.data.type &&
    selectedItem.value.itemId === bar.data.itemId &&
    selectedItem.value.startScene === bar.data.startScene &&
    selectedItem.value.endScene === bar.data.endScene
  );
}

function handleBarClick(bar: TimelineBar): void {
  selectedItem.value = bar.data;
  sidePanelOpen.value = true;
}

function closeSidePanel(): void {
  sidePanelOpen.value = false;
  selectedItem.value = null;
}

function handleExport(): void {
  const modeNames: Record<string, string> = {
    combined: 'Combined',
    props: 'Props',
    scenery: 'Scenery',
  };
  exportTimeline(svgRef, 'stage-timeline', modeNames[viewMode.value]);
}

onMounted(async () => {
  await Promise.all([
    showStore.getActList(),
    showStore.getSceneList(),
    stageStore.getPropTypes(),
    stageStore.getSceneryTypes(),
    stageStore.getPropsList(),
    stageStore.getSceneryList(),
    stageStore.getPropsAllocations(),
    stageStore.getSceneryAllocations(),
    stageStore.getCrewList(),
    stageStore.getCrewAssignments(),
  ]);
  dataLoaded.value = true;
});
</script>

<style lang="scss">
@use '@/assets/styles/timeline';

.timeline-with-panel {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.timeline-wrapper {
  flex: 1;
  overflow: auto;
  min-width: 0;
}

.allocation-bar {
  cursor: pointer;
  transition: stroke-width 0.15s ease;

  &.selected {
    stroke: #212529;
    stroke-width: 3px;
  }

  &:hover:not(.selected) {
    stroke: #495057;
    stroke-width: 2px;
  }
}
</style>
