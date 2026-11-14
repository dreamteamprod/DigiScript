<template>
  <div class="timeline-container">
    <div v-if="loading" class="text-center py-5">
      <BSpinner label="Loading timeline..." />
    </div>
    <div v-else class="timeline-wrapper">
      <div class="timeline-controls-bar">
        <BButtonGroup>
          <BButton
            :variant="viewMode === 'mic' ? 'primary' : 'outline-primary'"
            size="sm"
            @click="viewMode = 'mic'"
          >
            By Microphone
          </BButton>
          <BButton
            :variant="viewMode === 'character' ? 'primary' : 'outline-primary'"
            size="sm"
            @click="viewMode = 'character'"
          >
            By Character
          </BButton>
          <BButton
            :variant="viewMode === 'cast' ? 'primary' : 'outline-primary'"
            size="sm"
            @click="viewMode = 'cast'"
          >
            By Cast
          </BButton>
        </BButtonGroup>
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
          No allocation data to display for this view
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
import { ref, computed } from 'vue';
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

withDefaults(defineProps<{ loading?: boolean }>(), { loading: false });

const showStore = useShowStore();
const viewMode = ref<'mic' | 'character' | 'cast'>('mic');
const svgRef = ref<SVGSVGElement | null>(null);

const timelineData = computed(() => showStore.micTimelineData);
const scenes = computed(() => timelineData.value.scenes);
const allocations = computed(() => timelineData.value.allocations);
const microphones = computed(() => timelineData.value.microphones);
const characters = computed(() => timelineData.value.characters);

function hasCharacterAllocations(characterId: number): boolean {
  return Object.values(allocations.value).some(
    (micAllocs) => Array.isArray(micAllocs) && micAllocs.some((a) => a.character_id === characterId)
  );
}

function hasCastAllocations(castId: number): boolean {
  return characters.value
    .filter((c) => c.cast_member?.id === castId)
    .some((c) => hasCharacterAllocations(c.id));
}

