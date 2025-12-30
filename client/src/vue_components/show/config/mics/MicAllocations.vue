<template>
  <b-container
    class="mx-0 px-0"
    fluid
  >
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
      <b-col
        cols="6"
        class="text-right"
        style="margin-bottom: 15px"
      >
        <b-button-group v-if="IS_SHOW_EDITOR">
          <b-dropdown
            v-if="editMode"
            right
            text="Options"
            variant="secondary"
          >
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
            <span v-if="editMode">
              View
            </span>
            <span v-else>
              Edit
            </span>
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
              <template v-if="editMode && IS_SHOW_EDITOR">
                <span
                  v-if="selectedMic == null"
                  :key="scene.id"
                >
                  N/A
                </span>
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
                  <b-tooltip
                    :target="`cell-${data.item.Character}-${scene.id}`"
                    triggers="hover"
                  >
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

<script>
import { mapActions, mapGetters } from 'vuex';
import { diff } from 'deep-object-diff';
import MicAutoPopulateModal from '@/vue_components/show/config/mics/MicAutoPopulateModal.vue';

export default {
  name: 'MicAllocations',
  components: { MicAutoPopulateModal },
  data() {
    return {
      selectedMic: null,
      internalState: {},
      loaded: false,
      saving: false,
      editMode: true,
    };
  },
  computed: {
    micOptions() {
      return [
        { value: null, text: 'N/A', disabled: true },
        ...this.MICROPHONES.map((mic) => ({ value: mic.id, text: mic.name })),
      ];
    },
    tableFields() {
      return ['Character', ...this.sortedScenes.map((scene) => (scene.id.toString()))];
    },
    sortedActs() {
      if (this.CURRENT_SHOW.first_act_id == null) {
        return [];
      }
      let currentAct = this.ACT_BY_ID(this.CURRENT_SHOW.first_act_id);
      if (currentAct == null) {
        return [];
      }
      const acts = [];
      while (currentAct != null) {
        acts.push(currentAct);
        currentAct = this.ACT_BY_ID(currentAct.next_act);
      }
      return acts;
    },
    sortedScenes() {
      if (this.CURRENT_SHOW.first_act_id == null) {
        return [];
      }

      let currentAct = this.ACT_BY_ID(this.CURRENT_SHOW.first_act_id);
      if (currentAct == null || currentAct.first_scene == null) {
        return [];
      }

      const scenes = [];
      while (currentAct != null) {
        let currentScene = this.SCENE_BY_ID(currentAct.first_scene);
        while (currentScene != null) {
          scenes.push(currentScene);
          currentScene = this.SCENE_BY_ID(currentScene.next_scene);
        }
        currentAct = this.ACT_BY_ID(currentAct.next_act);
      }
      return scenes;
    },
    tableData() {
      if (!this.loaded) {
        return [];
      }
      return this.CHARACTER_LIST.map((character) => ({
        Character: character.id,
      }), this);
    },
    allAllocations() {
      const micData = {};
      Object.keys(this.MIC_ALLOCATIONS).forEach((micId) => {
        const sceneData = {};
        const allocations = this.MIC_ALLOCATIONS[micId];
        allocations.forEach((allocation) => {
          sceneData[allocation.scene_id] = allocation.character_id;
        });
        this.sortedScenes.map((scene) => (scene.id)).forEach((sceneId) => {
          if (!Object.keys(sceneData).includes(sceneId.toString())) {
            sceneData[sceneId] = null;
          }
        });
        micData[micId] = sceneData;
      }, this);
      return micData;
    },
    changes() {
      return diff(this.allAllocations, this.internalState);
    },
    needsSaving() {
      return Object.keys(this.changes).length > 0;
    },
    allocationByCharacter() {
      const charData = {};
      // Initialize with empty arrays for each character/scene combination
      this.CHARACTER_LIST.map((character) => (character.id)).forEach((characterId) => {
        const sceneData = {};
        this.sortedScenes.map((scene) => (scene.id)).forEach((sceneId) => {
          sceneData[sceneId] = [];
        });
        charData[characterId] = sceneData;
      }, this);
      // Collect all mics assigned to each character in each scene
      Object.keys(this.MIC_ALLOCATIONS).forEach((micId) => {
        this.sortedScenes.map((scene) => (scene.id)).forEach((sceneId) => {
          if (this.allAllocations[micId][sceneId] != null) {
            const characterId = this.allAllocations[micId][sceneId];
            charData[characterId][sceneId].push(this.MICROPHONE_BY_ID(micId).name);
          }
        }, this);
      }, this);
      // Convert arrays to comma-separated strings (or null if empty)
      Object.keys(charData).forEach((characterId) => {
        Object.keys(charData[characterId]).forEach((sceneId) => {
          const mics = charData[characterId][sceneId];
          charData[characterId][sceneId] = mics.length > 0 ? mics.join(', ') : null;
        });
      });
      return charData;
    },
    ...mapGetters(['MICROPHONES', 'CURRENT_SHOW', 'ACT_BY_ID', 'SCENE_BY_ID', 'CHARACTER_LIST',
      'CHARACTER_BY_ID', 'MIC_ALLOCATIONS', 'MICROPHONE_BY_ID', 'IS_SHOW_EDITOR',
      'CONFLICTS_BY_SCENE', 'CONFLICTS_BY_MIC']),
  },
  async mounted() {
    await this.resetToStoredAlloc();
    if (this.micOptions.length > 1) {
      this.selectedMic = this.micOptions[1].value;
    }
    this.loaded = true;
  },
  methods: {
    async resetToStoredAlloc() {
      await this.GET_MIC_ALLOCATIONS();
      const internalState = {};
      this.MICROPHONES.forEach(function resetMic(mic) {
        const micData = {};
        this.sortedScenes.forEach((scene) => {
          micData[scene.id] = this.allAllocations[mic.id][scene.id];
        }, this);
        internalState[mic.id] = micData;
      }, this);
      this.internalState = internalState;
    },
    async resetSelectedToStoredAlloc() {
      if (this.selectedMic == null) {
        return;
      }
      await this.GET_MIC_ALLOCATIONS();
      const micData = {};
      this.sortedScenes.forEach((scene) => {
        micData[scene.id] = this.allAllocations[this.selectedMic][scene.id];
      }, this);
      this.internalState[this.selectedMic] = micData;
    },
    clearMicAllocations() {
      const micData = {};
      this.sortedScenes.forEach((scene) => {
        micData[scene.id] = null;
      }, this);
      Object.keys(this.internalState).forEach((micId) => {
        this.internalState[micId] = micData;
      }, this);
    },
    clearSelectedMicAllocations() {
      if (this.selectedMic == null) {
        return;
      }
      const micData = {};
      this.sortedScenes.forEach((scene) => {
        micData[scene.id] = null;
      }, this);
      this.internalState[this.selectedMic] = micData;
    },
    numScenesPerAct(actId) {
      return this.sortedScenes.filter((scene) => scene.act === actId).length;
    },
    getHeaderName(sceneId) {
      return `head(${sceneId})`;
    },
    getCellName(sceneId) {
      return `cell(${sceneId})`;
    },
    micDisabledForCharacter(micId, sceneId, characterId) {
      if (this.saving) {
        return true;
      }

      // Check this mic isn't allocated to anyone else for this scene
      if (this.internalState[micId][sceneId] != null
          && this.internalState[micId][sceneId] !== characterId) {
        return true;
      }

      return false;
    },
    toggleAllocation(micId, sceneId, characterId) {
      if (this.internalState[micId][sceneId] === characterId) {
        this.internalState[micId][sceneId] = null;
      } else if (this.internalState[micId][sceneId] === null) {
        this.internalState[micId][sceneId] = characterId;
      }
    },
    async saveAllocations() {
      this.saving = true;
      await this.UPDATE_MIC_ALLOCATIONS(this.changes);
      await this.resetToStoredAlloc();
      this.saving = false;
    },
    getConflictsForCell(characterId, sceneId) {
      // Find all conflicts for this character in this scene (across all their mics)
      const allConflicts = Object.values(this.CONFLICTS_BY_SCENE).flat();
      if (!allConflicts || allConflicts.length === 0) {
        return [];
      }

      // Find all conflicts where this scene is the "change INTO" scene for this character
      return allConflicts.filter((c) => c.adjacentSceneId === sceneId
        && c.adjacentCharacterId === characterId);
    },
    getConflictClassForCell(characterId, sceneId) {
      const conflicts = this.getConflictsForCell(characterId, sceneId);
      if (conflicts.length === 0) return '';

      // Prioritize WARNING over INFO
      const hasWarning = conflicts.some((c) => c.severity === 'WARNING');
      return hasWarning ? 'conflict-warning' : 'conflict-info';
    },
    getTooltipText(characterId, sceneId) {
      // Get all mics assigned to this character in this scene
      const mics = [];
      Object.keys(this.MIC_ALLOCATIONS).forEach((micId) => {
        if (this.allAllocations[micId][sceneId] === characterId) {
          mics.push({
            id: parseInt(micId, 10),
            name: this.MICROPHONE_BY_ID(micId).name,
          });
        }
      });

      // Get conflicts for this character/scene
      const conflicts = this.getConflictsForCell(characterId, sceneId);

      // Build tooltip text
      let tooltipText = `Assigned mics: ${mics.map((m) => m.name).join(', ')}`;

      if (conflicts.length > 0) {
        tooltipText += '\n\nConflicts:';
        conflicts.forEach((conflict) => {
          const micName = this.MICROPHONE_BY_ID(conflict.micId).name;
          tooltipText += `\n• ${micName}: ${conflict.message}`;
        });
      }

      return tooltipText;
    },
    onAutoPopulateResult(data) {
      this.internalState = data;
    },
    ...mapActions(['UPDATE_MIC_ALLOCATIONS', 'GET_MIC_ALLOCATIONS']),
  },
};
</script>

<style scoped>
.act-header {
  border-left: .1rem solid;
  border-right: .1rem solid;
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
