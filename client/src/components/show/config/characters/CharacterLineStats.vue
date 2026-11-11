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
                  <span class="visually-hidden">Character</span>
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
            <template #cell(Character)="data">
              {{ showStore.characterById(data.item.Character)?.name }}
            </template>
            <template v-for="scene in sortedScenes" :key="scene.id" #[getCellName(scene.id)]="data">
              <template
                v-if="getLineCountForCharacter(data.item.Character, scene.act, scene.id) > 0"
              >
                {{ getLineCountForCharacter(data.item.Character, scene.act, scene.id) }}
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
const characterStats = ref<Record<string, unknown>>({});

const tableData = computed(() => {
  if (!loaded.value) return [];
  return showStore.characterList.map((character) => ({ Character: character.id }));
});

const tableFields = computed(() => [
  'Character',
  ...sortedScenes.value.map((scene) => scene.id.toString()),
]);

async function getStats(): Promise<void> {
  const response = await fetch(makeURL('/api/v1/show/character/stats'));
  if (response.ok) {
    characterStats.value = await response.json();
  } else {
    log.error('Unable to get character stats!');
  }
}

function getLineCountForCharacter(
  characterId: number,
  actId: number | null,
  sceneId: number
): number {
  const lineCounts = (characterStats.value as Record<string, unknown>).line_counts as
    Record<string, Record<string, Record<string, number>>> | undefined;
  if (!lineCounts) return 0;
  return lineCounts[characterId]?.[actId ?? '']?.[sceneId] ?? 0;
}

onMounted(async () => {
  await showStore.getActList();
  await showStore.getSceneList();
  await showStore.getCharacterList();
  await getStats();
  loaded.value = true;
});
</script>
