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
        <b v-else>Unable to get line counts. Ensure act and scene ordering is set.</b>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { mapGetters } from 'vuex';
import { makeURL } from '@/js/utils';
import log from 'loglevel';
import statsTableMixin from '@/mixins/statsTableMixin';

export default {
  name: 'CharacterLineStats',
  mixins: [statsTableMixin],
  data() {
    return {
      loaded: false,
      characterStats: {},
    };
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
    ...mapGetters(['CHARACTER_BY_ID', 'CHARACTER_LIST']),
  },
  methods: {
    async getStats() {
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
  },
};
</script>
