<template>
  <div class="resource-availability">
    <div
      v-if="loading"
      class="text-center py-5"
    >
      <b-spinner label="Loading resource data..." />
    </div>
    <div
      v-else
      class="availability-wrapper"
    >
      <!-- Header -->
      <div class="availability-header">
        <h5>Microphone Resource Availability</h5>
        <p class="text-muted small">
          Shows microphone allocation status across all scenes.
        </p>
      </div>

      <!-- Summary Stats -->
      <div class="summary-stats">
        <div class="stat-card">
          <div class="stat-value">
            {{ totalMicrophones }}
          </div>
          <div class="stat-label">
            Total Microphones
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-value">
            {{ peakUsage }}
          </div>
          <div class="stat-label">
            Peak Simultaneous Usage
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-value">
            {{ conflictCount }}
          </div>
          <div class="stat-label">
            Total Conflicts
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-value">
            {{ utilizationRate }}%
          </div>
          <div class="stat-label">
            Average Utilization
          </div>
        </div>
      </div>

      <!-- Legend -->
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

      <!-- No Data Message -->
      <div
        v-if="!hasData"
        class="text-center py-5 text-muted"
      >
        No microphone allocation data to display
      </div>

      <!-- Availability Grid -->
      <div
        v-else
        class="availability-grid"
      >
        <!-- Scene-by-scene breakdown -->
        <div
          v-for="sceneData in sceneAvailability"
          :key="`scene-${sceneData.scene.id}`"
          class="scene-section"
        >
          <div class="scene-header">
            <h6>{{ sceneData.scene.name }}</h6>
            <div class="scene-stats">
              <span class="stat-badge available">
                {{ sceneData.available }} free
              </span>
              <span class="stat-badge in-use">
                {{ sceneData.inUse }} in use
              </span>
              <span
                v-if="sceneData.conflicts > 0"
                class="stat-badge conflict"
              >
                {{ sceneData.conflicts }} conflicts
              </span>
            </div>
          </div>

          <!-- Microphone status grid for this scene -->
          <div class="mic-status-grid">
            <div
              v-for="micStatus in sceneData.micStatuses"
              :key="`mic-${micStatus.mic.id}`"
              class="mic-status-item"
              :class="micStatus.statusClass"
              :title="getMicTooltip(micStatus)"
              @click="handleMicClick(sceneData.scene, micStatus)"
            >
              <div class="mic-name">
                {{ micStatus.mic.name || `Mic ${micStatus.mic.id}` }}
              </div>
              <div
                v-if="micStatus.character"
                class="mic-character"
              >
                {{ micStatus.character.name }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';

export default {
  name: 'ResourceAvailability',
  props: {
    loading: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    ...mapGetters([
      'MIC_TIMELINE_DATA',
      'MICROPHONE_BY_ID',
      'CHARACTER_BY_ID',
      'MIC_CONFLICTS',
    ]),
    hasData() {
      return this.scenes.length > 0 && this.microphones.length > 0;
    },
    scenes() {
      return this.MIC_TIMELINE_DATA.scenes || [];
    },
    microphones() {
      return this.MIC_TIMELINE_DATA.microphones || [];
    },
    allocations() {
      return this.MIC_TIMELINE_DATA.allocations || {};
    },
    totalMicrophones() {
      return this.microphones.length;
    },
    peakUsage() {
      // Find the maximum number of mics used in any single scene
      let max = 0;
      this.scenes.forEach((scene) => {
        const micsInScene = new Set();
        Object.keys(this.allocations).forEach((micId) => {
          const micAllocs = this.allocations[micId];
          if (Array.isArray(micAllocs)) {
            const hasAllocation = micAllocs.some((alloc) => alloc.scene_id === scene.id);
            if (hasAllocation) {
              micsInScene.add(parseInt(micId, 10));
            }
          }
        });
        max = Math.max(max, micsInScene.size);
      });
      return max;
    },
    conflictCount() {
      const conflicts = this.MIC_CONFLICTS?.conflicts || [];
      return conflicts.length;
    },
    utilizationRate() {
      if (this.scenes.length === 0 || this.totalMicrophones === 0) return 0;

      // Calculate average utilization across all scenes
      let totalAllocations = 0;
      this.scenes.forEach((scene) => {
        Object.keys(this.allocations).forEach((micId) => {
          const micAllocs = this.allocations[micId];
          if (Array.isArray(micAllocs)) {
            const hasAllocation = micAllocs.some((alloc) => alloc.scene_id === scene.id);
            if (hasAllocation) {
              totalAllocations += 1;
            }
          }
        });
      });

      const maxPossibleAllocations = this.scenes.length * this.totalMicrophones;
      return Math.round((totalAllocations / maxPossibleAllocations) * 100);
    },
    sceneAvailability() {
      return this.scenes.map((scene) => {
        const micStatuses = [];
        let available = 0;
        let inUse = 0;
        let conflicts = 0;

        // Get conflicts for this scene
        const allConflicts = this.MIC_CONFLICTS?.conflicts || [];
        const sceneConflicts = allConflicts.filter((conflict) => conflict.sceneId === scene.id || conflict.adjacentSceneId === scene.id);

        this.microphones.forEach((mic) => {
          const micAllocs = this.allocations[mic.id];
          let allocation = null;
          let status = 'available';
          let statusClass = 'available';
          let character = null;

          if (Array.isArray(micAllocs)) {
            allocation = micAllocs.find((alloc) => alloc.scene_id === scene.id);
          }

          if (allocation) {
            status = 'in-use';
            statusClass = 'in-use';
            character = this.CHARACTER_BY_ID(allocation.character_id);
            inUse += 1;

            // Check if this mic has a conflict in this scene
            const hasConflict = sceneConflicts.some((conflict) => conflict.micId === mic.id);
            if (hasConflict) {
              status = 'conflict';
              statusClass = 'conflict';
              conflicts += 1;
              inUse -= 1; // Don't double-count
            }
          } else {
            available += 1;
          }

          micStatuses.push({
            mic,
            status,
            statusClass,
            character,
            allocation,
          });
        });

        return {
          scene,
          micStatuses,
          available,
          inUse,
          conflicts,
        };
      });
    },
  },
  methods: {
    getMicTooltip(micStatus) {
      const micName = micStatus.mic.name || `Mic ${micStatus.mic.id}`;

      if (micStatus.status === 'conflict') {
        return `${micName}: CONFLICT - ${micStatus.character?.name || 'Unknown'}`;
      }
      if (micStatus.status === 'in-use') {
        return `${micName}: In use by ${micStatus.character?.name || 'Unknown'}`;
      }
      return `${micName}: Available`;
    },
    handleMicClick(scene, micStatus) {
      this.$emit('mic-click', {
        scene,
        microphone: micStatus.mic,
        character: micStatus.character,
        status: micStatus.status,
      });
    },
  },
};
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

/* Summary Stats */
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

/* Legend */
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

/* Availability Grid */
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
  background-color: rgba(40, 167, 69, 0.2);
  border-color: #28a745;
  color: #28a745;
}

.stat-badge.in-use {
  background-color: rgba(0, 123, 255, 0.2);
  border-color: #007bff;
  color: #007bff;
}

.stat-badge.conflict {
  background-color: rgba(220, 53, 69, 0.2);
  border-color: #dc3545;
  color: #dc3545;
}

/* Mic Status Grid */
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
  cursor: pointer;
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
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7);
  }
  50% {
    box-shadow: 0 0 0 4px rgba(220, 53, 69, 0);
  }
}
</style>
