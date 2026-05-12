<template>
  <div class="timeline-container">
    <div v-if="loading" class="text-center py-5">
      <b-spinner label="Loading timeline..." />
    </div>
    <div v-else class="timeline-with-panel">
      <div class="timeline-wrapper">
        <div class="timeline-controls-bar">
          <b-button-group>
            <b-button
              :variant="viewMode === 'combined' ? 'primary' : 'outline-primary'"
              size="sm"
              @click="viewMode = 'combined'"
            >
              Combined
            </b-button>
            <b-button
              :variant="viewMode === 'props' ? 'primary' : 'outline-primary'"
              size="sm"
              @click="viewMode = 'props'"
            >
              Props
            </b-button>
            <b-button
              :variant="viewMode === 'scenery' ? 'primary' : 'outline-primary'"
              size="sm"
              @click="viewMode = 'scenery'"
            >
              Scenery
            </b-button>
          </b-button-group>
          <b-button
            size="sm"
            variant="outline-secondary"
            title="Export as PNG"
            @click="handleExport"
          >
            <b-icon-download />
          </b-button>
        </div>
        <div class="svg-container">
          <div v-if="!hasData" class="text-center py-5 text-muted">
            No allocation data to display for this view
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
                    :class="['allocation-bar', { selected: isBarSelected(bar) }]"
                    @click="handleBarClick(bar)"
                    @mouseenter="handleBarHover(bar, $event)"
                    @mouseleave="handleBarLeave()"
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

<script lang="ts">
import { defineComponent } from 'vue';
import { mapGetters, mapActions } from 'vuex';
import timelineMixin from '@/mixins/timelineMixin';
import TimelineSidePanel from './TimelineSidePanel.vue';

