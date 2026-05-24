<template>
  <div class="timeline-container">
    <div v-if="!dataLoaded" class="text-center py-5">
      <BSpinner label="Loading timeline..." />
    </div>
    <div v-else class="timeline-wrapper">
      <div class="timeline-controls-bar">
        <span class="text-light small">Crew Assignments</span>
        <BButton size="sm" variant="outline-secondary" title="Export as PNG" @click="handleExport">
          <IMdiDownload />
        </BButton>
      </div>
      <div class="svg-container">
        <div v-if="!hasData" class="text-center py-5 text-muted">
          No crew assignments to display. Assign crew members to SET/STRIKE tasks in the Stage
          Manager tab.
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
                  :class="['assignment-bar', bar.cssClass]"
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
                  :style="{ fontSize: Math.min(11, (bar.width / bar.label.length) * 1.5) + 'px' }"
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
import type { TimelineRow } from '@/composables/useTimeline';
import { useTimeline } from '@/composables/useTimeline';
import { useStageStore } from '@/stores/stage';
import { useShowStore } from '@/stores/show';
import type { CrewAssignment } from '@/types/api/stage';

interface CrewBar {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
  label: string;
  tooltip: string;
  cssClass: string;
}

const stageStore = useStageStore();
const showStore = useShowStore();

const svgRef = ref<SVGSVGElement | null>(null);
const dataLoaded = ref(false);

const scenes = computed(() => showStore.orderedScenes);

const rows = computed((): TimelineRow[] =>
  stageStore.crewList
    .filter((c) => (stageStore.crewAssignmentsByCrew[c.id] ?? []).length > 0)
    .map(
      (c): TimelineRow => ({
        id: c.id,
        name: [c.first_name, c.last_name].filter(Boolean).join(' '),
        type: 'crew',
      })
    )
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
  exportTimeline,
} = useTimeline(scenes, rows);

const hasData = computed(() => scenes.value.length > 0 && rows.value.length > 0);

const sceneIndexMap = computed(() => Object.fromEntries(scenes.value.map((s, i) => [s.id, i])));

function detectHardConflicts(
  rowId: number,
  byScene: Record<number, Set<string>>
): Array<[string, 'hard']> {
  return Object.keys(byScene)
    .map(Number)
    .filter((sceneId) => byScene[sceneId].size >= 2)
    .map((sceneId) => [`${rowId}-${sceneId}`, 'hard'] as [string, 'hard']);
}

function detectSoftConflicts(
  rowId: number,
  byScene: Record<number, Set<string>>,
  existing: Record<string, 'hard' | 'soft'>
): Array<[string, 'soft']> {
  const assignedSceneIds = Object.keys(byScene).map(Number);
  const softKeys: Array<[string, 'soft']> = [];
  assignedSceneIds.forEach((sceneId) => {
    const sceneIndex = sceneIndexMap.value[sceneId];
    if (sceneIndex == null) return;
    const scene = scenes.value[sceneIndex];
    const nextScene = scenes.value[sceneIndex + 1];
    if (!nextScene || nextScene.act !== scene.act || !assignedSceneIds.includes(nextScene.id))
      return;
    const itemsA = byScene[sceneId];
    const itemsB = byScene[nextScene.id];
    const sameItems = itemsA.size === itemsB.size && [...itemsA].every((k) => itemsB.has(k));
    if (!sameItems) {
      const k1 = `${rowId}-${sceneId}`;
      const k2 = `${rowId}-${nextScene.id}`;
      if (!existing[k1]) softKeys.push([k1, 'soft']);
      if (!existing[k2]) softKeys.push([k2, 'soft']);
    }
  });
  return softKeys;
}

const conflicts = computed((): Record<string, 'hard' | 'soft'> => {
  const conflictMap: Record<string, 'hard' | 'soft'> = {};
  rows.value.forEach((row) => {
    const assignments: CrewAssignment[] = stageStore.crewAssignmentsByCrew[row.id] ?? [];
    const byScene: Record<number, Set<string>> = {};
    assignments.forEach((a) => {
      if (!byScene[a.scene_id]) byScene[a.scene_id] = new Set();
      byScene[a.scene_id].add(a.prop_id == null ? `scenery-${a.scenery_id}` : `prop-${a.prop_id}`);
    });
    detectHardConflicts(row.id, byScene).forEach(([k, v]) => {
      conflictMap[k] = v;
    });
    detectSoftConflicts(row.id, byScene, conflictMap).forEach(([k, v]) => {
      conflictMap[k] = v;
    });
  });
  return conflictMap;
});

function getItemName(assignment: CrewAssignment): string {
  if (assignment.prop_id != null) {
    return stageStore.propById(assignment.prop_id)?.name ?? `Prop ${assignment.prop_id}`;
  }
  return stageStore.sceneryById(assignment.scenery_id)?.name ?? `Scenery ${assignment.scenery_id}`;
}

