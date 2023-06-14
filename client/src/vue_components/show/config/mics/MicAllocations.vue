<template>
  <b-container
    class="mx-0 px-0"
    fluid
  >
    <b-row align-h="between">
      <b-col cols="3">
        <b-form-group
          id="mic-input-group"
          label="Microphone"
          label-for="mic-input"
          :label-cols="true"
        >
          <b-form-select
            id="mic-input"
            v-model="selectedMic"
            name="act-input"
            :options="micOptions"
            :disabled="!editMode"
          />
        </b-form-group>
      </b-col>
      <b-col
        cols="3"
      >
        <b-button-group>
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
          <b-button
            :disabled="!needsSaving || saving || !editMode"
            variant="success"
            @click.stop="saveAllocations"
          >
            Save
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
              <template v-if="editMode">
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
                <span
                  v-if="allocationByCharacter[data.item.Character][scene.id] != null"
                  :key="scene.id"
                >
                  {{ allocationByCharacter[data.item.Character][scene.id] }}
                </span>
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

export default {
  name: 'MicAllocations',
  data() {
    return {
      selectedMic: null,
      internalState: {},
      loaded: false,
      saving: false,
      editMode: true,
    };
  },
  async mounted() {
    await this.resetToStoredAlloc();
    this.loaded = true;
  },
  methods: {
    async resetToStoredAlloc() {
      await this.GET_MIC_ALLOCATIONS();
      const internalState = {};
      this.MICROPHONES.forEach(function (mic) {
        const micData = {};
        this.sortedScenes.forEach((scene) => {
          micData[scene.id] = this.allAllocations[mic.id][scene.id];
        }, this);
        internalState[mic.id] = micData;
      }, this);
      this.internalState = internalState;
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

      let disabled = false;
      // Check this mic isn't allocated to anyone else for this scene
      if (this.internalState[micId][sceneId] != null
          && this.internalState[micId][sceneId] !== characterId) {
        return true;
      }
      // Check another mic isn't already assigned for this scene
      this.MICROPHONES.map((mic) => (mic.id)).forEach((innerMicId) => {
        if (this.internalState[innerMicId][sceneId] != null
            && this.internalState[innerMicId][sceneId] === characterId
            && innerMicId !== micId) {
          disabled = true;
        }
      }, this);
      return disabled;
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
    ...mapActions(['UPDATE_MIC_ALLOCATIONS', 'GET_MIC_ALLOCATIONS']),
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
      this.CHARACTER_LIST.map((character) => (character.id)).forEach((characterId) => {
        const sceneData = {};
        this.sortedScenes.map((scene) => (scene.id)).forEach((sceneId) => {
          sceneData[sceneId] = null;
        });
        charData[characterId] = sceneData;
      }, this);
      Object.keys(this.MIC_ALLOCATIONS).forEach((micId) => {
        this.sortedScenes.map((scene) => (scene.id)).forEach((sceneId) => {
          if (this.allAllocations[micId][sceneId] != null) {
            charData[this.allAllocations[micId][sceneId]][
              sceneId] = this.MICROPHONE_BY_ID(micId).name;
          }
        }, this);
      }, this);
      return charData;
    },
    ...mapGetters(['MICROPHONES', 'CURRENT_SHOW', 'ACT_BY_ID', 'SCENE_BY_ID', 'CHARACTER_LIST',
      'CHARACTER_BY_ID', 'MIC_ALLOCATIONS', 'MICROPHONE_BY_ID']),
  },
};
</script>

<style>
.act-header {
  border-left: .1rem solid;
  border-right: .1rem solid;
  border-color: inherit;
}
</style>
