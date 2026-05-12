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

<script lang="ts">
import { defineComponent } from 'vue';
import { mapGetters, mapActions } from 'vuex';
import timelineMixin from '@/mixins/timelineMixin';

export default defineComponent({
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
    hasData(): boolean {
      return (this as any).scenes.length > 0 && (this as any).rows.length > 0;
    },
    scenes(): any[] {
      return (this as any).ORDERED_SCENES || [];
    },
    sceneIndexMap(): Record<number, number> {
      const map: Record<number, number> = {};
      (this as any).scenes.forEach((scene: any, index: number) => {
        map[scene.id] = index;
      });
      return map;
    },
    rows(): any[] {
      const crewList = (this as any).CREW_LIST as any[];
      const assignmentsByCrew = (this as any).CREW_ASSIGNMENTS_BY_CREW as Record<number, any[]>;
      return crewList
        .filter((crew: any) => (assignmentsByCrew[crew.id] || []).length > 0)
        .map((crew: any) => ({
          id: `crew-${crew.id}`,
          crewId: crew.id,
          name: crew.last_name ? `${crew.first_name} ${crew.last_name}` : crew.first_name,
        }));
    },
    conflicts(): Record<string, string> {
      const conflictMap: Record<string, string> = {};
      const assignmentsByCrew = (this as any).CREW_ASSIGNMENTS_BY_CREW as Record<number, any[]>;

      (this as any).rows.forEach((row: any) => {
        const assignments = assignmentsByCrew[row.crewId] || [];

        const byScene: Record<string, any[]> = {};
        const itemsByScene: Record<string, Set<string>> = {};
        assignments.forEach((a: any) => {
          if (!byScene[a.scene_id]) {
            byScene[a.scene_id] = [];
            itemsByScene[a.scene_id] = new Set();
          }
          byScene[a.scene_id].push(a);
          const itemKey = a.prop_id != null ? `prop-${a.prop_id}` : `scenery-${a.scenery_id}`;
          itemsByScene[a.scene_id].add(itemKey);
        });

        const assignedSceneIds = Object.keys(byScene).map(Number);

        assignedSceneIds.forEach((sceneId) => {
          if (itemsByScene[sceneId].size >= 2) {
            conflictMap[`${row.crewId}-${sceneId}`] = 'hard';
          }
        });

        assignedSceneIds.forEach((sceneId) => {
          const sceneIndex = (this as any).sceneIndexMap[sceneId];
          if (sceneIndex == null) return;
          const scene = (this as any).scenes[sceneIndex];

          const nextIndex = sceneIndex + 1;
          if (nextIndex < (this as any).scenes.length) {
            const nextScene = (this as any).scenes[nextIndex];
            if (nextScene.act === scene.act && assignedSceneIds.includes(nextScene.id)) {
              const itemsA = itemsByScene[sceneId];
              const itemsB = itemsByScene[nextScene.id];
              const sameItems =
                itemsA.size === itemsB.size && [...itemsA].every((k) => itemsB.has(k));

              if (!sameItems) {
                const key1 = `${row.crewId}-${sceneId}`;
                const key2 = `${row.crewId}-${nextScene.id}`;
                if (!conflictMap[key1]) conflictMap[key1] = 'soft';
                if (!conflictMap[key2]) conflictMap[key2] = 'soft';
              }
            }
          }
        });
      });

      return conflictMap;
    },
    allocationBars(): any[] {
      const bars: any[] = [];
      (this as any).rows.forEach((row: any, rowIndex: number) => {
        this.generateBarsForCrew(row.crewId, rowIndex, bars);
      });
      return bars;
    },
  },
  async mounted(): Promise<void> {
    await Promise.all([
      (this as any).GET_ACT_LIST(),
      (this as any).GET_SCENE_LIST(),
      (this as any).GET_CREW_LIST(),
      (this as any).GET_CREW_ASSIGNMENTS(),
      (this as any).GET_PROPS_LIST(),
      (this as any).GET_SCENERY_LIST(),
      (this as any).GET_PROPS_ALLOCATIONS(),
      (this as any).GET_SCENERY_ALLOCATIONS(),
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
    getItemName(assignment: any): string {
      if (assignment.prop_id != null) {
        const prop = (this as any).PROP_BY_ID(assignment.prop_id);
        return prop?.name || `Prop ${assignment.prop_id}`;
      }
      const scenery = (this as any).SCENERY_BY_ID(assignment.scenery_id);
      return scenery?.name || `Scenery ${assignment.scenery_id}`;
    },
    getItemId(assignment: any): number {
      return assignment.prop_id != null ? assignment.prop_id : assignment.scenery_id;
    },
    getItemType(assignment: any): string {
      return assignment.prop_id != null ? 'prop' : 'scenery';
    },
    generateBarsForCrew(crewId: number, rowIndex: number, bars: any[]): void {
      const assignmentsByCrew = (this as any).CREW_ASSIGNMENTS_BY_CREW as Record<number, any[]>;
      const assignments = assignmentsByCrew[crewId] || [];

      const byScene: Record<string, Record<string, any[]>> = {};
      assignments.forEach((a: any) => {
        if (!byScene[a.scene_id]) byScene[a.scene_id] = {};
        const itemKey = a.prop_id != null ? `prop-${a.prop_id}` : `scenery-${a.scenery_id}`;
        if (!byScene[a.scene_id][itemKey]) byScene[a.scene_id][itemKey] = [];
        byScene[a.scene_id][itemKey].push(a);
      });

      const availableHeight = (this as any).rowHeight - 2 * (this as any).barPadding;

      Object.entries(byScene).forEach(([sceneId, itemGroups]) => {
        const itemCount = Object.keys(itemGroups).length;
        const barHeight = availableHeight / itemCount;
        const sceneIndex = (this as any).sceneIndexMap[sceneId];
        if (sceneIndex == null) return;

        const scene = (this as any).scenes[sceneIndex];
        const conflictKey = `${crewId}-${sceneId}`;
        const conflictType = (this as any).conflicts[conflictKey];

        let cssClass = '';
        if (conflictType === 'hard') cssClass = 'conflict-hard';
        else if (conflictType === 'soft') cssClass = 'conflict-soft';

        const sortedKeys = Object.keys(itemGroups).sort((a, b) => {
          const nameA = this.getItemName(itemGroups[a][0]);
          const nameB = this.getItemName(itemGroups[b][0]);
          return nameA.localeCompare(nameB);
        });

        sortedKeys.forEach((itemKey, stackIndex) => {
          const group = itemGroups[itemKey];
          const representative = group[0];
          const itemName = this.getItemName(representative);
          const hasSet = group.some((a: any) => a.assignment_type === 'set');
          const hasStrike = group.some((a: any) => a.assignment_type === 'strike');

          let label: string;
          let tooltip: string;
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
            x: (this as any).getSceneX(sceneIndex),
            y: (this as any).getRowY(rowIndex) + (this as any).barPadding + stackIndex * barHeight,
            width: (this as any).sceneWidth,
            height: barHeight,
            color: (this as any).getColorForEntity(
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
    handleExport(): void {
      (this as any).exportTimeline('crew-timeline', 'Crew');
    },
  },
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
