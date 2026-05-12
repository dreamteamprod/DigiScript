<template>
  <div class="scene-density-heatmap">
    <div v-if="loading" class="text-center py-5">
      <b-spinner label="Loading heatmap..." />
    </div>
    <div v-else class="heatmap-wrapper">
      <!-- Header -->
      <div class="heatmap-header">
        <h5>Scene Microphone Density</h5>
        <p class="text-muted small">Shows the number of active microphones per scene.</p>
      </div>

      <!-- Legend -->
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

      <!-- No Data Message -->
      <div v-if="!hasData" class="text-center py-5 text-muted">
        No microphone allocation data to display
      </div>

      <!-- Heatmap -->
      <div v-else class="heatmap-container">
        <!-- Act sections -->
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
                class="scene-bar"
                :style="{
                  backgroundColor: getDensityColor(sceneData.micCount),
                  height: getBarHeight(sceneData.micCount) + 'px',
                }"
                :title="`${sceneData.scene.name}: ${sceneData.micCount} microphone${sceneData.micCount !== 1 ? 's' : ''}`"
                @click="handleBarClick(sceneData)"
              >
                <span class="mic-count">{{ sceneData.micCount }}</span>
              </div>
              <div class="scene-label">
                {{ sceneData.scene.name }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Summary Stats -->
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
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapGetters } from 'vuex';

export default defineComponent({
  name: 'SceneDensityHeatmap',
  props: {
    loading: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      maxBarHeight: 200,
      minBarHeight: 20,
    };
  },
  computed: {
    ...mapGetters(['MIC_TIMELINE_DATA', 'ACT_BY_ID']),
    hasData(): boolean {
      return this.scenes.length > 0 && Object.keys(this.allocations).length > 0;
    },
    scenes(): any[] {
      return (this as any).MIC_TIMELINE_DATA.scenes || [];
    },
    allocations(): Record<string, any> {
      return (this as any).MIC_TIMELINE_DATA.allocations || {};
    },
    sceneDensityData(): any[] {
      return this.scenes.map((scene: any) => {
        const micsInScene = new Set<number>();

        Object.keys(this.allocations).forEach((micId) => {
          const micAllocs = this.allocations[micId];
          if (Array.isArray(micAllocs)) {
            const hasAllocation = micAllocs.some((alloc: any) => alloc.scene_id === scene.id);
            if (hasAllocation) {
              micsInScene.add(parseInt(micId, 10));
            }
          }
        });

        return {
          scene,
          micCount: micsInScene.size,
        };
      });
    },
    actGroups(): any[] {
      const groups: any[] = [];
      const actMap: Record<number, any> = {};

      this.sceneDensityData.forEach((sceneData: any) => {
        const actId = sceneData.scene.act;
        if (!actMap[actId]) {
          actMap[actId] = {
            actId,
            actName: (this as any).ACT_BY_ID(actId)?.name || 'Unknown Act',
            scenes: [],
          };
          groups.push(actMap[actId]);
        }
        actMap[actId].scenes.push(sceneData);
      });

      return groups;
    },
    maxDensity(): number {
      if (this.sceneDensityData.length === 0) return 0;
      return Math.max(...this.sceneDensityData.map((d: any) => d.micCount));
    },
    averageDensity(): number {
      if (this.sceneDensityData.length === 0) return 0;
      const total = this.sceneDensityData.reduce((sum: number, d: any) => sum + d.micCount, 0);
      return total / this.sceneDensityData.length;
    },
    peakSceneName(): string {
      const peakScene = this.sceneDensityData.find((d: any) => d.micCount === this.maxDensity);
      return peakScene ? peakScene.scene.name : 'N/A';
    },
    uniqueMicsUsed(): number {
      const allMics = new Set<number>();
      Object.keys(this.allocations).forEach((micId) => {
        const micAllocs = this.allocations[micId];
        if (Array.isArray(micAllocs) && micAllocs.length > 0) {
          allMics.add(parseInt(micId, 10));
        }
      });
      return allMics.size;
    },
  },
  methods: {
    getDensityColor(micCount: number): string {
      if (micCount === 0) {
        return '#2c3e50';
      }

      const ratio = this.maxDensity > 0 ? micCount / this.maxDensity : 0;
      const hue = 240 - ratio * 240;
      const saturation = 70;
      const lightness = 45 + ratio * 10;

      return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
    },
    getBarHeight(micCount: number): number {
      if (micCount === 0) return this.minBarHeight;

      const ratio = this.maxDensity > 0 ? micCount / this.maxDensity : 0;
      const height = this.minBarHeight + ratio * (this.maxBarHeight - this.minBarHeight);
      return Math.round(height);
    },
    handleBarClick(sceneData: any): void {
      this.$emit('scene-click', {
        scene: sceneData.scene,
        micCount: sceneData.micCount,
      });
    },
  },
});
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

/* Legend */
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

/* Heatmap Container */
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
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
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

/* Stats */
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
