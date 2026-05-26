<template>
  <div class="scene-density-heatmap">
    <div v-if="loading" class="text-center py-5">
      <BSpinner label="Loading heatmap..." />
    </div>
    <div v-else class="heatmap-wrapper">
      <div class="heatmap-header">
        <h5>Scene Microphone Density</h5>
        <p class="text-muted small">Shows the number of active microphones per scene.</p>
      </div>

      <div class="heatmap-legend">
        <div class="legend-item">
          <span class="legend-color" :style="{ backgroundColor: getDensityColor(0) }" />
          <span class="legend-label">0 mics</span>
        </div>
        <div class="legend-item">
          <span
            class="legend-color"
            :style="{ backgroundColor: getDensityColor(maxDensity / 4) }"
          />
          <span class="legend-label">Low</span>
        </div>
        <div class="legend-item">
          <span
            class="legend-color"
            :style="{ backgroundColor: getDensityColor(maxDensity / 2) }"
          />
          <span class="legend-label">Medium</span>
        </div>
        <div class="legend-item">
          <span
            class="legend-color"
            :style="{ backgroundColor: getDensityColor((maxDensity * 3) / 4) }"
          />
          <span class="legend-label">High</span>
        </div>
        <div class="legend-item">
          <span class="legend-color" :style="{ backgroundColor: getDensityColor(maxDensity) }" />
          <span class="legend-label">{{ maxDensity }}+ mics</span>
        </div>
      </div>

      <div v-if="!hasData" class="text-center py-5 text-muted">
        No microphone allocation data to display
      </div>

      <div v-else class="heatmap-container">
        <div v-for="actGroup in actGroups" :key="`act-${actGroup.actId}`" class="act-section">
          <div class="act-header">
            <h6>{{ actGroup.actName }}</h6>
          </div>
          <div class="scene-bars">
            <div
              v-for="sceneData in actGroup.scenes"
              :key="`scene-${sceneData.scene.id}`"
              class="scene-bar-wrapper"
            >
              <div
                v-b-tooltip.hover.top="
                  `${sceneData.scene.name}: ${sceneData.micCount} microphone${sceneData.micCount !== 1 ? 's' : ''}`
                "
                class="scene-bar"
                :style="{
                  backgroundColor: getDensityColor(sceneData.micCount),
                  height: getBarHeight(sceneData.micCount) + 'px',
                }"
              >
                <span class="mic-count">{{ sceneData.micCount }}</span>
              </div>
              <div class="scene-label">{{ sceneData.scene.name }}</div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="hasData" class="heatmap-stats">
        <div class="stat-item"><strong>Total Scenes:</strong> {{ scenes.length }}</div>
        <div class="stat-item">
          <strong>Avg Mics/Scene:</strong> {{ averageDensity.toFixed(1) }}
        </div>
        <div class="stat-item">
          <strong>Peak Usage:</strong> {{ maxDensity }} mics in {{ peakSceneName }}
        </div>
        <div class="stat-item"><strong>Total Active Mics:</strong> {{ uniqueMicsUsed }}</div>
      </div>
    </div>
  </div>
  <BTooltip v-model="tooltipVisible" :target="tooltipTarget" :title="tooltipText" manual />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useShowStore } from '@/stores/show';
import { useHoverTooltip } from '@/composables/useHoverTooltip';
import type { Scene } from '@/types/api/show';

interface SceneDensityEntry {
  scene: Scene;
  micCount: number;
}

interface ActDensityGroup {
  actId: number;
  actName: string;
  scenes: SceneDensityEntry[];
}

withDefaults(defineProps<{ loading?: boolean }>(), { loading: false });

const showStore = useShowStore();
const { tooltipTarget, tooltipText, tooltipVisible, showTooltip, hideTooltip } = useHoverTooltip();

const maxBarHeight = 200;
const minBarHeight = 20;

const scenes = computed(() => showStore.micTimelineData.scenes);
const allocations = computed(() => showStore.micTimelineData.allocations);

const hasData = computed(
  () => scenes.value.length > 0 && Object.keys(allocations.value).length > 0
);

const sceneDensityData = computed((): SceneDensityEntry[] =>
  scenes.value.map((scene) => {
    const micsInScene = new Set<number>();
    Object.keys(allocations.value).forEach((micId) => {
      const micAllocs = allocations.value[micId];
      if (Array.isArray(micAllocs) && micAllocs.some((a) => a.scene_id === scene.id)) {
        micsInScene.add(Number.parseInt(micId, 10));
      }
    });
    return { scene, micCount: micsInScene.size };
  })
);

