<template>
  <div ref="paneContainer" class="stage-manager-pane">
    <div class="pane-header">
      <h6 class="mb-0">Stage Manager</h6>
    </div>
    <div v-if="!loaded" class="loading-state">
      <b-spinner small variant="light" />
    </div>
    <div v-else-if="orderedScenes.length === 0" class="empty-state">
      <small class="text-muted">No scenes configured</small>
    </div>
    <div v-else ref="scrollContainer" class="scenes-container">
      <b-card
        v-for="scene in orderedScenes"
        :ref="`scene-card-${scene.id}`"
        :key="scene.id"
        no-body
        class="scene-card mb-2"
        :class="{
          'current-scene': scene.id === currentSceneId,
          'next-scene': scene.id === nextSceneId,
        }"
      >
        <b-card-header
          header-tag="header"
          class="p-2 scene-header"
          role="button"
          @click="toggleScene(scene.id)"
        >
          <div class="d-flex justify-content-between align-items-center">
            <span class="scene-title">
              <b-icon
                :icon="expandedScenes[scene.id] ? 'chevron-down' : 'chevron-right'"
                class="mr-1"
              />
              {{ getSceneDisplayName(scene) }}
            </span>
            <span class="scene-badges">
              <b-icon
                v-if="pinnedScenes[scene.id]"
                icon="pin-angle-fill"
                class="pinned-icon mr-1"
                title="Pinned - won't auto-collapse"
              />
              <b-badge v-if="scene.id === currentSceneId" variant="success" pill> Current </b-badge>
              <b-badge v-else-if="scene.id === nextSceneId" variant="primary" pill> Next </b-badge>
            </span>
          </div>
        </b-card-header>
        <b-collapse :id="`collapse-${scene.id}`" v-model="expandedScenes[scene.id]">
          <b-card-body class="p-2 scene-body">
            <div
              class="d-flex justify-content-end align-items-end"
              @click.stop.prevent="showSMPlanModal(scene)"
            >
              <b-button size="sm" variant="primary"> Plan </b-button>
            </div>
            <div
              v-if="
                getSceneryForScene(scene.id).length === 0 && getPropsForScene(scene.id).length === 0
              "
              class="empty-scene"
            >
              <small>No props or scenery</small>
            </div>
            <template v-else>
              <div v-if="getSceneryForScene(scene.id).length > 0" class="mb-2">
                <small class="section-label">Scenery</small>
                <ul class="item-list mb-0">
                  <li v-for="item in getSceneryForScene(scene.id)" :key="`scenery-${item.id}`">
                    {{ getSceneryDisplayName(item) }}
                  </li>
                </ul>
              </div>
              <div v-if="getPropsForScene(scene.id).length > 0">
                <small class="section-label">Props</small>
                <ul class="item-list mb-0">
                  <li v-for="item in getPropsForScene(scene.id)" :key="`prop-${item.id}`">
                    {{ getPropDisplayName(item) }}
                  </li>
                </ul>
              </div>
            </template>
          </b-card-body>
        </b-collapse>
      </b-card>
    </div>
    <b-modal
      id="sm-plan-modal"
      ref="sm-plan-modal"
      :title="`${smPlanScene ? getSceneDisplayName(smPlanScene) : ''} - Plan`"
      size="lg"
      @hidden="resetSMPlanScene"
    >
      <div v-if="smPlanScene">
        <b-card no-body class="mb-2">
          <b-card-header header-tag="header" class="p-2" role="button" @click="togglePlanSet">
            <div class="d-flex justify-content-between align-items-center">
              <span>
                <b-icon :icon="smPlanSet ? 'chevron-down' : 'chevron-right'" class="mr-1" />
                Setting
              </span>
            </div>
          </b-card-header>
          <b-collapse v-model="smPlanSet">
            <b-card-body class="p-2">
              <b-container class="mx-0 px-0" fluid>
                <b-row class="plan-header-row">
                  <b-col cols="6" class="plan-header-col border-right">
                    <b>Scenery</b>
                  </b-col>
                  <b-col cols="6" class="plan-header-col">
                    <b>Props</b>
                  </b-col>
                </b-row>
                <b-row class="plan-content-row">
                  <b-col cols="6" class="plan-content-col border-right">
                    <ul v-if="getSettingScenery(smPlanScene).length > 0" class="item-list mb-0">
                      <li
                        v-for="item in getSettingScenery(smPlanScene)"
                        :key="`set-scenery-${item.id}`"
                      >
                        {{ getSceneryDisplayName(item) }}
                        <div
                          v-if="getCrewNamesForSettingItem(item, 'scenery', smPlanScene).length > 0"
                          class="crew-names"
                        >
                          {{ getCrewNamesForSettingItem(item, 'scenery', smPlanScene).join(', ') }}
                        </div>
                      </li>
                    </ul>
                    <p v-else class="text-muted mb-0">None</p>
                  </b-col>
                  <b-col cols="6" class="plan-content-col">
                    <ul v-if="getSettingProps(smPlanScene).length > 0" class="item-list mb-0">
                      <li v-for="item in getSettingProps(smPlanScene)" :key="`set-prop-${item.id}`">
                        {{ getPropDisplayName(item) }}
                        <div
                          v-if="getCrewNamesForSettingItem(item, 'prop', smPlanScene).length > 0"
                          class="crew-names"
                        >
                          {{ getCrewNamesForSettingItem(item, 'prop', smPlanScene).join(', ') }}
                        </div>
                      </li>
                    </ul>
                    <p v-else class="text-muted mb-0">None</p>
                  </b-col>
                </b-row>
              </b-container>
            </b-card-body>
          </b-collapse>
        </b-card>
        <b-card no-body class="mb-2">
          <b-card-header header-tag="header" class="p-2" role="button" @click="togglePlanStrike">
            <div class="d-flex justify-content-between align-items-center">
              <span>
                <b-icon :icon="smPlanStrike ? 'chevron-down' : 'chevron-right'" class="mr-1" />
                Striking
              </span>
            </div>
          </b-card-header>
          <b-collapse v-model="smPlanStrike">
            <b-card-body class="p-2">
              <b-container class="mx-0 px-0" fluid>
                <b-row class="plan-header-row">
                  <b-col cols="6" class="plan-header-col border-right">
                    <b>Scenery</b>
                  </b-col>
                  <b-col cols="6" class="plan-header-col">
                    <b>Props</b>
                  </b-col>
                </b-row>
                <b-row class="plan-content-row">
                  <b-col cols="6" class="plan-content-col border-right">
                    <ul v-if="getStrikingScenery(smPlanScene).length > 0" class="item-list mb-0">
                      <li
                        v-for="item in getStrikingScenery(smPlanScene)"
                        :key="`strike-scenery-${item.id}`"
                      >
                        {{ getSceneryDisplayName(item) }}
                        <div
                          v-if="
                            getCrewNamesForStrikingItem(item, 'scenery', smPlanScene).length > 0
                          "
                          class="crew-names"
                        >
                          {{ getCrewNamesForStrikingItem(item, 'scenery', smPlanScene).join(', ') }}
                        </div>
                      </li>
                    </ul>
                    <p v-else class="text-muted mb-0">None</p>
                  </b-col>
                  <b-col cols="6" class="plan-content-col">
                    <ul v-if="getStrikingProps(smPlanScene).length > 0" class="item-list mb-0">
                      <li
                        v-for="item in getStrikingProps(smPlanScene)"
                        :key="`strike-prop-${item.id}`"
                      >
                        {{ getPropDisplayName(item) }}
                        <div
                          v-if="getCrewNamesForStrikingItem(item, 'prop', smPlanScene).length > 0"
                          class="crew-names"
                        >
                          {{ getCrewNamesForStrikingItem(item, 'prop', smPlanScene).join(', ') }}
                        </div>
                      </li>
                    </ul>
                    <p v-else class="text-muted mb-0">None</p>
                  </b-col>
                </b-row>
              </b-container>
            </b-card-body>
          </b-collapse>
        </b-card>
      </div>
      <div v-else>
        <p>No scene selected.</p>
      </div>
    </b-modal>
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';
import { debounce } from 'lodash';
import Vue from 'vue';

