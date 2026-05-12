<template>
  <b-container class="mx-0 px-0" fluid>
    <b-row align-h="between">
      <b-col cols="3">
        <b-form-group
          v-show="editMode"
          id="mic-input-group"
          label="Microphone"
          label-for="mic-input"
          :label-cols="true"
        >
          <b-form-select
            id="mic-input"
            v-model="selectedMic"
            name="mic-input"
            :options="micOptions"
            :disabled="!editMode || !IS_SHOW_EDITOR"
          />
        </b-form-group>
      </b-col>
      <b-col cols="6" class="text-right" style="margin-bottom: 15px">
        <b-button-group v-if="IS_SHOW_EDITOR">
          <b-dropdown v-if="editMode" right text="Options" variant="secondary">
            <b-dropdown-item-btn
              :disabled="needsSaving || saving"
              variant="info"
              @click.stop="$bvModal.show('mic-auto-populate-modal')"
            >
              Auto-Allocate
              <mic-auto-populate-modal @autoPopulateResult="onAutoPopulateResult" />
            </b-dropdown-item-btn>
            <b-dropdown-divider />
            <b-dropdown-item-btn
              variant="warning"
              :disabled="changes[selectedMic] == null || saving"
              @click.stop="resetSelectedToStoredAlloc"
            >
              Reset Current
            </b-dropdown-item-btn>
            <b-dropdown-item-btn
              variant="warning"
              :disabled="!needsSaving || saving"
              @click.stop="resetToStoredAlloc"
            >
              Reset All
            </b-dropdown-item-btn>
            <b-dropdown-divider />
            <b-dropdown-item-btn
              variant="danger"
              :disabled="saving"
              @click.stop="clearSelectedMicAllocations"
            >
              Clear Current
            </b-dropdown-item-btn>
            <b-dropdown-item-btn
              variant="danger"
              :disabled="saving"
              @click.stop="clearMicAllocations"
            >
              Clear All
            </b-dropdown-item-btn>
          </b-dropdown>
          <b-button
            v-if="editMode"
            :disabled="!needsSaving || saving || !editMode"
            variant="success"
            @click.stop="saveAllocations"
          >
            Save
          </b-button>
          <b-button
            :disabled="needsSaving || saving"
            variant="primary"
            @click.stop="editMode = !editMode"
          >
            <span v-if="editMode"> View </span>
            <span v-else> Edit </span>
          </b-button>
        </b-button-group>
      </b-col>
    </b-row>
    <b-row>
      <b-col id="allocations-table">
        <template v-if="sortedScenes.length > 0">
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
            <template v-for="scene in sortedScenes" #[getHeaderName(scene.id)]="data">
              {{ scene.name }}
            </template>
            <template #cell(Character)="data">
              <div style="display: flex; align-items: center; gap: 0.75rem">
                <span style="white-space: nowrap; flex: 1">
                  {{ CHARACTER_BY_ID(data.item.Character).name }}
                </span>
                <b-button
                  style="height: fit-content; flex-shrink: 0"
                  squared
                  :disabled="micSelectAllDisabledForCharacter(selectedMic, data.item.Character)"
                  @click.stop="toggleSelectAllAllocation(selectedMic, data.item.Character)"
                >
                  <b-icon-check-circle
                    v-if="micSelectedAllForCharacter(selectedMic, data.item.Character)"
                    variant="success"
                  />
                  <b-icon-x-circle v-else />
                </b-button>
              </div>
            </template>
            <template v-for="scene in sortedScenes" #[getCellName(scene.id)]="data">
              <template v-if="editMode && IS_SHOW_EDITOR">
                <span v-if="selectedMic == null" :key="scene.id"> N/A </span>
                <b-button
                  v-else
                  :key="scene.id"
                  squared
                  :disabled="micDisabledForCharacter(selectedMic, scene.id, data.item.Character)"
                  @click.stop="toggleAllocation(selectedMic, scene.id, data.item.Character)"
                >
                  <b-icon-check-circle
                    v-if="internalState[selectedMic][scene.id] === data.item.Character"
                    variant="success"
                  />
                  <b-icon-x-circle v-else />
                </b-button>
              </template>
              <template v-else>
                <div
                  v-if="allocationByCharacter[data.item.Character][scene.id] != null"
                  :id="`cell-${data.item.Character}-${scene.id}`"
                  :key="scene.id"
                  class="allocation-cell"
                  :class="getConflictClassForCell(data.item.Character, scene.id)"
                >
                  {{ allocationByCharacter[data.item.Character][scene.id] }}
                  <b-icon-exclamation-triangle
                    v-if="getConflictsForCell(data.item.Character, scene.id).length > 0"
                    class="conflict-icon"
                  />
                  <b-tooltip :target="`cell-${data.item.Character}-${scene.id}`" triggers="hover">
                    {{ getTooltipText(data.item.Character, scene.id) }}
                  </b-tooltip>
                </div>
              </template>
            </template>
          </b-table>
        </template>
        <b v-else>Unable to get mic allocations. Ensure act and scene ordering is set.</b>
      </b-col>
    </b-row>
  </b-container>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapActions, mapGetters } from 'vuex';