const rows = computed((): TimelineRow[] => {
  if (viewMode.value === 'mic') {
    return microphones.value.map((mic) => ({
      id: mic.id,
      name: mic.name ?? `Mic ${mic.id}`,
      type: 'mic',
    }));
  }
  if (viewMode.value === 'character') {
    return characters.value
      .filter((char) => hasCharacterAllocations(char.id))
      .map((char) => ({ id: char.id, name: char.name ?? `Char ${char.id}`, type: 'character' }));
  }
  return showStore.castList
    .filter((cast) => hasCastAllocations(cast.id))
    .map((cast) => ({
      id: cast.id,
      name: `${cast.first_name ?? ''} ${cast.last_name ?? ''}`.trim() || `Cast ${cast.id}`,
      type: 'cast',
    }));
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
  exportTimeline,
} = useTimeline(scenes, rows);

const hasData = computed(() => scenes.value.length > 0 && rows.value.length > 0);

function generateBarsForMic(micId: number, rowIndex: number, bars: AllocationBar[]): void {
  const micAllocs = allocations.value[micId];
  if (!Array.isArray(micAllocs)) return;

  const segments: { characterId: number; startIndex: number; endIndex: number }[] = [];
  let current: (typeof segments)[0] | null = null;

  scenes.value.forEach((scene, idx) => {
    const charId = micAllocs.find((a) => a.scene_id === scene.id)?.character_id;
    if (charId) {
      if (current && current.characterId === charId) {
        current.endIndex = idx;
      } else {
        if (current) segments.push(current);
        current = { characterId: charId, startIndex: idx, endIndex: idx };
      }
    } else if (current) {
      segments.push(current);
      current = null;
    }
  });
  if (current) segments.push(current);

  segments.forEach((seg, segIdx) => {
    const char = showStore.characterById(seg.characterId);
    bars.push({
      id: `mic-${micId}-seg-${segIdx}`,
      x: getSceneX(seg.startIndex),
      y: getRowY(rowIndex) + barPadding,
      width: sceneWidth * (seg.endIndex - seg.startIndex + 1),
      height: rowHeight - 2 * barPadding,
      color: getColorForEntity(seg.characterId, 'character'),
      label: char?.name ?? 'Unknown',
      tooltip: `${char?.name ?? 'Unknown'} (Scenes ${seg.startIndex + 1}–${seg.endIndex + 1})`,
    });
  });
}

function generateBarsForCharacter(
  characterId: number,
  rowIndex: number,
  bars: AllocationBar[]
): void {
  type Seg = { micId: number; startIndex: number; endIndex: number };
  const segmentsByMic = new Map<number, Seg[]>();

  Object.keys(allocations.value).forEach((micId) => {
    const micAllocs = allocations.value[micId];
    if (!Array.isArray(micAllocs)) return;
    const micIdNum = Number.parseInt(micId, 10);
    const segments: Seg[] = [];
    let current: Seg | null = null;

    scenes.value.forEach((scene, idx) => {
      const alloc = micAllocs.find(
        (a) => a.scene_id === scene.id && a.character_id === characterId
      );
      if (alloc) {
        if (current && current.micId === micIdNum) {
          current.endIndex = idx;
        } else {
          if (current) segments.push(current);
          current = { micId: micIdNum, startIndex: idx, endIndex: idx };
        }
      } else if (current) {
        segments.push(current);
        current = null;
      }
    });
    if (current) segments.push(current);
    if (segments.length > 0) segmentsByMic.set(micIdNum, segments);
  });

  const micIds = Array.from(segmentsByMic.keys());
  const barH = (rowHeight - 2 * barPadding) / Math.max(micIds.length, 1);

  micIds.forEach((micId, micIdx) => {
    segmentsByMic.get(micId)!.forEach((seg, segIdx) => {
      bars.push(
        buildMicBar(
          `char-${characterId}-mic-${micId}-seg-${segIdx}`,
          seg.startIndex,
          seg.endIndex,
          getRowY(rowIndex) + barPadding + micIdx * barH,
          barH,
          getColorForEntity(characterId, 'character'),
          seg.micId
        )
      );
    });
  });
}

function buildMicBar(
  id: string,
  startIndex: number,
  endIndex: number,
  yPos: number,
  barH: number,
  color: string,
  micId: number
): AllocationBar {
  const mic = showStore.microphoneById(micId);
  const micName = mic?.name ?? `Mic ${micId}`;
  return {
    id,
    x: getSceneX(startIndex),
    y: yPos,
    width: sceneWidth * (endIndex - startIndex + 1),
    height: barH,
    color,
    label: micName,
    tooltip: `${micName} (Scenes ${startIndex + 1}–${endIndex + 1})`,
  };
}

function generateBarsForCast(castId: number, rowIndex: number, bars: AllocationBar[]): void {
  const castChars = characters.value.filter((c) => c.cast_member?.id === castId);
  type Seg = { micId: number; startIndex: number; endIndex: number; charIds: Set<number> };
  const segmentsByMic = new Map<number, Seg[]>();

  Object.keys(allocations.value).forEach((micId) => {
    const micAllocs = allocations.value[micId];
    if (!Array.isArray(micAllocs)) return;
    const micIdNum = Number.parseInt(micId, 10);
    const segments: Seg[] = [];
    let current: Seg | null = null;

    scenes.value.forEach((scene, idx) => {
      const alloc = micAllocs.find(
        (a) => a.scene_id === scene.id && castChars.some((c) => c.id === a.character_id)
      );
      if (alloc) {
        if (current && current.micId === micIdNum) {
          current.endIndex = idx;
          current.charIds.add(alloc.character_id);
        } else {
          if (current) segments.push(current);
          current = {
            micId: micIdNum,
            startIndex: idx,
            endIndex: idx,
            charIds: new Set([alloc.character_id]),
          };
        }
      } else if (current) {
        segments.push(current);
        current = null;
      }
    });
    if (current) segments.push(current);
    if (segments.length > 0) segmentsByMic.set(micIdNum, segments);
  });

  const micIds = Array.from(segmentsByMic.keys());
  const barH = (rowHeight - 2 * barPadding) / Math.max(micIds.length, 1);

  micIds.forEach((micId, micIdx) => {
    segmentsByMic.get(micId)!.forEach((seg, segIdx) => {
      const charNames = Array.from(seg.charIds)
        .map((id) => showStore.characterById(id)?.name ?? 'Unknown')
        .join(', ');
      const bar = buildMicBar(
        `cast-${castId}-mic-${micId}-seg-${segIdx}`,
        seg.startIndex,
        seg.endIndex,
        getRowY(rowIndex) + barPadding + micIdx * barH,
        barH,
        getColorForEntity(castId, 'cast'),
        seg.micId
      );
      bars.push({
        ...bar,
        tooltip: `${bar.label} – ${charNames} (Scenes ${seg.startIndex + 1}–${seg.endIndex + 1})`,
      });
    });
  });
}

const allocationBars = computed((): AllocationBar[] => {
  const bars: AllocationBar[] = [];
  rows.value.forEach((row, rowIndex) => {
    if (viewMode.value === 'mic') generateBarsForMic(row.id, rowIndex, bars);
    else if (viewMode.value === 'character') generateBarsForCharacter(row.id, rowIndex, bars);
    else generateBarsForCast(row.id, rowIndex, bars);
  });
  return bars;
});

const viewModeNames: Record<string, string> = {
  mic: 'Microphone',
  character: 'Character',
  cast: 'Cast',
};

function handleExport(): void {
  exportTimeline(svgRef, 'mic-timeline', viewModeNames[viewMode.value]);
}
</script>

<style lang="scss">
@use '@/assets/styles/timeline';
</style>
