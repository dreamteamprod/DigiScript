import { defineComponent } from 'vue';
import { mapActions, mapGetters } from 'vuex';
import type { Act, Scene } from '@/types/api/show';

export default defineComponent({
  computed: {
    sortedActs(): Act[] {
      const show = (this as any).CURRENT_SHOW;
      if (show?.first_act_id == null) return [];
      let currentAct: Act | null = (this as any).ACT_BY_ID(show.first_act_id);
      if (currentAct == null) return [];
      const acts: Act[] = [];
      while (currentAct != null) {
        acts.push(currentAct);
        currentAct = (this as any).ACT_BY_ID(currentAct.next_act);
      }
      return acts;
    },

    sortedScenes(): Scene[] {
      const show = (this as any).CURRENT_SHOW;
      if (show?.first_act_id == null) return [];
      let currentAct: Act | null = (this as any).ACT_BY_ID(show.first_act_id);
      if (currentAct == null || currentAct.first_scene == null) return [];
      const scenes: Scene[] = [];
      while (currentAct != null) {
        let currentScene: Scene | null = (this as any).SCENE_BY_ID(currentAct.first_scene);
        while (currentScene != null) {
          scenes.push(currentScene);
          currentScene = (this as any).SCENE_BY_ID(currentScene.next_scene);
        }
        currentAct = (this as any).ACT_BY_ID(currentAct.next_act);
      }
      return scenes;
    },
    ...mapGetters(['ACT_BY_ID', 'SCENE_BY_ID', 'CURRENT_SHOW']),
  },

  async mounted() {
    await (this as any).GET_ACT_LIST();
    await (this as any).GET_SCENE_LIST();
    await (this as any).getStats();
    (this as any).loaded = true;
  },

  methods: {
    numScenesPerAct(actId: number): number {
      return (this as any).sortedScenes.filter((scene: Scene) => scene.act === actId).length;
    },

    getHeaderName(sceneId: number): string {
      return `head(${sceneId})`;
    },

    getCellName(sceneId: number): string {
      return `cell(${sceneId})`;
    },
    ...mapActions(['GET_ACT_LIST', 'GET_SCENE_LIST']),
  },
});