export default {
  name: 'StageManagerPane',
  props: {
    sessionFollowData: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      loaded: false,
      expandedScenes: {},
      pinnedScenes: {},
      debounceContentSize: null,
      smPlanScene: null,
      smPlanSet: true,
      smPlanStrike: true,
    };
  },
  computed: {
    orderedScenes() {
      return this.ORDERED_SCENES;
    },
    currentSceneId() {
      if (!this.sessionFollowData?.current_line) {
        return null;
      }

      // Parse page_X_line_Y format
      const parts = this.sessionFollowData.current_line.split('_');
      if (parts.length < 4) {
        return null;
      }

      const pageNumber = parseInt(parts[1], 10);
      const lineIndex = parseInt(parts[3], 10);

      // Get the lines for this page
      const pageLines = this.GET_SCRIPT_PAGE(pageNumber);
      if (!pageLines || lineIndex >= pageLines.length) {
        return null;
      }

      // Return the scene_id from the current line
      return pageLines[lineIndex]?.scene_id || null;
    },
    nextSceneId() {
      if (this.currentSceneId === null) {
        return null;
      }
      const currentIndex = this.orderedScenes.findIndex((s) => s.id === this.currentSceneId);
      if (currentIndex === -1 || currentIndex >= this.orderedScenes.length - 1) {
        return null;
      }
      return this.orderedScenes[currentIndex + 1].id;
    },
    propsDict() {
      // Create a lookup dictionary for props by ID
      return Object.fromEntries(this.PROPS_LIST.map((prop) => [prop.id, prop]));
    },
    sceneryDict() {
      // Create a lookup dictionary for scenery by ID
      return Object.fromEntries(this.SCENERY_LIST.map((item) => [item.id, item]));
    },
    ...mapGetters([
      'ORDERED_SCENES',
      'ACT_BY_ID',
      'GET_SCRIPT_PAGE',
      'PROPS_ALLOCATIONS',
      'SCENERY_ALLOCATIONS',
      'PROPS_LIST',
      'SCENERY_LIST',
      'PROP_TYPES_DICT',
      'SCENERY_TYPES_DICT',
      'CREW_ASSIGNMENTS_BY_PROP',
      'CREW_ASSIGNMENTS_BY_SCENERY',
      'CREW_MEMBER_BY_ID',
    ]),
  },
  watch: {
    currentSceneId(newSceneId, oldSceneId) {
      if (newSceneId !== null && newSceneId !== oldSceneId) {
        const currentIndex = this.orderedScenes.findIndex((s) => s.id === newSceneId);

        // Determine which scenes should be auto-expanded: current + next
        const autoExpandIds = new Set([newSceneId]);
        if (currentIndex !== -1 && currentIndex < this.orderedScenes.length - 1) {
          autoExpandIds.add(this.orderedScenes[currentIndex + 1].id);
        }

        // Collapse all scenes that aren't current/next and aren't pinned
        // This handles both forward and backward navigation
        this.orderedScenes.forEach((scene) => {
          if (!autoExpandIds.has(scene.id) && !this.pinnedScenes[scene.id]) {
            Vue.set(this.expandedScenes, scene.id, false);
          }
        });

        // Expand current and next scenes
        autoExpandIds.forEach((sceneId) => {
          Vue.set(this.expandedScenes, sceneId, true);
        });

        // Auto-scroll to keep current scene visible with previous scene above
        this.$nextTick(() => {
          this.autoScrollToCurrentScene(newSceneId);
        });
      }
    },
    orderedScenes: {
      immediate: true,
      handler(scenes) {
        // Initialize expanded state for all scenes (expand first scene by default)
        scenes.forEach((scene, index) => {
          if (this.expandedScenes[scene.id] === undefined) {
            Vue.set(this.expandedScenes, scene.id, index === 0);
          }
        });
      },
    },
  },
  created() {
    this.debounceContentSize = debounce(this.computeContentSize, 100);
  },
  async mounted() {
    // Load required data
    await Promise.all([
      this.GET_ACT_LIST(),
      this.GET_SCENE_LIST(),
      this.GET_PROPS_LIST(),
      this.GET_SCENERY_LIST(),
      this.GET_PROPS_ALLOCATIONS(),
      this.GET_SCENERY_ALLOCATIONS(),
      this.GET_PROP_TYPES(),
      this.GET_SCENERY_TYPES(),
      this.GET_CREW_LIST(),
      this.GET_CREW_ASSIGNMENTS(),
    ]);
    this.loaded = true;

    // Compute initial size and listen for resize
    this.$nextTick(() => {
      this.computeContentSize();
    });
    window.addEventListener('resize', this.debounceContentSize);
  },
  destroyed() {
    window.removeEventListener('resize', this.debounceContentSize);
  },
  methods: {
    computeContentSize() {
      const container = this.$refs.paneContainer;
      if (!container) return;

      // Calculate available height from viewport minus container's top position
      const containerTop = container.getBoundingClientRect().top;
      const availableHeight = document.documentElement.clientHeight - containerTop;
      container.style.height = `${availableHeight}px`;
    },
    toggleScene(sceneId) {
      const isCurrentlyExpanded = this.expandedScenes[sceneId];
      Vue.set(this.expandedScenes, sceneId, !isCurrentlyExpanded);

      // Track pinned state: opening = pin, closing = unpin
      if (isCurrentlyExpanded) {
        // User is closing - unpin the scene
        Vue.set(this.pinnedScenes, sceneId, false);
      } else {
        // User is opening - pin the scene so it won't auto-collapse
        Vue.set(this.pinnedScenes, sceneId, true);
      }
    },
    getSceneDisplayName(scene) {
      // Scene uses 'act' field, not 'act_id'
      const act = this.ACT_BY_ID(scene.act);
      const actName = act?.name || 'Unknown Act';
      return `${actName}: ${scene.name}`;
    },
    getPropsForScene(sceneId) {
      // Filter props allocations for this scene and map to prop details
      // Note: allocation uses 'props_id' not 'prop_id'
      return this.PROPS_ALLOCATIONS.filter((alloc) => alloc.scene_id === sceneId)
        .map((alloc) => this.propsDict[alloc.props_id])
        .filter((prop) => prop != null);
    },
    getSceneryForScene(sceneId) {
      // Filter scenery allocations for this scene and map to scenery details
      return this.SCENERY_ALLOCATIONS.filter((alloc) => alloc.scene_id === sceneId)
        .map((alloc) => this.sceneryDict[alloc.scenery_id])
        .filter((scenery) => scenery != null);
    },
    getPropDisplayName(prop) {
      const propType = this.PROP_TYPES_DICT[prop.prop_type_id];
      return propType ? `${propType.name}: ${prop.name}` : prop.name;
    },
    getSceneryDisplayName(scenery) {
      const sceneryType = this.SCENERY_TYPES_DICT[scenery.scenery_type_id];
      return sceneryType ? `${sceneryType.name}: ${scenery.name}` : scenery.name;
    },
    autoScrollToCurrentScene(currentSceneId) {
      const container = this.$refs.scrollContainer;
      if (!container) return;

      // Find the index of the current scene
      const currentIndex = this.orderedScenes.findIndex((s) => s.id === currentSceneId);
      if (currentIndex === -1) return;

      // Determine target element: previous scene if exists, otherwise current scene
      let targetSceneId;
      if (currentIndex > 0) {
        // Scroll to show previous scene at top, so current scene is visible below
        targetSceneId = this.orderedScenes[currentIndex - 1].id;
      } else {
        // First scene - scroll to top
        targetSceneId = currentSceneId;
      }

      const targetRef = this.$refs[`scene-card-${targetSceneId}`];
      if (targetRef && targetRef[0]) {
        // Scroll within the container only, not the whole page
        const element = targetRef[0].$el || targetRef[0];
        const containerTop = container.getBoundingClientRect().top;
        const elementTop = element.getBoundingClientRect().top;
        const scrollOffset = elementTop - containerTop + container.scrollTop;
        container.scrollTo({ top: scrollOffset, behavior: 'smooth' });
      }
    },
    resetSMPlanScene() {
      this.smPlanScene = null;
    },
    showSMPlanModal(scene) {
      this.smPlanScene = scene;
      this.$bvModal.show('sm-plan-modal');
    },
    togglePlanSet() {
      this.smPlanSet = !this.smPlanSet;
    },
    togglePlanStrike() {
      this.smPlanStrike = !this.smPlanStrike;
    },
    getPreviousScene(scene) {
      const currentIndex = this.orderedScenes.findIndex((s) => s.id === scene.id);
      if (currentIndex <= 0) {
        return null; // First scene or not found
      }
      return this.orderedScenes[currentIndex - 1];
    },
    getSettingScenery(scene) {
      const currentScenery = this.getSceneryForScene(scene.id);
      const previousScene = this.getPreviousScene(scene);
      if (!previousScene) {
        return currentScenery; // First scene - all items are being set
      }
      const previousSceneryIds = new Set(
        this.getSceneryForScene(previousScene.id).map((s) => s.id)
      );
      return currentScenery.filter((item) => !previousSceneryIds.has(item.id));
    },
    getSettingProps(scene) {
      const currentProps = this.getPropsForScene(scene.id);
      const previousScene = this.getPreviousScene(scene);
      if (!previousScene) {
        return currentProps; // First scene - all items are being set
      }
      const previousPropsIds = new Set(this.getPropsForScene(previousScene.id).map((p) => p.id));
      return currentProps.filter((item) => !previousPropsIds.has(item.id));
    },
    getStrikingScenery(scene) {
      const previousScene = this.getPreviousScene(scene);
      if (!previousScene) {
        return []; // First scene - nothing to strike
      }
      const currentSceneryIds = new Set(this.getSceneryForScene(scene.id).map((s) => s.id));
      return this.getSceneryForScene(previousScene.id).filter(
        (item) => !currentSceneryIds.has(item.id)
      );
    },
    getStrikingProps(scene) {
      const previousScene = this.getPreviousScene(scene);
      if (!previousScene) {
        return []; // First scene - nothing to strike
      }
      const currentPropsIds = new Set(this.getPropsForScene(scene.id).map((p) => p.id));
      return this.getPropsForScene(previousScene.id).filter(
        (item) => !currentPropsIds.has(item.id)
      );
    },
    formatCrewName(crew) {
      if (!crew) return 'Unknown';
      return crew.last_name ? `${crew.first_name} ${crew.last_name}` : crew.first_name;
    },
    getCrewNamesForSettingItem(item, itemType, scene) {
      const assignments =
        itemType === 'scenery'
          ? this.CREW_ASSIGNMENTS_BY_SCENERY[item.id] || []
          : this.CREW_ASSIGNMENTS_BY_PROP[item.id] || [];
      return assignments
        .filter((a) => a.assignment_type === 'set' && a.scene_id === scene.id)
        .map((a) => this.formatCrewName(this.CREW_MEMBER_BY_ID(a.crew_id)));
    },
    getCrewNamesForStrikingItem(item, itemType, scene) {
      const previousScene = this.getPreviousScene(scene);
      if (!previousScene) return [];
      const assignments =
        itemType === 'scenery'
          ? this.CREW_ASSIGNMENTS_BY_SCENERY[item.id] || []
          : this.CREW_ASSIGNMENTS_BY_PROP[item.id] || [];
      return assignments
        .filter((a) => a.assignment_type === 'strike' && a.scene_id === previousScene.id)
        .map((a) => this.formatCrewName(this.CREW_MEMBER_BY_ID(a.crew_id)));
    },
    ...mapActions([
      'GET_ACT_LIST',
      'GET_SCENE_LIST',
      'GET_PROPS_LIST',
      'GET_SCENERY_LIST',
      'GET_PROPS_ALLOCATIONS',
      'GET_SCENERY_ALLOCATIONS',
      'GET_PROP_TYPES',
      'GET_SCENERY_TYPES',
      'GET_CREW_LIST',
      'GET_CREW_ASSIGNMENTS',
    ]),
  },
};
</script>

