<template>
  <BContainer class="mx-0 px-0" fluid>
    <BRow>
      <BCol>
        <div v-if="!loaded" class="text-center center-spinner">
          <BSpinner style="width: 10rem; height: 10rem" variant="info" />
        </div>
        <template v-else-if="sortedScenes.length > 0">
          <BTable
            :items="tableData"
            :fields="tableFields"
            responsive
            show-empty
            sticky-header="65vh"
          >
            <template #thead-top>
              <BTr>
                <BTh colspan="1">
                  <span class="visually-hidden">Cast</span>
                </BTh>
                <template v-for="act in sortedActs" :key="act.id">
                  <BTh
                    v-if="numScenesPerAct(act.id) > 0"
                    variant="primary"
                    :colspan="numScenesPerAct(act.id)"
                    class="act-header"
                  >
                    {{ act.name }}
                  </BTh>
                </template>
              </BTr>
            </template>
            <template v-for="scene in sortedScenes" :key="scene.id" #[getHeaderName(scene.id)]>
              {{ scene.name }}
            </template>
            <template #cell(Cast)="data">
              {{ showStore.castById(data.item.Cast)?.first_name }}
              {{ showStore.castById(data.item.Cast)?.last_name }}
            </template>
            <template v-for="scene in sortedScenes" :key="scene.id" #[getCellName(scene.id)]="data">
              <template v-if="getLineCountForCast(data.item.Cast, scene.act, scene.id) > 0">
                {{ getLineCountForCast(data.item.Cast, scene.act, scene.id) }}
              </template>
            </template>
          </BTable>
        </template>
        <b v-else>Unable to get line counts. Ensure act and scene ordering is set.</b>
      </BCol>
    </BRow>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import log from 'loglevel';
import { makeURL } from '@/js/utils';
import { useShowStore } from '@/stores/show';
import { useStatsTable } from '@/composables/useStatsTable';

const showStore = useShowStore();
const { sortedActs, sortedScenes, numScenesPerAct, getHeaderName, getCellName } = useStatsTable();

const loaded = ref(false);
const castStats = ref<Record<string, unknown>>({});

const tableData = computed(() => {
  if (!loaded.value) return [];
  return showStore.castList.map((cast) => ({ Cast: cast.id }));
});

const tableFields = computed(() => [
  'Cast',
  ...sortedScenes.value.map((scene) => scene.id.toString()),
]);

async function getStats(): Promise<void> {
  const response = await fetch(makeURL('/api/v1/show/cast/stats'));
  if (response.ok) {
    castStats.value = await response.json();
  } else {
    log.error('Unable to get cast stats!');
  }
}

function getLineCountForCast(castId: number, actId: number | null, sceneId: number): number {
  const lineCounts = (castStats.value as Record<string, unknown>).line_counts as
    | Record<string, Record<string, Record<string, number>>>
    | undefined;
  if (!lineCounts) return 0;
  return lineCounts[castId]?.[actId ?? '']?.[sceneId] ?? 0;
}

onMounted(async () => {
  await showStore.getActList();
  await showStore.getSceneList();
  await showStore.getCastList();
  await getStats();
  loaded.value = true;
});
</script>
