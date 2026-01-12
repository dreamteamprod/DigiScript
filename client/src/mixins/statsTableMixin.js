import { mapActions, mapGetters } from 'vuex';

/**
 * Shared mixin for stats table components that display data organized by acts and scenes.
 * Provides common logic for traversing and displaying act/scene hierarchies in table format.
 *
 * This mixin assumes the component has:
 * - A Vuex store with ACT_BY_ID, SCENE_BY_ID, and CURRENT_SHOW getters
 * - A Vuex store with GET_ACT_LIST and GET_SCENE_LIST actions
 * - A `loaded` boolean in the component's data (for loading state)
 * - A `getStats()` method that fetches component-specific statistics
 *
 * Components using this mixin should implement:
 * - data() with `loaded: false` and component-specific stats object
 * - methods.getStats() - async method to fetch stats from API
 * - computed.tableData - component-specific data formatting
 * - computed.tableFields - component-specific field names (can use this.sortedScenes)
 */
export default {
  computed: {
    /**
     * Returns acts in order by following the linked list structure.
     * Starts from first_act_id and follows next_act references.
     */
    sortedActs() {
      if (this.CURRENT_SHOW.first_act_id == null) {
        return [];
      }
      let currentAct = this.ACT_BY_ID(this.CURRENT_SHOW.first_act_id);
      if (currentAct == null) {
        return [];
      }
      const acts = [];
      while (currentAct != null) {
        acts.push(currentAct);
        currentAct = this.ACT_BY_ID(currentAct.next_act);
      }
      return acts;
    },

    /**
     * Returns scenes in order by following the linked list structure.
     * Iterates through acts, then through scenes within each act.
     */
    sortedScenes() {
      if (this.CURRENT_SHOW.first_act_id == null) {
        return [];
      }

      let currentAct = this.ACT_BY_ID(this.CURRENT_SHOW.first_act_id);
      if (currentAct == null || currentAct.first_scene == null) {
        return [];
      }

      const scenes = [];
      while (currentAct != null) {
        let currentScene = this.SCENE_BY_ID(currentAct.first_scene);
        while (currentScene != null) {
          scenes.push(currentScene);
          currentScene = this.SCENE_BY_ID(currentScene.next_scene);
        }
        currentAct = this.ACT_BY_ID(currentAct.next_act);
      }
      return scenes;
    },
    ...mapGetters(['ACT_BY_ID', 'SCENE_BY_ID', 'CURRENT_SHOW']),
  },

  async mounted() {
    await this.GET_ACT_LIST();
    await this.GET_SCENE_LIST();
    await this.getStats();
    this.loaded = true;
  },

  methods: {
    /**
     * Counts how many scenes belong to a given act.
     * Used for table header colspan calculations.
     */
    numScenesPerAct(actId) {
      return this.sortedScenes.filter((scene) => scene.act === actId).length;
    },

    /**
     * Generates the slot name for a scene's table header.
     * Used in template #[getHeaderName(scene.id)] syntax.
     */
    getHeaderName(sceneId) {
      return `head(${sceneId})`;
    },

    /**
     * Generates the slot name for a scene's table cell.
     * Used in template #[getCellName(scene.id)] syntax.
     */
    getCellName(sceneId) {
      return `cell(${sceneId})`;
    },
    ...mapActions(['GET_ACT_LIST', 'GET_SCENE_LIST']),
  },
};
