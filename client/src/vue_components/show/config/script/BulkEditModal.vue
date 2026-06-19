<template>
  <b-modal
    id="bulk-edit-modal"
    title="Bulk Edit"
    size="md"
    ok-title="Apply"
    :ok-disabled="!canApply"
    @ok="handleOk"
    @hidden="reset"
  >
    <p class="text-muted small mb-3">
      Applies the selected changes to all lines from the chosen start line to end line (inclusive).
      Fill in a section to apply those changes; leave it empty to skip it.
    </p>

    <h6 class="mb-2">Act / Scene</h6>
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

    <hr />

    <h6 class="mb-2">Character Assignment</h6>
    <p class="text-muted small mb-2">Lines without the selected part will be skipped.</p>
    <b-form-group label="Part" label-for="bulk-part-input">
      <b-form-select id="bulk-part-input" v-model="selectedPartIndex" :options="partOptions" />
    </b-form-group>
    <template v-if="combinedDropdown">
      <b-form-group label="Character / Character Group" label-for="bulk-char-combined-input">
        <b-form-select
          id="bulk-char-combined-input"
          v-model="combinedValue"
          :options="combinedOptions"
          :disabled="selectedPartIndex == null"
        />
      </b-form-group>
    </template>
    <template v-else>
      <b-form-group
        v-show="selectedCharacterGroupId == null"
        label="Character"
        label-for="bulk-char-input"
      >
        <b-form-select
          id="bulk-char-input"
          v-model="selectedCharacterId"
          :options="characterOptions"
          :disabled="selectedPartIndex == null"
        />
      </b-form-group>
      <b-form-group
        v-show="selectedCharacterId == null"
        label="Character Group"
        label-for="bulk-char-group-input"
      >
        <b-form-select
          id="bulk-char-group-input"
          v-model="selectedCharacterGroupId"
          :options="characterGroupOptions"
          :disabled="selectedPartIndex == null"
        />
      </b-form-group>
    </template>
  </b-modal>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapGetters } from 'vuex';

export default defineComponent({
  name: 'BulkEditModal',
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
    characters: {
      required: true,
      type: Array,
    },
    characterGroups: {
      required: true,
      type: Array,
    },
  },
  data() {
    return {
      selectedActId: null as number | null,
      selectedSceneId: null as number | null,
      selectedPartIndex: null as number | null,
      selectedCharacterId: null as number | null,
      selectedCharacterGroupId: null as number | null,
    };
  },
  computed: {
    ...mapGetters(['USER_SETTINGS']),
    combinedDropdown(): boolean {
      return !!(this.USER_SETTINGS as { character_combined_dropdown?: boolean })
        ?.character_combined_dropdown;
    },
    validActs(): any[] {
      let startAct = (this.acts as any[]).find((act) => act.previous_act == null);
      if (this.previousLineOfStart != null && this.previousLineOfStart.act_id != null) {
        startAct = (this.acts as any[]).find((act) => act.id === this.previousLineOfStart.act_id);
      }
      const validActs: any[] = [];
      let nextAct = startAct;
      while (nextAct != null) {
        validActs.push(nextAct);
        if (this.nextLineOfEnd != null && this.nextLineOfEnd.act_id === nextAct.id) {
          break;
        }
        nextAct = (this.acts as any[]).find((act) => act.id === nextAct.next_act) || null;
      }
      return validActs;
    },
    validScenes(): any[] {
      if (this.selectedActId == null) {
        return [];
      }
      const actScenes = (this.scenes as any[]).filter((scene) => scene.act === this.selectedActId);
      let startScene = actScenes.find((scene) => scene.previous_scene == null);
      if (
        this.previousLineOfStart != null &&
        this.previousLineOfStart.act_id === this.selectedActId &&
        this.previousLineOfStart.scene_id != null
      ) {
        startScene = actScenes.find((scene) => scene.id === this.previousLineOfStart.scene_id);
      }
      const validScenes: any[] = [];
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
    actOptions(): any[] {
      return [
        { value: null, text: 'Select an act', disabled: true },
        ...this.validActs.map((act) => ({ value: act.id, text: act.name })),
      ];
    },
    sceneOptions(): any[] {
      return [
        { value: null, text: 'Select a scene', disabled: true },
        ...this.validScenes.map((scene) => ({ value: scene.id, text: scene.name })),
      ];
    },
    partOptions(): any[] {
      return [
        { value: null, text: 'Select a part', disabled: true },
        { value: 1, text: 'Part 1' },
        { value: 2, text: 'Part 2' },
        { value: 3, text: 'Part 3' },
        { value: 4, text: 'Part 4' },
      ];
    },
    characterOptions(): any[] {
      return [
        { value: null, text: 'N/A' },
        ...(this.characters as any[]).map((c) => ({ value: c.id, text: c.name })),
      ];
    },
    characterGroupOptions(): any[] {
      return [
        { value: null, text: 'N/A' },
        ...(this.characterGroups as any[]).map((g) => ({ value: g.id, text: g.name })),
      ];
    },
    combinedOptions(): any[] {
      return [
        { value: null, text: 'Select character / group', disabled: true },
        ...(this.characters as any[]).map((c) => ({ value: `c:${c.id}`, text: c.name })),
        ...(this.characterGroups as any[]).map((g) => ({ value: `g:${g.id}`, text: g.name })),
      ];
    },
    combinedValue: {
      get(): string | null {
        if (this.selectedCharacterId != null) return `c:${this.selectedCharacterId}`;
        if (this.selectedCharacterGroupId != null) return `g:${this.selectedCharacterGroupId}`;
        return null;
      },
      set(val: string | null) {
        if (val == null) {
          this.selectedCharacterId = null;
          this.selectedCharacterGroupId = null;
        } else if (val.startsWith('c:')) {
          this.selectedCharacterId = Number.parseInt(val.slice(2), 10);
          this.selectedCharacterGroupId = null;
        } else if (val.startsWith('g:')) {
          this.selectedCharacterId = null;
          this.selectedCharacterGroupId = Number.parseInt(val.slice(2), 10);
        }
      },
    },
    actSceneComplete(): boolean {
      return this.selectedActId != null && this.selectedSceneId != null;
    },
    characterComplete(): boolean {
      return (
        this.selectedPartIndex != null &&
        (this.selectedCharacterId != null || this.selectedCharacterGroupId != null)
      );
    },
    canApply(): boolean {
      return this.actSceneComplete || this.characterComplete;
    },
  },
  methods: {
    handleOk(bvModalEvt: any): void {
      bvModalEvt.preventDefault();
      if (this.canApply) {
        this.$emit('apply', {
          actId: this.actSceneComplete ? this.selectedActId : null,
          sceneId: this.actSceneComplete ? this.selectedSceneId : null,
          partIndex: this.characterComplete ? this.selectedPartIndex : null,
          characterId: this.characterComplete ? this.selectedCharacterId : null,
          characterGroupId: this.characterComplete ? this.selectedCharacterGroupId : null,
        });
      }
    },
    reset(): void {
      this.selectedActId = null;
      this.selectedSceneId = null;
      this.selectedPartIndex = null;
      this.selectedCharacterId = null;
      this.selectedCharacterGroupId = null;
    },
  },
});
</script>