import { diff } from 'deep-object-diff';
import MicAutoPopulateModal from '@/vue_components/show/config/mics/MicAutoPopulateModal.vue';

export default defineComponent({
  name: 'MicAllocations',
  components: { MicAutoPopulateModal },
  data() {
    return {
      selectedMic: null as number | null,
      internalState: {} as Record<string | number, any>,
      loaded: false,
      saving: false,
      editMode: true,
    };
  },
  computed: {
    micOptions(): any[] {
      return [
        { value: null, text: 'N/A', disabled: true },
        ...((this as any).MICROPHONES as any[]).map((mic: any) => ({
          value: mic.id,
          text: mic.name,
        })),
      ];
    },
    tableFields(): string[] {
      return [
        'Character',
        ...((this as any).sortedScenes as any[]).map((scene: any) => scene.id.toString()),
      ];
    },
    sortedActs(): any[] {
      if ((this as any).CURRENT_SHOW.first_act_id == null) {
        return [];
      }
      let currentAct = (this as any).ACT_BY_ID((this as any).CURRENT_SHOW.first_act_id);
      if (currentAct == null) {
        return [];
      }
      const acts: any[] = [];
      while (currentAct != null) {
        acts.push(currentAct);
        currentAct = (this as any).ACT_BY_ID(currentAct.next_act);
      }
      return acts;
    },
    sortedScenes(): any[] {
      if ((this as any).CURRENT_SHOW.first_act_id == null) {
        return [];
      }

      let currentAct = (this as any).ACT_BY_ID((this as any).CURRENT_SHOW.first_act_id);
      if (currentAct == null || currentAct.first_scene == null) {
        return [];
      }

      const scenes: any[] = [];
      while (currentAct != null) {
        let currentScene = (this as any).SCENE_BY_ID(currentAct.first_scene);
        while (currentScene != null) {
          scenes.push(currentScene);
          currentScene = (this as any).SCENE_BY_ID(currentScene.next_scene);
        }
        currentAct = (this as any).ACT_BY_ID(currentAct.next_act);
      }
      return scenes;
    },
    tableData(): unknown[] {
      if (!this.loaded) {
        return [];
      }
      return ((this as any).CHARACTER_LIST as any[]).map((character: any) => ({
        Character: character.id,
      }));
    },
    allAllocations(): Record<string, any> {
      const micData: Record<string, any> = {};
      Object.keys((this as any).MIC_ALLOCATIONS).forEach((micId) => {
        const sceneData: Record<string | number, any> = {};
        const allocations = (this as any).MIC_ALLOCATIONS[micId];
        allocations.forEach((allocation: any) => {
          sceneData[allocation.scene_id] = allocation.character_id;
        });
        (this as any).sortedScenes
          .map((scene: any) => scene.id)
          .forEach((sceneId: number) => {
            if (!Object.keys(sceneData).includes(sceneId.toString())) {
              sceneData[sceneId] = null;
            }
          });
        micData[micId] = sceneData;
      });
      return micData;
    },
    changes(): Record<string, any> {
      return diff((this as any).allAllocations, this.internalState) as Record<string, any>;
    },
    needsSaving(): boolean {
      return Object.keys(this.changes).length > 0;
    },
    allocationByCharacter(): Record<string | number, any> {
      const charData: Record<string | number, any> = {};
      ((this as any).CHARACTER_LIST as any[])
        .map((character: any) => character.id)
        .forEach((characterId: number) => {
          const sceneData: Record<string | number, any> = {};
          (this as any).sortedScenes
            .map((scene: any) => scene.id)
            .forEach((sceneId: number) => {
              sceneData[sceneId] = [];
            });
          charData[characterId] = sceneData;
        });
      Object.keys((this as any).MIC_ALLOCATIONS).forEach((micId) => {
        (this as any).sortedScenes
          .map((scene: any) => scene.id)
          .forEach((sceneId: number) => {
            if ((this as any).allAllocations[micId][sceneId] != null) {
              const characterId = (this as any).allAllocations[micId][sceneId];
              charData[characterId][sceneId].push((this as any).MICROPHONE_BY_ID(micId).name);
            }
          });
      });
      Object.keys(charData).forEach((characterId) => {
        Object.keys(charData[characterId]).forEach((sceneId) => {
          const mics = charData[characterId][sceneId];
          charData[characterId][sceneId] = mics.length > 0 ? mics.join(', ') : null;
        });
      });
      return charData;
    },
    ...mapGetters([
      'MICROPHONES',
      'CURRENT_SHOW',
      'ACT_BY_ID',
      'SCENE_BY_ID',
      'CHARACTER_LIST',
      'CHARACTER_BY_ID',
      'MIC_ALLOCATIONS',
      'MICROPHONE_BY_ID',
      'IS_SHOW_EDITOR',
      'CONFLICTS_BY_SCENE',
      'CONFLICTS_BY_MIC',
    ]),
  },
  async mounted(): Promise<void> {
    await this.resetToStoredAlloc();
    if ((this as any).micOptions.length > 1) {
      this.selectedMic = (this as any).micOptions[1].value;
    }
    this.loaded = true;
  },
  methods: {
    async resetToStoredAlloc(): Promise<void> {
      await (this as any).GET_MIC_ALLOCATIONS();
      const internalState: Record<string | number, any> = {};
      ((this as any).MICROPHONES as any[]).forEach((mic: any) => {
        const micData: Record<string | number, any> = {};
        (this as any).sortedScenes.forEach((scene: any) => {
          micData[scene.id] = (this as any).allAllocations[mic.id][scene.id];
        });
        internalState[mic.id] = micData;
      });
      this.internalState = internalState;
    },
    async resetSelectedToStoredAlloc(): Promise<void> {
      if (this.selectedMic == null) {
        return;
      }
      await (this as any).GET_MIC_ALLOCATIONS();
      const micData: Record<string | number, any> = {};
      (this as any).sortedScenes.forEach((scene: any) => {
        micData[scene.id] = (this as any).allAllocations[this.selectedMic!][scene.id];
      });
      this.internalState[this.selectedMic] = micData;
    },
    clearMicAllocations(): void {
      const micData: Record<string | number, null> = {};
      (this as any).sortedScenes.forEach((scene: any) => {
        micData[scene.id] = null;
      });
      Object.keys(this.internalState).forEach((micId) => {
        this.internalState[micId] = micData;
      });
    },
    clearSelectedMicAllocations(): void {
      if (this.selectedMic == null) {
        return;
      }
      const micData: Record<string | number, null> = {};
      (this as any).sortedScenes.forEach((scene: any) => {
        micData[scene.id] = null;
      });
      this.internalState[this.selectedMic] = micData;
    },
    numScenesPerAct(actId: number): number {
      return ((this as any).sortedScenes as any[]).filter((scene: any) => scene.act === actId)
        .length;
    },
    getHeaderName(sceneId: number): string {
      return `head(${sceneId})`;
    },
    getCellName(sceneId: number): string {
      return `cell(${sceneId})`;
    },
    micDisabledForCharacter(micId: number, sceneId: number, characterId: number): boolean {
      if (this.saving) {
        return true;
      }

      if (
        this.internalState[micId][sceneId] != null &&
        this.internalState[micId][sceneId] !== characterId
      ) {
        return true;
      }

      return false;
    },
    micSelectAllDisabledForCharacter(micId: number, characterId: number): boolean {
      if (this.saving) {
        return true;
      }
      let canAssign = true;
      (this as any).sortedScenes.forEach((scene: any) => {
        if (
          this.internalState[micId][scene.id] != null &&
          this.internalState[micId][scene.id] !== characterId
        ) {
          canAssign = false;
        }
      });
      if (!canAssign) {
        return true;
      }

      ((this as any).MICROPHONES as any[]).forEach((otherMic: any) => {
        if (otherMic.id !== micId) {
          (this as any).sortedScenes.forEach((scene: any) => {
            if (this.internalState[otherMic.id][scene.id] === characterId) {
              canAssign = false;
            }
          });
        }
      });
      return !canAssign;
    },
    toggleSelectAllAllocation(micId: number, characterId: number): void {
      let allAssigned = true;
      (this as any).sortedScenes.forEach((scene: any) => {
        if (this.internalState[micId][scene.id] !== characterId) {
          allAssigned = false;
        }
      });
      (this as any).sortedScenes.forEach((scene: any) => {
        if (allAssigned) {
          this.internalState[micId][scene.id] = null;
        } else {
          this.internalState[micId][scene.id] = characterId;
        }
      });
    },
    micSelectedAllForCharacter(micId: number, characterId: number): boolean {
      let allAssigned = true;
      (this as any).sortedScenes.forEach((scene: any) => {
        if (this.internalState[micId][scene.id] !== characterId) {
          allAssigned = false;
        }
      });
      return allAssigned;
    },
    toggleAllocation(micId: number, sceneId: number, characterId: number): void {
      if (this.internalState[micId][sceneId] === characterId) {
        this.internalState[micId][sceneId] = null;
      } else if (this.internalState[micId][sceneId] === null) {
        this.internalState[micId][sceneId] = characterId;
      }
    },
    async saveAllocations(): Promise<void> {
      this.saving = true;
      await (this as any).UPDATE_MIC_ALLOCATIONS(this.changes);
      await this.resetToStoredAlloc();
      this.saving = false;
    },
    getConflictsForCell(characterId: number, sceneId: number): any[] {
      const allConflicts = (Object.values((this as any).CONFLICTS_BY_SCENE) as any[][]).flat();
      if (!allConflicts || allConflicts.length === 0) {
        return [];
      }

      return allConflicts.filter(
        (c: any) => c.adjacentSceneId === sceneId && c.adjacentCharacterId === characterId
      );
    },
    getConflictClassForCell(characterId: number, sceneId: number): string {
      const conflicts = this.getConflictsForCell(characterId, sceneId);
      if (conflicts.length === 0) return '';

      const hasWarning = conflicts.some((c: any) => c.severity === 'WARNING');
      return hasWarning ? 'conflict-warning' : 'conflict-info';
    },
    getTooltipText(characterId: number, sceneId: number): string {
      const mics: any[] = [];
      Object.keys((this as any).MIC_ALLOCATIONS).forEach((micId) => {
        if ((this as any).allAllocations[micId][sceneId] === characterId) {
          mics.push({
            id: parseInt(micId, 10),
            name: (this as any).MICROPHONE_BY_ID(micId).name,
          });
        }
      });

      const conflicts = this.getConflictsForCell(characterId, sceneId);

      let tooltipText = `Assigned mics: ${mics.map((m) => m.name).join(', ')}`;

      if (conflicts.length > 0) {
        tooltipText += '\n\nConflicts:';
        conflicts.forEach((conflict: any) => {
          const micName = (this as any).MICROPHONE_BY_ID(conflict.micId).name;
          tooltipText += `\n• ${micName}: ${conflict.message}`;
        });
      }

      return tooltipText;
    },
    onAutoPopulateResult(data: any): void {
      this.internalState = data;
    },
    ...mapActions(['UPDATE_MIC_ALLOCATIONS', 'GET_MIC_ALLOCATIONS']),
  },
});
</script>

<style scoped>
.act-header {
  border-left: 0.1rem solid;
  border-right: 0.1rem solid;
  border-color: inherit;
}

/* Conflict highlighting */
.allocation-cell {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  min-width: 3rem;
  max-width: 15rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conflict-warning {
  background-color: #ff9800;
  color: #000;
  font-weight: 500;
}

.conflict-info {
  background-color: #2196f3;
  color: #fff;
  font-weight: 500;
}

.conflict-icon {
  margin-left: 0.25rem;
  font-size: 0.875rem;
}
</style>
