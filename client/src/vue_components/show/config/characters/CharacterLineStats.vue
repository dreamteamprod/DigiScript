<template>
  <b-container
    class="mx-0 px-0"
    fluid
  >
    <b-row>
      <b-col>
        <div
          v-if="!loaded"
          class="text-center center-spinner"
        >
          <b-spinner
            style="width: 10rem; height: 10rem;"
            variant="info"
          />
        </div>
        <template v-else-if="sortedScenes.length > 0">
          <b-table
            :items="tableData"
            :fields="tableFields"
            responsive
            show-empty
            sticky-header="65vh"
          >
            <template #thead-top="data">
              <b-tr>
                <b-th colspan="1">
                  <span class="sr-only">Character</span>
                </b-th>
                <template v-for="act in sortedActs">
                  <b-th
                    v-if="numScenesPerAct(act.id) > 0"
                    :key="act.id"
                    variant="primary"
                    :colspan="numScenesPerAct(act.id)"
                    class="act-header"
                  >
                    {{ act.name }}
                  </b-th>
                </template>
              </b-tr>
            </template>
            <template
              v-for="scene in sortedScenes"
              #[getHeaderName(scene.id)]="data"
            >
              {{ scene.name }}
            </template>
            <template #cell(Character)="data">
              {{ CHARACTER_BY_ID(data.item.Character).name }}
            </template>
            <template
              v-for="scene in sortedScenes"
              #[getCellName(scene.id)]="data"
            >
              <template
                v-if="getLineCountForCharacter(data.item.Character, scene.act, scene.id) > 0"
              >
                {{ getLineCountForCharacter(data.item.Character, scene.act, scene.id) }}
              </template>
            </template>
          </b-table>
        </template>
        <b v-else>Unable to get mic allocations. Ensure act and scene ordering is set.</b>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';
import { makeURL } from '@/js/utils';
import log from 'loglevel';

export default {
  name: 'CharacterLineStats',
  data() {
    return {
      loaded: false,
      characterStats: {},
    };
  },
  async mounted() {
    await this.GET_ACT_LIST();
    await this.GET_SCENE_LIST();
    await this.getCharacterStats();
    this.loaded = true;
  },
  methods: {
    numScenesPerAct(actId) {
      return this.sortedScenes.filter((scene) => scene.act === actId).length;
    },
    getHeaderName(sceneId) {
      return `head(${sceneId})`;
    },
    getCellName(sceneId) {
      return `cell(${sceneId})`;
    },
    async getCharacterStats() {
      const response = await fetch(`${makeURL('/api/v1/show/character/stats')}`);
      if (response.ok) {
        this.characterStats = await response.json();
      } else {
        log.error('Unable to get character stats!');
      }
    },
    getLineCountForCharacter(characterId, actId, sceneId) {
      if (!Object.keys(this.characterStats).includes('line_counts')) {
        return 0;
      }
      const lineCounts = this.characterStats.line_counts;
      if (Object.keys(lineCounts).includes(characterId.toString())) {
        const characterCounts = this.characterStats.line_counts[characterId];
        if (Object.keys(characterCounts).includes(actId.toString())) {
          const actCounts = characterCounts[actId];
          if (Object.keys(actCounts).includes(sceneId.toString())) {
            return actCounts[sceneId];
          }
        }
      }
      return 0;
    },
    ...mapActions(['GET_ACT_LIST', 'GET_SCENE_LIST']),
  },
  computed: {
    tableData() {
      if (!this.loaded) {
        return [];
      }
      return this.CHARACTER_LIST.map((character) => ({
        Character: character.id,
      }), this);
    },
    tableFields() {
      return ['Character', ...this.sortedScenes.map((scene) => (scene.id.toString()))];
    },
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
    ...mapGetters(['ACT_BY_ID', 'SCENE_BY_ID', 'CURRENT_SHOW', 'CHARACTER_BY_ID', 'CHARACTER_LIST']),
  },
};
</script>