<style scoped>
.stage-manager-pane {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  overflow: hidden;
  background-color: var(--body-background, #222);
}

.pane-header {
  flex-shrink: 0;
  padding: 0.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background-color: rgba(0, 0, 0, 0.2);
}

.scenes-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0.5rem;
  min-height: 0;
}

.loading-state,
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  flex: 1;
  padding: 1rem;
}

.scene-card {
  background-color: #303030;
  border: 1px solid #444;
  border-radius: 0.25rem;
}

.scene-card.current-scene {
  border-color: #28a745;
  border-width: 2px;
}

.scene-card.next-scene {
  border-color: #2863a7;
  border-width: 2px;
}

.scene-header {
  cursor: pointer;
  background-color: #3a3a3a;
  border-bottom: 1px solid #444;
  transition: background-color 0.15s ease-in-out;
}

.scene-header:hover {
  background-color: #454545;
}

.current-scene .scene-header {
  background-color: #1a472a;
}

.next-scene .scene-header {
  background-color: #1a3147;
}

.current-scene .scene-header:hover {
  background-color: #215d35;
}

.next-scene .scene-header:hover {
  background-color: #28476b;
}

.scene-title {
  font-size: 0.8rem;
  font-weight: 500;
  color: #dee2e6;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.scene-badges {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.pinned-icon {
  color: #6c757d;
  font-size: 0.75rem;
}

.scene-body {
  background-color: #303030;
}

.section-label {
  display: block;
  color: #6c757d;
  font-weight: 600;
  text-transform: uppercase;
  margin-bottom: 0.25rem;
}

.item-list {
  list-style: none;
  padding-left: 0.5rem;
  margin: 0;
}

.item-list li {
  color: #adb5bd;
  padding: 0.1rem 0;
}

.empty-scene {
  color: #6c757d;
  font-style: italic;
}

.plan-header-row {
  margin: 0;
  padding: 0;
  border-bottom: 1px solid #dee2e6;
}

.plan-header-col {
  padding: 0.5rem 0.75rem;
}

.plan-header-col.border-right {
  border-right: 1px solid #dee2e6;
}

.plan-content-row {
  margin: 0;
  padding: 0;
}

.plan-content-col {
  padding: 0.5rem 0.75rem;
}

.plan-content-col.border-right {
  border-right: 1px solid #dee2e6;
}

.crew-names {
  color: #6c757d;
  font-size: 0.8rem;
  padding-left: 0.5rem;
  font-style: italic;
}
</style>