const actGroups = computed((): ActDensityGroup[] => {
  const groups: ActDensityGroup[] = [];
  const actMap: Record<number, ActDensityGroup> = {};
  sceneDensityData.value.forEach((entry) => {
    const actId = entry.scene.act!;
    if (!actMap[actId]) {
      actMap[actId] = {
        actId,
        actName: showStore.actById(actId)?.name ?? 'Unknown Act',
        scenes: [],
      };
      groups.push(actMap[actId]);
    }
    actMap[actId].scenes.push(entry);
  });
  return groups;
});

const maxDensity = computed(() =>
  sceneDensityData.value.length === 0
    ? 0
    : Math.max(...sceneDensityData.value.map((d) => d.micCount))
);

const averageDensity = computed(() => {
  if (sceneDensityData.value.length === 0) return 0;
  const total = sceneDensityData.value.reduce((sum, d) => sum + d.micCount, 0);
  return total / sceneDensityData.value.length;
});

const peakSceneName = computed(() => {
  const peak = sceneDensityData.value.find((d) => d.micCount === maxDensity.value);
  return peak?.scene.name ?? 'N/A';
});

const uniqueMicsUsed = computed(() => {
  const allMics = new Set<number>();
  Object.keys(allocations.value).forEach((micId) => {
    const micAllocs = allocations.value[micId];
    if (Array.isArray(micAllocs) && micAllocs.length > 0) {
      allMics.add(Number.parseInt(micId, 10));
    }
  });
  return allMics.size;
});

function getDensityColor(micCount: number): string {
  if (micCount === 0) return '#2c3e50';
  const ratio = maxDensity.value > 0 ? micCount / maxDensity.value : 0;
  const hue = 240 - ratio * 240;
  return `hsl(${hue}, 70%, ${45 + ratio * 10}%)`;
}

function getBarHeight(micCount: number): number {
  if (micCount === 0) return minBarHeight;
  const ratio = maxDensity.value > 0 ? micCount / maxDensity.value : 0;
  return Math.round(minBarHeight + ratio * (maxBarHeight - minBarHeight));
}
</script>

<style scoped>
.scene-density-heatmap {
  background-color: var(--body-background);
  border: 1px solid #dee2e6;
  border-radius: 0.25rem;
  overflow: hidden;
}

.heatmap-wrapper {
  padding: 1.5rem;
}

.heatmap-header {
  margin-bottom: 1.5rem;
}

.heatmap-header h5 {
  margin-bottom: 0.5rem;
  color: #dee2e6;
}

.heatmap-legend {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 0.75rem;
  background-color: rgba(52, 58, 64, 0.5);
  border-radius: 0.25rem;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.legend-color {
  width: 20px;
  height: 20px;
  border-radius: 3px;
  border: 1px solid #6c757d;
}

.legend-label {
  font-size: 0.875rem;
  color: #adb5bd;
}

.heatmap-container {
  margin-bottom: 1.5rem;
}

.act-section {
  margin-bottom: 2rem;
}

.act-header {
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #6c757d;
}

.act-header h6 {
  margin: 0;
  color: #dee2e6;
  font-size: 1rem;
  font-weight: 600;
}

.scene-bars {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  flex-wrap: wrap;
}

.scene-bar-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  min-width: 60px;
}

.scene-bar {
  width: 60px;
  min-height: 20px;
  border-radius: 4px;
  border: 1px solid #212529;
  cursor: default;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.scene-bar:hover {
  opacity: 0.8;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

.mic-count {
  color: #fff;
  font-weight: 600;
  font-size: 0.875rem;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8);
  user-select: none;
}

.scene-label {
  font-size: 0.75rem;
  color: #adb5bd;
  text-align: center;
  max-width: 80px;
  word-wrap: break-word;
  user-select: none;
}

.heatmap-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  padding: 1rem;
  background-color: rgba(52, 58, 64, 0.5);
  border-radius: 0.25rem;
}

.stat-item {
  color: #dee2e6;
  font-size: 0.875rem;
}

.stat-item strong {
  color: #fff;
  margin-right: 0.25rem;
}
</style>
