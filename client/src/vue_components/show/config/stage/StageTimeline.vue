<template>
  <div class="timeline-container">
    <div v-if="loading" class="text-center py-5">
      <b-spinner label="Loading timeline..." />
    </div>
    <div v-else class="timeline-wrapper">
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
        <b-button size="sm" variant="outline-secondary" title="Export as PNG" @click="handleExport">
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
                  class="allocation-bar"
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
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';
import timelineMixin from '@/mixins/timelineMixin';

export default {
  name: 'StageTimeline',
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
    hasData() {
      return this.scenes.length > 0 && this.rows.length > 0;
    },
    scenes() {
      return this.ORDERED_SCENES || [];
    },
    rows() {
      const propsRows = this.PROPS_LIST.filter((prop) => this.hasPropAllocations(prop.id)).map(
        (prop) => ({
          id: `prop-${prop.id}`,
          itemId: prop.id,
          name: prop.name,
          type: 'prop',
        })
      );

      const sceneryRows = this.SCENERY_LIST.filter((scenery) =>
        this.hasSceneryAllocations(scenery.id)
      ).map((scenery) => ({
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
      // Combined: props first, then scenery
      return [...propsRows, ...sceneryRows];
    },
    allocationBars() {
      const bars = [];
      this.rows.forEach((row, rowIndex) => {
        this.generateBarsForItem(row.itemId, row.type, rowIndex, bars);
      });
      return bars;
    },
  },
  watch: {
    viewMode() {
      this.$forceUpdate();
    },
  },
  async mounted() {
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
    ]),
    async loadData() {
      await Promise.all([
        this.GET_ACT_LIST(),
        this.GET_SCENE_LIST(),
        this.GET_PROP_TYPES(),
        this.GET_SCENERY_TYPES(),
        this.GET_PROPS_LIST(),
        this.GET_SCENERY_LIST(),
        this.GET_PROPS_ALLOCATIONS(),
        this.GET_SCENERY_ALLOCATIONS(),
      ]);
      this.dataLoaded = true;
    },
    hasPropAllocations(propId) {
      const allocations = this.PROPS_ALLOCATIONS_BY_ITEM[propId];
      return allocations && allocations.length > 0;
    },
    hasSceneryAllocations(sceneryId) {
      const allocations = this.SCENERY_ALLOCATIONS_BY_ITEM[sceneryId];
      return allocations && allocations.length > 0;
    },

    formatSceneRange(startScene, endScene) {
      if (startScene === endScene) {
        return startScene;
      }
      return `${startScene} - ${endScene}`;
    },

    generateBarsForItem(itemId, itemType, rowIndex, bars) {
      const allocations =
        itemType === 'prop'
          ? this.PROPS_ALLOCATIONS_BY_ITEM[itemId] || []
          : this.SCENERY_ALLOCATIONS_BY_ITEM[itemId] || [];
      const segments = this.groupConsecutiveScenes(allocations, 'scene_id');

      const item = itemType === 'prop' ? this.PROP_BY_ID(itemId) : this.SCENERY_BY_ID(itemId);
      const itemName = item?.name || `${itemType === 'prop' ? 'Prop' : 'Scenery'} ${itemId}`;

      segments.forEach((segment, idx) => {
        const startX = this.getSceneX(segment.startIndex);
        const width = this.sceneWidth * (segment.endIndex - segment.startIndex + 1);

        bars.push({
          id: `${itemType}-${itemId}-seg-${idx}`,
          x: startX,
          y: this.getRowY(rowIndex) + this.barPadding,
          width,
          height: this.rowHeight - 2 * this.barPadding,
          color: this.getColorForEntity(itemId, itemType),
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
    handleExport() {
      const viewModeNames = {
        combined: 'Combined',
        props: 'Props',
        scenery: 'Scenery',
      };
      this.exportTimeline('stage-timeline', viewModeNames[this.viewMode]);
    },
    handleBarClick(bar) {
      this.$emit('bar-click', bar.data);
    },
    handleBarHover(bar, event) {
      this.$emit('bar-hover', { bar: bar.data, event });
    },
    handleBarLeave() {
      this.$emit('bar-leave');
    },
  },
};
</script>

<style lang="scss">
@use '@/assets/styles/timeline';
</style>
