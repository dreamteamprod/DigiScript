import { computed } from 'vue';
import { useSystemStore } from '@/stores/system';
import { useShowStore } from '@/stores/show';
import type { Act, Scene } from '@/types/api/show';

function getHeaderName(sceneId: number): string {
  return `head(${sceneId})`;
}

function getCellName(sceneId: number): string {
  return `cell(${sceneId})`;
}

export function useStatsTable() {
  const systemStore = useSystemStore();
  const showStore = useShowStore();

  const sortedActs = computed((): Act[] => {
    const show = systemStore.currentShow;
    if (show?.first_act_id == null) return [];
    let current = showStore.actById(show.first_act_id);
    const acts: Act[] = [];
    while (current != null) {
      acts.push(current);
      current = showStore.actById(current.next_act);
    }
    return acts;
  });

  const sortedScenes = computed((): Scene[] => {
    const show = systemStore.currentShow;
    if (show?.first_act_id == null) return [];
    let currentAct = showStore.actById(show.first_act_id);
    if (currentAct == null || currentAct.first_scene == null) return [];
    const scenes: Scene[] = [];
    while (currentAct != null) {
      let currentScene = showStore.sceneById(currentAct.first_scene);
      while (currentScene != null) {
        scenes.push(currentScene);
        currentScene = showStore.sceneById(currentScene.next_scene);
      }
      currentAct = showStore.actById(currentAct.next_act);
    }
    return scenes;
  });

  function numScenesPerAct(actId: number): number {
    return sortedScenes.value.filter((scene) => scene.act === actId).length;
  }

  return { sortedActs, sortedScenes, numScenesPerAct, getHeaderName, getCellName };
}
