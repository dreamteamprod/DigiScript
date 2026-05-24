<template>
  <div class="resource-availability">
    <div v-if="loading" class="text-center py-5">
      <BSpinner label="Loading resource data..." />
    </div>
    <div v-else class="availability-wrapper">
      <div class="availability-header">
        <h5>Microphone Resource Availability</h5>
        <p class="text-muted small">Shows microphone allocation status across all scenes.</p>
      </div>

      <div class="summary-stats">
        <div class="stat-card">
          <div class="stat-value">{{ totalMicrophones }}</div>
          <div class="stat-label">Total Microphones</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ peakUsage }}</div>
          <div class="stat-label">Peak Simultaneous Usage</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ conflictCount }}</div>
          <div class="stat-label">Total Conflicts</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ utilizationRate }}%</div>
          <div class="stat-label">Average Utilization</div>
        </div>
      </div>

      <div class="availability-legend">
        <div class="legend-item">
          <span class="legend-icon available" />
          <span class="legend-label">Available</span>
        </div>
        <div class="legend-item">
          <span class="legend-icon in-use" />
          <span class="legend-label">In Use</span>
        </div>
        <div class="legend-item">
          <span class="legend-icon conflict" />
          <span class="legend-label">Conflict</span>
        </div>
      </div>

      <div v-if="!hasData" class="text-center py-5 text-muted">
        No microphone allocation data to display
      </div>

      <div v-else class="availability-grid">
        <div
          v-for="sceneData in sceneAvailability"
          :key="`scene-${sceneData.scene.id}`"
          class="scene-section"
        >
          <div class="scene-header">
            <h6>{{ sceneData.scene.name }}</h6>
            <div class="scene-stats">
              <span class="stat-badge available">{{ sceneData.available }} free</span>
              <span class="stat-badge in-use">{{ sceneData.inUse }} in use</span>
              <span v-if="sceneData.conflicts > 0" class="stat-badge conflict">
                {{ sceneData.conflicts }} conflicts
              </span>
            </div>
          </div>
          <div class="mic-status-grid">
            <div
              v-for="micStatus in sceneData.micStatuses"
              :key="`mic-${micStatus.mic.id}`"
              class="mic-status-item"
              :class="micStatus.statusClass"
              :title="getMicTooltip(micStatus)"
            >
              <div class="mic-name">{{ micStatus.mic.name ?? `Mic ${micStatus.mic.id}` }}</div>
              <div v-if="micStatus.character" class="mic-character">
                {{ micStatus.character.name }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useShowStore } from '@/stores/show';
import type { Scene, Character } from '@/types/api/show';
import type { Microphone } from '@/types/api/microphones';

interface MicStatus {
  mic: Microphone;
  status: 'available' | 'in-use' | 'conflict';
  statusClass: string;
  character: Character | null;
}

interface SceneAvailability {
  scene: Scene;
  micStatuses: MicStatus[];
  available: number;
  inUse: number;
  conflicts: number;
}

withDefaults(defineProps<{ loading?: boolean }>(), { loading: false });

const showStore = useShowStore();

const scenes = computed(() => showStore.micTimelineData.scenes);
const microphones = computed(() => showStore.micTimelineData.microphones);
const allocations = computed(() => showStore.micTimelineData.allocations);

const hasData = computed(() => scenes.value.length > 0 && microphones.value.length > 0);
const totalMicrophones = computed(() => microphones.value.length);

const peakUsage = computed(() => {
  let max = 0;
  scenes.value.forEach((scene) => {
    const micsInScene = new Set<number>();
    Object.keys(allocations.value).forEach((micId) => {
      const micAllocs = allocations.value[micId];
      if (Array.isArray(micAllocs) && micAllocs.some((a) => a.scene_id === scene.id)) {
        micsInScene.add(Number.parseInt(micId, 10));
      }
    });
    max = Math.max(max, micsInScene.size);
  });
  return max;
});

const conflictCount = computed(() => showStore.micConflicts.conflicts.length);

const utilizationRate = computed(() => {
  if (scenes.value.length === 0 || totalMicrophones.value === 0) return 0;
  let totalAllocs = 0;
  scenes.value.forEach((scene) => {
    Object.keys(allocations.value).forEach((micId) => {
      const micAllocs = allocations.value[micId];
      if (Array.isArray(micAllocs) && micAllocs.some((a) => a.scene_id === scene.id)) {
        totalAllocs += 1;
      }
    });
  });
  return Math.round((totalAllocs / (scenes.value.length * totalMicrophones.value)) * 100);
});

