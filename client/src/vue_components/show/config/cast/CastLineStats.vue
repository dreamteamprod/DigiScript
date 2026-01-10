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
            <template #cell(Cast)="data">
              {{ CAST_BY_ID(data.item.Cast).first_name }} {{ CAST_BY_ID(data.item.Cast).last_name }}
            </template>
            <template
              v-for="scene in sortedScenes"
              #[getCellName(scene.id)]="data"
            >
              <template
                v-if="getLineCountForCast(data.item.Cast, scene.act, scene.id) > 0"
              >
                {{ getLineCountForCast(data.item.Cast, scene.act, scene.id) }}
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
  name: 'CastLineStats',
  mixins: [statsTableMixin],
  data() {
    return {
      loaded: false,
      castStats: {},
    };
  },
  computed: {
    tableData() {
      if (!this.loaded) {
        return [];
      }
      return this.CAST_LIST.map((cast) => ({
        Cast: cast.id,
      }), this);
    },
    tableFields() {
      return ['Cast', ...this.sortedScenes.map((scene) => (scene.id.toString()))];
    },
    ...mapGetters(['CAST_BY_ID', 'CAST_LIST']),
  },
  methods: {
    async getStats() {
      const response = await fetch(`${makeURL('/api/v1/show/cast/stats')}`);
      if (response.ok) {
        this.castStats = await response.json();
      } else {
        log.error('Unable to get cast stats!');
      }
    },
    getLineCountForCast(castId, actId, sceneId) {
      if (!Object.keys(this.castStats).includes('line_counts')) {
        return 0;
      }
      const lineCounts = this.castStats.line_counts;
      if (Object.keys(lineCounts).includes(castId.toString())) {
        const castCounts = this.castStats.line_counts[castId];
        if (Object.keys(castCounts).includes(actId.toString())) {
          const actCounts = castCounts[actId];
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