function buildBarLabel(
  hasSet: boolean,
  hasStrike: boolean,
  itemName: string,
  sceneName: string | null
): { label: string; tooltip: string } {
  if (hasSet && hasStrike)
    return { label: `▲ ${itemName} ▼`, tooltip: `SET & STRIKE: ${itemName} (${sceneName})` };
  if (hasSet) return { label: `▲ ${itemName}`, tooltip: `SET: ${itemName} (${sceneName})` };
  return { label: `▼ ${itemName}`, tooltip: `STRIKE: ${itemName} (${sceneName})` };
}

function buildBarsForScene(
  rowId: number,
  rowIndex: number,
  sceneId: number,
  sceneIndex: number,
  itemGroups: Record<string, CrewAssignment[]>,
  availableHeight: number,
  cssClass: string,
  bars: CrewBar[]
): void {
  const scene = scenes.value[sceneIndex];
  const itemCount = Object.keys(itemGroups).length;
  const barHeight = availableHeight / itemCount;
  const sortedKeys = Object.keys(itemGroups).sort((a, b) =>
    getItemName(itemGroups[a][0]).localeCompare(getItemName(itemGroups[b][0]))
  );
  sortedKeys.forEach((itemKey, stackIndex) => {
    const group = itemGroups[itemKey];
    const representative = group[0];
    const itemName = getItemName(representative);
    const { label, tooltip } = buildBarLabel(
      group.some((a) => a.assignment_type === 'set'),
      group.some((a) => a.assignment_type === 'strike'),
      itemName,
      scene.name ?? null
    );
    const itemId =
      representative.prop_id == null ? (representative.scenery_id ?? 0) : representative.prop_id;
    bars.push({
      id: `crew-${rowId}-scene-${sceneId}-${stackIndex}`,
      x: getSceneX(sceneIndex),
      y: getRowY(rowIndex) + barPadding + stackIndex * barHeight,
      width: sceneWidth,
      height: barHeight,
      color: getColorForEntity(itemId, representative.prop_id == null ? 'scenery' : 'prop'),
      label,
      tooltip,
      cssClass,
    });
  });
}

const allocationBars = computed((): CrewBar[] => {
  const bars: CrewBar[] = [];
  rows.value.forEach((row, rowIndex) => {
    const assignments: CrewAssignment[] = stageStore.crewAssignmentsByCrew[row.id] ?? [];
    const byScene: Record<number, Record<string, CrewAssignment[]>> = {};
    assignments.forEach((a) => {
      if (!byScene[a.scene_id]) byScene[a.scene_id] = {};
      const itemKey = a.prop_id == null ? `scenery-${a.scenery_id}` : `prop-${a.prop_id}`;
      if (!byScene[a.scene_id][itemKey]) byScene[a.scene_id][itemKey] = [];
      byScene[a.scene_id][itemKey].push(a);
    });
    const availableHeight = rowHeight - 2 * barPadding;
    Object.entries(byScene).forEach(([sceneIdStr, itemGroups]) => {
      const sceneId = Number(sceneIdStr);
      const sceneIndex = sceneIndexMap.value[sceneId];
      if (sceneIndex == null) return;
      const conflictType = conflicts.value[`${row.id}-${sceneId}`];
      let cssClass = '';
      if (conflictType === 'hard') cssClass = 'conflict-hard';
      else if (conflictType === 'soft') cssClass = 'conflict-soft';
      buildBarsForScene(
        row.id,
        rowIndex,
        sceneId,
        sceneIndex,
        itemGroups,
        availableHeight,
        cssClass,
        bars
      );
    });
  });
  return bars;
});

function handleExport(): void {
  exportTimeline(svgRef, 'crew-timeline', 'Crew');
}

onMounted(async () => {
  await Promise.all([
    showStore.getActList(),
    showStore.getSceneList(),
    stageStore.getCrewList(),
    stageStore.getCrewAssignments(),
    stageStore.getPropsList(),
    stageStore.getSceneryList(),
    stageStore.getPropsAllocations(),
    stageStore.getSceneryAllocations(),
  ]);
  dataLoaded.value = true;
});
</script>

<style lang="scss" scoped>
@use '@/assets/styles/timeline';

.assignment-bar {
  cursor: default;
  stroke: #212529;
  stroke-width: 1px;
  transition: opacity 0.2s ease;

  &:hover {
    opacity: 0.85;
  }

  &.conflict-hard {
    stroke: #dc3545;
    stroke-width: 2px;
  }

  &.conflict-soft {
    stroke: #fd7e14;
    stroke-width: 2px;
    stroke-dasharray: 4 2;
  }
}
</style>
