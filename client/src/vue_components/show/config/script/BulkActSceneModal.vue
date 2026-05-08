<template>
  <b-modal
    id="bulk-act-scene-modal"
    title="Bulk Edit Act/Scene"
    size="md"
    ok-title="Apply"
    :ok-disabled="!canApply"
    @ok="handleOk"
    @hidden="reset"
  >
    <p class="text-muted small mb-3">
      Applies the selected act and scene to all lines from the chosen start line to end line
      (inclusive).
    </p>
    <b-form-group label="Act" label-for="bulk-act-input">
      <b-form-select
        id="bulk-act-input"
        v-model="selectedActId"
        :options="actOptions"
        @change="selectedSceneId = null"
      />
    </b-form-group>
    <b-form-group label="Scene" label-for="bulk-scene-input">
      <b-form-select
        id="bulk-scene-input"
        v-model="selectedSceneId"
        :options="sceneOptions"
        :disabled="selectedActId == null"
      />
    </b-form-group>
  </b-modal>
</template>

<script>
export default {
  name: 'BulkActSceneModal',
  events: ['apply'],
  props: {
    previousLineOfStart: {
      type: Object,
      default: null,
    },
    nextLineOfEnd: {
      type: Object,
      default: null,
    },
    acts: {
      required: true,
      type: Array,
    },
    scenes: {
      required: true,
      type: Array,
    },
  },
  data() {
    return {
      selectedActId: null,
      selectedSceneId: null,
    };
  },
  computed: {
    validActs() {
      // Same algorithm as nextActs in ScriptLineEditor — constrained by the line before
      // the start selection (lower bound) and the line after the end selection (upper bound).
      let startAct = this.acts.find((act) => act.previous_act == null);
      if (this.previousLineOfStart != null && this.previousLineOfStart.act_id != null) {
        startAct = this.acts.find((act) => act.id === this.previousLineOfStart.act_id);
      }
      const validActs = [];
      let nextAct = startAct;
      while (nextAct != null) {
        validActs.push(nextAct);
        if (this.nextLineOfEnd != null && this.nextLineOfEnd.act_id === nextAct.id) {
          break;
        }
        nextAct = this.acts.find((act) => act.id === nextAct.next_act) || null;
      }
      return validActs;
    },
    validScenes() {
      if (this.selectedActId == null) {
        return [];
      }
      const actScenes = this.scenes.filter((scene) => scene.act === this.selectedActId);
      let startScene = actScenes.find((scene) => scene.previous_scene == null);
      if (
        this.previousLineOfStart != null &&
        this.previousLineOfStart.act_id === this.selectedActId &&
        this.previousLineOfStart.scene_id != null
      ) {
        startScene = actScenes.find((scene) => scene.id === this.previousLineOfStart.scene_id);
      }
      const validScenes = [];
      let nextScene = startScene;
      while (nextScene != null) {
        validScenes.push(nextScene);
        if (this.nextLineOfEnd != null && this.nextLineOfEnd.scene_id === nextScene.id) {
          break;
        }
        nextScene = actScenes.find((scene) => scene.id === nextScene.next_scene) || null;
      }
      return validScenes;
    },
    actOptions() {
      return [
        { value: null, text: 'Select an act', disabled: true },
        ...this.validActs.map((act) => ({ value: act.id, text: act.name })),
      ];
    },
    sceneOptions() {
      return [
        { value: null, text: 'Select a scene', disabled: true },
        ...this.validScenes.map((scene) => ({ value: scene.id, text: scene.name })),
      ];
    },
    canApply() {
      return this.selectedActId != null && this.selectedSceneId != null;
    },
  },
  methods: {
    handleOk(bvModalEvt) {
      bvModalEvt.preventDefault();
      if (this.canApply) {
        this.$emit('apply', { actId: this.selectedActId, sceneId: this.selectedSceneId });
      }
    },
    reset() {
      this.selectedActId = null;
      this.selectedSceneId = null;
    },
  },
};
</script>