const sceneAvailability = computed((): SceneAvailability[] =>
  scenes.value.map((scene) => {
    const allConflicts = showStore.micConflicts.conflicts;
    const sceneConflicts = allConflicts.filter(
      (c) => c.sceneId === scene.id || c.adjacentSceneId === scene.id
    );

    const micStatuses: MicStatus[] = [];
    let available = 0;
    let inUse = 0;
    let conflicts = 0;

    microphones.value.forEach((mic) => {
      const micAllocs = allocations.value[mic.id];
      const allocation = Array.isArray(micAllocs)
        ? micAllocs.find((a) => a.scene_id === scene.id)
        : undefined;

      let status: MicStatus['status'] = 'available';
      let character: Character | null = null;

      if (allocation) {
        status = 'in-use';
        character = showStore.characterById(allocation.character_id);
        const hasConflict = sceneConflicts.some((c) => c.micId === mic.id);
        if (hasConflict) {
          status = 'conflict';
          conflicts += 1;
        } else {
          inUse += 1;
        }
      } else {
        available += 1;
      }

      micStatuses.push({ mic, status, statusClass: status, character });
    });

    return { scene, micStatuses, available, inUse, conflicts };
  })
);

function getMicTooltip(micStatus: MicStatus): string {
  const name = micStatus.mic.name ?? `Mic ${micStatus.mic.id}`;
  if (micStatus.status === 'conflict')
    return `${name}: CONFLICT – ${micStatus.character?.name ?? 'Unknown'}`;
  if (micStatus.status === 'in-use')
    return `${name}: In use by ${micStatus.character?.name ?? 'Unknown'}`;
  return `${name}: Available`;
}
</script>

<style scoped>
.resource-availability {
  background-color: var(--body-background);
  border: 1px solid #dee2e6;
  border-radius: 0.25rem;
  overflow: hidden;
}

.availability-wrapper {
  padding: 1.5rem;
}

.availability-header {
  margin-bottom: 1.5rem;
}

.availability-header h5 {
  margin-bottom: 0.5rem;
  color: #dee2e6;
}

.summary-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background-color: rgba(52, 58, 64, 0.5);
  border: 1px solid #6c757d;
  border-radius: 0.25rem;
  padding: 1rem;
  text-align: center;
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: #fff;
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.875rem;
  color: #adb5bd;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.availability-legend {
  display: flex;
  gap: 1.5rem;
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

.legend-icon {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: 1px solid #212529;
}

.legend-icon.available {
  background-color: #28a745;
}

.legend-icon.in-use {
  background-color: #007bff;
}

.legend-icon.conflict {
  background-color: #dc3545;
}

.legend-label {
  font-size: 0.875rem;
  color: #adb5bd;
  font-weight: 500;
}

.availability-grid {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.scene-section {
  border: 1px solid #6c757d;
  border-radius: 0.25rem;
  overflow: hidden;
}

.scene-header {
  background-color: rgba(52, 58, 64, 0.8);
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #6c757d;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.scene-header h6 {
  margin: 0;
  color: #dee2e6;
  font-size: 1rem;
  font-weight: 600;
}

.scene-stats {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.stat-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  border: 1px solid;
}

.stat-badge.available {
  background-color: #d4edda;
  border-color: #28a745;
  color: #155724;
}

.stat-badge.in-use {
  background-color: #cce5ff;
  border-color: #007bff;
  color: #004085;
}

.stat-badge.conflict {
  background-color: #f8d7da;
  border-color: #dc3545;
  color: #721c24;
}

.mic-status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 0.5rem;
  padding: 1rem;
}

.mic-status-item {
  padding: 0.75rem;
  border-radius: 0.25rem;
  border: 2px solid;
  cursor: default;
  transition: all 0.2s ease;
  min-height: 60px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.mic-status-item.available {
  background-color: rgba(40, 167, 69, 0.1);
  border-color: #28a745;
}

.mic-status-item.in-use {
  background-color: rgba(0, 123, 255, 0.1);
  border-color: #007bff;
}

.mic-status-item.conflict {
  background-color: rgba(220, 53, 69, 0.1);
  border-color: #dc3545;
  animation: pulse-conflict 2s ease-in-out infinite;
}

.mic-status-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

.mic-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: #dee2e6;
  margin-bottom: 0.25rem;
}

.mic-character {
  font-size: 0.75rem;
  color: #adb5bd;
  font-style: italic;
}

@keyframes pulse-conflict {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7);
  }
  50% {
    box-shadow: 0 0 0 4px rgba(220, 53, 69, 0);
  }
}
</style>
