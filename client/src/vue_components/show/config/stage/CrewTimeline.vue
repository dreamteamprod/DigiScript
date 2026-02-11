<template>
  <div class="timeline-container">
    <div v-if="!dataLoaded" class="text-center py-5">
      <b-spinner label="Loading timeline..." />
    </div>
    <div v-else class="timeline-wrapper">
      <div class="timeline-controls-bar">
        <span class="text-light small">Crew Assignments</span>
        <b-button size="sm" variant="outline-secondary" title="Export as PNG" @click="handleExport">
          <b-icon-download />
        </b-button>
      </div>
      <div class="svg-container">
        <div v-if="!hasData" class="text-center py-5 text-muted">
          No crew assignments to display. Assign crew members to SET/STRIKE tasks in the Stage
          Manager tab.
        </div>
        <svg v-else ref="svg" :width="totalWidth" :height="totalHeight" class="timeline-svg">
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

<script>
import { mapGetters, mapActions } from 'vuex';
import timelineMixin from '@/mixins/timelineMixin';

export default {
  name: 'CrewTimeline',
  mixins: [timelineMixin],
  data() {
    return {
      dataLoaded: false,
    };
  },
  computed: {
    ...mapGetters([
      'ORDERED_SCENES',
      'CREW_LIST',
      'CREW_ASSIGNMENTS_BY_CREW',
      'PROPS_LIST',
      'SCENERY_LIST',
      'PROP_BY_ID',
      'SCENERY_BY_ID',
    ]),
    hasData() {
      return this.scenes.length > 0 && this.rows.length > 0;
    },
    scenes() {
      return this.ORDERED_SCENES || [];
    },
    sceneIndexMap() {
      const map = {};
      this.scenes.forEach((scene, index) => {
        map[scene.id] = index;
      });
      return map;
    },
    rows() {
      return this.CREW_LIST.filter(
        (crew) => (this.CREW_ASSIGNMENTS_BY_CREW[crew.id] || []).length > 0
      ).map((crew) => ({
        id: `crew-${crew.id}`,
        crewId: crew.id,
        name: crew.last_name ? `${crew.first_name} ${crew.last_name}` : crew.first_name,
      }));
    },
    conflicts() {
      const conflictMap = {};

      this.rows.forEach((row) => {
        const assignments = this.CREW_ASSIGNMENTS_BY_CREW[row.crewId] || [];

        // Group assignments by scene, tracking distinct items per scene
        const byScene = {};
        const itemsByScene = {};
        assignments.forEach((a) => {
          if (!byScene[a.scene_id]) {
            byScene[a.scene_id] = [];
            itemsByScene[a.scene_id] = new Set();
          }
          byScene[a.scene_id].push(a);
          const itemKey = a.prop_id != null ? `prop-${a.prop_id}` : `scenery-${a.scenery_id}`;
          itemsByScene[a.scene_id].add(itemKey);
        });

        const assignedSceneIds = Object.keys(byScene).map(Number);

        // Hard conflicts: 2+ distinct items in the same scene
        assignedSceneIds.forEach((sceneId) => {
          if (itemsByScene[sceneId].size >= 2) {
            conflictMap[`${row.crewId}-${sceneId}`] = 'hard';
          }
        });

        // Soft conflicts: adjacent scenes (same act) with different item sets
        assignedSceneIds.forEach((sceneId) => {
          const sceneIndex = this.sceneIndexMap[sceneId];
          if (sceneIndex == null) return;
          const scene = this.scenes[sceneIndex];

          const nextIndex = sceneIndex + 1;
          if (nextIndex < this.scenes.length) {
            const nextScene = this.scenes[nextIndex];
            if (nextScene.act === scene.act && assignedSceneIds.includes(nextScene.id)) {
              // Compare item sets — only flag if they differ
              const itemsA = itemsByScene[sceneId];
              const itemsB = itemsByScene[nextScene.id];
              const sameItems =
                itemsA.size === itemsB.size && [...itemsA].every((k) => itemsB.has(k));

              if (!sameItems) {
                const key1 = `${row.crewId}-${sceneId}`;
                const key2 = `${row.crewId}-${nextScene.id}`;
                // Hard takes precedence
                if (!conflictMap[key1]) conflictMap[key1] = 'soft';
                if (!conflictMap[key2]) conflictMap[key2] = 'soft';
              }
            }
          }
        });
      });

      return conflictMap;
    },
    allocationBars() {
      const bars = [];
      this.rows.forEach((row, rowIndex) => {
        this.generateBarsForCrew(row.crewId, rowIndex, bars);
      });
      return bars;
    },
  },
  async mounted() {
    await Promise.all([
      this.GET_ACT_LIST(),
      this.GET_SCENE_LIST(),
      this.GET_CREW_LIST(),
      this.GET_CREW_ASSIGNMENTS(),
      this.GET_PROPS_LIST(),
      this.GET_SCENERY_LIST(),
      this.GET_PROPS_ALLOCATIONS(),
      this.GET_SCENERY_ALLOCATIONS(),
    ]);
    this.dataLoaded = true;
  },
  methods: {
    ...mapActions([
      'GET_ACT_LIST',
      'GET_SCENE_LIST',
      'GET_CREW_LIST',
      'GET_CREW_ASSIGNMENTS',
      'GET_PROPS_LIST',
      'GET_SCENERY_LIST',
      'GET_PROPS_ALLOCATIONS',
      'GET_SCENERY_ALLOCATIONS',
    ]),
    getItemName(assignment) {
      if (assignment.prop_id != null) {
        const prop = this.PROP_BY_ID(assignment.prop_id);
        return prop?.name || `Prop ${assignment.prop_id}`;
      }
      const scenery = this.SCENERY_BY_ID(assignment.scenery_id);
      return scenery?.name || `Scenery ${assignment.scenery_id}`;
    },
    getItemId(assignment) {
      return assignment.prop_id != null ? assignment.prop_id : assignment.scenery_id;
    },
    getItemType(assignment) {
      return assignment.prop_id != null ? 'prop' : 'scenery';
    },
    generateBarsForCrew(crewId, rowIndex, bars) {
      const assignments = this.CREW_ASSIGNMENTS_BY_CREW[crewId] || [];

      // Group by scene, then by item within each scene
      const byScene = {};
      assignments.forEach((a) => {
        if (!byScene[a.scene_id]) byScene[a.scene_id] = {};
        const itemKey = a.prop_id != null ? `prop-${a.prop_id}` : `scenery-${a.scenery_id}`;
        if (!byScene[a.scene_id][itemKey]) byScene[a.scene_id][itemKey] = [];
        byScene[a.scene_id][itemKey].push(a);
      });

      const availableHeight = this.rowHeight - 2 * this.barPadding;

      Object.entries(byScene).forEach(([sceneId, itemGroups]) => {
        // Bar height based on distinct items in THIS scene
        const itemCount = Object.keys(itemGroups).length;
        const barHeight = availableHeight / itemCount;
        const sceneIndex = this.sceneIndexMap[sceneId];
        if (sceneIndex == null) return;

        const scene = this.scenes[sceneIndex];
        const conflictKey = `${crewId}-${sceneId}`;
        const conflictType = this.conflicts[conflictKey];

        let cssClass = '';
        if (conflictType === 'hard') cssClass = 'conflict-hard';
        else if (conflictType === 'soft') cssClass = 'conflict-soft';

        // Sort item groups by name for stable ordering
        const sortedKeys = Object.keys(itemGroups).sort((a, b) => {
          const nameA = this.getItemName(itemGroups[a][0]);
          const nameB = this.getItemName(itemGroups[b][0]);
          return nameA.localeCompare(nameB);
        });

        sortedKeys.forEach((itemKey, stackIndex) => {
          const group = itemGroups[itemKey];
          const representative = group[0];
          const itemName = this.getItemName(representative);
          const hasSet = group.some((a) => a.assignment_type === 'set');
          const hasStrike = group.some((a) => a.assignment_type === 'strike');

          let label, tooltip;
          if (hasSet && hasStrike) {
            label = `▲ ${itemName} ▼`;
            tooltip = `SET & STRIKE: ${itemName} (${scene.name})`;
          } else if (hasSet) {
            label = `▲ ${itemName}`;
            tooltip = `SET: ${itemName} (${scene.name})`;
          } else {
            label = `▼ ${itemName}`;
            tooltip = `STRIKE: ${itemName} (${scene.name})`;
          }

          bars.push({
            id: `crew-${crewId}-scene-${sceneId}-${stackIndex}`,
            x: this.getSceneX(sceneIndex),
            y: this.getRowY(rowIndex) + this.barPadding + stackIndex * barHeight,
            width: this.sceneWidth,
            height: barHeight,
            color: this.getColorForEntity(
              this.getItemId(representative),
              this.getItemType(representative)
            ),
            label,
            tooltip,
            cssClass,
          });
        });
      });
    },
    handleExport() {
      this.exportTimeline('crew-timeline', 'Crew');
    },
  },
};
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
