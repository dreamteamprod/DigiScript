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
                  <span class="sr-only">Cast</span>
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
            <template #cell(Cues)="data">
              {{ CUE_TYPE_BY_ID(data.item.CueType).prefix }}
            </template>
            <template
              v-for="scene in sortedScenes"
              #[getCellName(scene.id)]="data"
            >
              <template
                v-if="getCountForCueType(data.item.CueType, scene.act, scene.id) > 0"
              >
                {{ getCountForCueType(data.item.CueType, scene.act, scene.id) }}
              </template>
            </template>
          </b-table>
        </template>
        <b v-else>Unable to get cue counts. Ensure act and scene ordering is set.</b>
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
  name: 'CueCountStats',
  mixins: [statsTableMixin],
  data() {
    return {
      loaded: false,
      cueStats: {},
    };
  },
  computed: {
    tableData() {
      if (!this.loaded) {
        return [];
      }
      return this.CUE_TYPES.map((cueType) => ({
        CueType: cueType.id,
      }), this);
    },
    tableFields() {
      return ['Cues', ...this.sortedScenes.map((scene) => (scene.id.toString()))];
    },
    ...mapGetters(['CUE_TYPES', 'CUE_TYPE_BY_ID']),
  },
  methods: {
    async getStats() {
      const response = await fetch(`${makeURL('/api/v1/show/cues/stats')}`);
      if (response.ok) {
        this.cueStats = await response.json();
      } else {
        log.error('Unable to get cue stats!');
      }
    },
    getCountForCueType(cueTypeId, actId, sceneId) {
      if (!Object.keys(this.cueStats).includes('cue_counts')) {
        return 0;
      }
      const cueCounts = this.cueStats.cue_counts;
      if (Object.keys(cueCounts).includes(cueTypeId.toString())) {
        const cueTypeCounts = cueCounts[cueTypeId];
        if (Object.keys(cueTypeCounts).includes(actId.toString())) {
          const actCounts = cueTypeCounts[actId];
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