export default defineComponent({
  name: 'StageTimeline',
  components: {
    TimelineSidePanel,
  },
  mixins: [timelineMixin],
  props: {
    loading: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      viewMode: 'combined',
      dataLoaded: false,
      selectedItem: null as any,
      sidePanelOpen: false,
    };
  },
  computed: {
    ...mapGetters([
      'ORDERED_SCENES',
      'PROPS_LIST',
      'SCENERY_LIST',
      'PROPS_ALLOCATIONS',
      'SCENERY_ALLOCATIONS',
      'PROPS_ALLOCATIONS_BY_ITEM',
      'SCENERY_ALLOCATIONS_BY_ITEM',
      'PROP_BY_ID',
      'SCENERY_BY_ID',
    ]),
    hasData(): boolean {
      return (this as any).scenes.length > 0 && (this as any).rows.length > 0;
    },
    scenes(): any[] {
      return (this as any).ORDERED_SCENES || [];
    },
    rows(): any[] {
      const propsList = (this as any).PROPS_LIST as any[];
      const sceneryList = (this as any).SCENERY_LIST as any[];

      const propsRows = propsList
        .filter((prop: any) => this.hasPropAllocations(prop.id))
        .map((prop: any) => ({
          id: `prop-${prop.id}`,
          itemId: prop.id,
          name: prop.name,
          type: 'prop',
        }));

      const sceneryRows = sceneryList
        .filter((scenery: any) => this.hasSceneryAllocations(scenery.id))
        .map((scenery: any) => ({
          id: `scenery-${scenery.id}`,
          itemId: scenery.id,
          name: scenery.name,
          type: 'scenery',
        }));

      if (this.viewMode === 'props') {
        return propsRows;
      }
      if (this.viewMode === 'scenery') {
        return sceneryRows;
      }
      return [...propsRows, ...sceneryRows];
    },
    allocationBars(): any[] {
      const bars: any[] = [];
      (this as any).rows.forEach((row: any, rowIndex: number) => {
        this.generateBarsForItem(row.itemId, row.type, rowIndex, bars);
      });
      return bars;
    },
  },
  watch: {
    viewMode(): void {
      this.$forceUpdate();
    },
  },
  async mounted(): Promise<void> {
    await this.loadData();
  },
  methods: {
    ...mapActions([
      'GET_PROPS_LIST',
      'GET_SCENERY_LIST',
      'GET_PROPS_ALLOCATIONS',
      'GET_SCENERY_ALLOCATIONS',
      'GET_ACT_LIST',
      'GET_SCENE_LIST',
      'GET_PROP_TYPES',
      'GET_SCENERY_TYPES',
      'GET_CREW_LIST',
      'GET_CREW_ASSIGNMENTS',
    ]),
    async loadData(): Promise<void> {
      await Promise.all([
        (this as any).GET_ACT_LIST(),
        (this as any).GET_SCENE_LIST(),
        (this as any).GET_PROP_TYPES(),
        (this as any).GET_SCENERY_TYPES(),
        (this as any).GET_PROPS_LIST(),
        (this as any).GET_SCENERY_LIST(),
        (this as any).GET_PROPS_ALLOCATIONS(),
        (this as any).GET_SCENERY_ALLOCATIONS(),
        (this as any).GET_CREW_LIST(),
        (this as any).GET_CREW_ASSIGNMENTS(),
      ]);
      this.dataLoaded = true;
    },
    hasPropAllocations(propId: number): boolean {
      const allocations = ((this as any).PROPS_ALLOCATIONS_BY_ITEM as Record<number, any[]>)[
        propId
      ];
      return allocations && allocations.length > 0;
    },
    hasSceneryAllocations(sceneryId: number): boolean {
      const allocations = ((this as any).SCENERY_ALLOCATIONS_BY_ITEM as Record<number, any[]>)[
        sceneryId
      ];
      return allocations && allocations.length > 0;
    },
    formatSceneRange(startScene: any, endScene: any): string {
      if (startScene === endScene) {
        return startScene;
      }
      return `${startScene} - ${endScene}`;
    },
    generateBarsForItem(itemId: number, itemType: string, rowIndex: number, bars: any[]): void {
      const allocations =
        itemType === 'prop'
          ? ((this as any).PROPS_ALLOCATIONS_BY_ITEM as Record<number, any[]>)[itemId] || []
          : ((this as any).SCENERY_ALLOCATIONS_BY_ITEM as Record<number, any[]>)[itemId] || [];
      const segments = (this as any).groupConsecutiveScenes(allocations, 'scene_id');

      const item =
        itemType === 'prop'
          ? (this as any).PROP_BY_ID(itemId)
          : (this as any).SCENERY_BY_ID(itemId);
      const itemName = item?.name || `${itemType === 'prop' ? 'Prop' : 'Scenery'} ${itemId}`;

      segments.forEach((segment: any, idx: number) => {
        const startX = (this as any).getSceneX(segment.startIndex);
        const width = (this as any).sceneWidth * (segment.endIndex - segment.startIndex + 1);

        bars.push({
          id: `${itemType}-${itemId}-seg-${idx}`,
          x: startX,
          y: (this as any).getRowY(rowIndex) + (this as any).barPadding,
          width,
          height: (this as any).rowHeight - 2 * (this as any).barPadding,
          color: (this as any).getColorForEntity(itemId, itemType),
          label: itemName,
          tooltip: `${itemName} (${this.formatSceneRange(segment.startScene, segment.endScene)})`,
          data: {
            type: itemType,
            itemId,
            startScene: segment.startIndex,
            endScene: segment.endIndex,
          },
        });
      });
    },
    handleExport(): void {
      const viewModeNames: Record<string, string> = {
        combined: 'Combined',
        props: 'Props',
        scenery: 'Scenery',
      };
      (this as any).exportTimeline('stage-timeline', viewModeNames[this.viewMode]);
    },
    handleBarClick(bar: any): void {
      this.selectedItem = bar.data;
      this.sidePanelOpen = true;
      this.$emit('bar-click', bar.data);
    },
    handleBarHover(bar: any, event: MouseEvent): void {
      this.$emit('bar-hover', { bar: bar.data, event });
    },
    handleBarLeave(): void {
      this.$emit('bar-leave');
    },
    closeSidePanel(): void {
      this.sidePanelOpen = false;
      this.selectedItem = null;
    },
    isBarSelected(bar: any): boolean {
      if (!this.selectedItem) return false;
      return (
        this.selectedItem.type === bar.data.type &&
        this.selectedItem.itemId === bar.data.itemId &&
        this.selectedItem.startScene === bar.data.startScene &&
        this.selectedItem.endScene === bar.data.endScene
      );
    },
  },
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
