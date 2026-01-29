<template>
  <b-container class="mx-0 px-0 stage-manager-container" fluid>
    <template v-if="loaded && orderedScenes.length > 0">
      <div class="sticky-header" :style="{ top: navbarHeight + 'px' }">
        <b-row>
          <b-col cols="2">
            <b-button
              v-b-modal.go-to-scene
              :disabled="orderedScenes.length === 0"
              variant="success"
            >
              Go to Scene
            </b-button>
          </b-col>
          <b-col cols="2" style="text-align: right">
            <b-button variant="success" :disabled="currentSceneIndex === 0" @click="decrScene">
              Prev Scene
            </b-button>
          </b-col>
          <b-col cols="4">
            <b>{{ currentSceneLabel }}</b>
          </b-col>
          <b-col cols="2" style="text-align: left">
            <b-button
              variant="success"
              :disabled="
                orderedScenes.length === 0 || currentSceneIndex === orderedScenes.length - 1
              "
              @click="incrScene"
            >
              Next Scene
            </b-button>
          </b-col>
          <b-col cols="2">
            <b-dropdown :disabled="orderedScenes.length === 0" right text="Add" variant="success">
              <b-dropdown-item-button v-b-modal.add-scenery> Scenery </b-dropdown-item-button>
              <b-dropdown-item-button v-b-modal.add-prop> Prop </b-dropdown-item-button>
            </b-dropdown>
          </b-col>
        </b-row>
      </div>
      <b-row style="margin-top: 0.5rem">
        <b-col
          cols="6"
          style="border-right: 1px solid #dee2e6; margin-top: -0.5rem; padding-top: 0.5rem"
        >
          <h5>Scenery</h5>
          <b-table
            id="scenery-alloc-table"
            :items="currentSceneSceneryAllocations"
            :fields="sceneryAllocFields"
            :per-page="rowsPerPage"
            :current-page="currentSceneryAllocPage"
            show-empty
            empty-text="No scenery allocated to this scene"
          >
            <template #cell(scenery_name)="data">
              {{ getSceneryById(data.item.scenery_id)?.name }}
            </template>
            <template #cell(scenery_type)="data">
              {{ SCENERY_TYPE_BY_ID(getSceneryById(data.item.scenery_id)?.scenery_type_id)?.name }}
            </template>
            <template #cell(btn)="data">
              <b-button variant="danger" size="sm" @click="deleteSceneryAllocation(data.item)">
                Delete
              </b-button>
            </template>
          </b-table>
          <b-pagination
            v-show="currentSceneSceneryAllocations.length > rowsPerPage"
            v-model="currentSceneryAllocPage"
            :total-rows="currentSceneSceneryAllocations.length"
            :per-page="rowsPerPage"
            aria-controls="scenery-alloc-table"
            class="justify-content-center"
          />
        </b-col>
        <b-col cols="6" style="margin-top: -0.5rem; padding-top: 0.5rem">
          <h5>Props</h5>
          <b-table
            id="props-alloc-table"
            :items="currentScenePropsAllocations"
            :fields="propsAllocFields"
            :per-page="rowsPerPage"
            :current-page="currentPropsAllocPage"
            show-empty
            empty-text="No props allocated to this scene"
          >
            <template #cell(prop_name)="data">
              {{ getPropById(data.item.props_id)?.name }}
            </template>
            <template #cell(prop_type)="data">
              {{ PROP_TYPE_BY_ID(getPropById(data.item.props_id)?.prop_type_id)?.name }}
            </template>
            <template #cell(btn)="data">
              <b-button variant="danger" size="sm" @click="deletePropAllocation(data.item)">
                Delete
              </b-button>
            </template>
          </b-table>
          <b-pagination
            v-show="currentScenePropsAllocations.length > rowsPerPage"
            v-model="currentPropsAllocPage"
            :total-rows="currentScenePropsAllocations.length"
            :per-page="rowsPerPage"
            aria-controls="props-alloc-table"
            class="justify-content-center"
          />
        </b-col>
      </b-row>
      <b-modal
        id="go-to-scene"
        ref="go-to-scene"
        size="md"
        title="Go To Scene"
        @hidden="resetGoToSceneForm"
        @ok="onSubmitGoToScene"
      >
        <b-form ref="go-to-scene-form" @submit.stop.prevent="onSubmitGoToScene">
          <b-form-group id="scene-input-group" label="Scene" label-for="scene-input">
            <b-form-select
              id="scene-input"
              v-model="$v.goToSceneFormState.scene_index.$model"
              :options="sceneFormOptions"
              :state="validateGoToSceneState('scene_index')"
              aria-describedby="scene-input-feedback"
            />
            <b-form-invalid-feedback id="scene-input-feedback">
              This is a required field.
            </b-form-invalid-feedback>
          </b-form-group>
        </b-form>
      </b-modal>
      <b-modal
        id="add-scenery"
        ref="add-scenery"
        size="md"
        title="Add Scenery to Scene"
        @hidden="resetAddSceneryForm"
        @ok="onSubmitAddScenery"
      >
        <b-form ref="add-scenery-form" @submit.stop.prevent="onSubmitAddScenery">
          <b-form-group id="scenery-input-group" label="Scenery" label-for="scenery-input">
            <b-form-select
              id="scenery-input"
              v-model="$v.addSceneryFormState.scenery_id.$model"
              :state="validateAddSceneryState('scenery_id')"
              aria-describedby="scenery-input-feedback"
            >
              <template #first>
                <b-form-select-option :value="null" disabled>
                  Please select scenery...
                </b-form-select-option>
              </template>
              <b-form-select-option-group
                v-for="group in sceneryOptionsByType"
                :key="group.label"
                :label="group.label"
              >
                <b-form-select-option
                  v-for="option in group.options"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.text }}
                </b-form-select-option>
              </b-form-select-option-group>
            </b-form-select>
            <b-form-invalid-feedback id="scenery-input-feedback">
              This is a required field.
            </b-form-invalid-feedback>
          </b-form-group>
        </b-form>
      </b-modal>
      <b-modal
        id="add-prop"
        ref="add-prop"
        size="md"
        title="Add Prop to Scene"
        @hidden="resetAddPropForm"
        @ok="onSubmitAddProp"
      >
        <b-form ref="add-prop-form" @submit.stop.prevent="onSubmitAddProp">
          <b-form-group id="prop-input-group" label="Prop" label-for="prop-input">
            <b-form-select
              id="prop-input"
              v-model="$v.addPropFormState.props_id.$model"
              :state="validateAddPropState('props_id')"
              aria-describedby="prop-input-feedback"
            >
              <template #first>
                <b-form-select-option :value="null" disabled>
                  Please select a prop...
                </b-form-select-option>
              </template>
              <b-form-select-option-group
                v-for="group in propOptionsByType"
                :key="group.label"
                :label="group.label"
              >
                <b-form-select-option
                  v-for="option in group.options"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.text }}
                </b-form-select-option>
              </b-form-select-option-group>
            </b-form-select>
            <b-form-invalid-feedback id="prop-input-feedback">
              This is a required field.
            </b-form-invalid-feedback>
          </b-form-group>
        </b-form>
      </b-modal>
    </template>
    <b-row v-else>
      <b-col>
        <b-alert v-if="loaded" variant="danger" show>
          There are no scenes configured for this show.
        </b-alert>
        <div v-else class="text-center py-5">
          <b-spinner label="Loading" />
        </div>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { required } from 'vuelidate/lib/validators';
import { mapActions, mapGetters } from 'vuex';
import { notNull } from '@/js/customValidators';

export default {
  name: 'StageManager',
  data() {
    return {
      loaded: false,
      navbarHeight: 0,
      currentSceneIndex: 0,
      goToSceneFormState: {
        scene_index: null,
      },
      addSceneryFormState: { scenery_id: null },
      addPropFormState: { props_id: null },
      rowsPerPage: 10,
      currentSceneryAllocPage: 1,
      currentPropsAllocPage: 1,
      sceneryAllocFields: [
        { key: 'scenery_name', label: 'Name' },
        { key: 'scenery_type', label: 'Type' },
        { key: 'btn', label: '' },
      ],
      propsAllocFields: [
        { key: 'prop_name', label: 'Name' },
        { key: 'prop_type', label: 'Type' },
        { key: 'btn', label: '' },
      ],
    };
  },
  validations: {
    goToSceneFormState: {
      scene_index: {
        required,
        notNull,
      },
    },
    addSceneryFormState: {
      scenery_id: {
        required,
        notNull,
      },
    },
    addPropFormState: {
      props_id: {
        required,
        notNull,
      },
    },
  },
  computed: {
    orderedScenes() {
      return this.ORDERED_SCENES;
    },
    currentScene() {
      if (
        this.currentSceneIndex >= 0 &&
        this.orderedScenes.length > 0 &&
        this.currentSceneIndex < this.orderedScenes.length
      ) {
        return this.orderedScenes[this.currentSceneIndex];
      }
      return null;
    },
    currentSceneLabel() {
      if (this.currentScene != null) {
        return `${this.ACT_BY_ID(this.currentScene.act).name}: ${this.currentScene.name}`;
      }
      return 'N/A';
    },
    sceneFormOptions() {
      return [
        { value: null, text: 'Please select an option', disabled: true },
        ...this.orderedScenes.map((scene, index) => ({
          value: index,
          text: `${this.ACT_BY_ID(scene.act).name}: ${scene.name}`,
        })),
      ];
    },
    availableSceneryForScene() {
      if (!this.currentScene) return [];
      const allocatedIds = this.SCENERY_ALLOCATIONS.filter(
        (a) => a.scene_id === this.currentScene.id
      ).map((a) => a.scenery_id);
      return this.SCENERY_LIST.filter((s) => !allocatedIds.includes(s.id));
    },
    availablePropsForScene() {
      if (!this.currentScene) return [];
      const allocatedIds = this.PROPS_ALLOCATIONS.filter(
        (a) => a.scene_id === this.currentScene.id
      ).map((a) => a.props_id);
      return this.PROPS_LIST.filter((p) => !allocatedIds.includes(p.id));
    },
    sceneryOptionsByType() {
      return this.SCENERY_TYPES.map((type) => ({
        label: type.name,
        options: this.availableSceneryForScene
          .filter((s) => s.scenery_type_id === type.id)
          .map((s) => ({ value: s.id, text: s.name })),
      })).filter((group) => group.options.length > 0);
    },
    propOptionsByType() {
      return this.PROP_TYPES.map((type) => ({
        label: type.name,
        options: this.availablePropsForScene
          .filter((p) => p.prop_type_id === type.id)
          .map((p) => ({ value: p.id, text: p.name })),
      })).filter((group) => group.options.length > 0);
    },
    currentSceneSceneryAllocations() {
      if (!this.currentScene) return [];
      return this.SCENERY_ALLOCATIONS.filter((a) => a.scene_id === this.currentScene.id);
    },
    currentScenePropsAllocations() {
      if (!this.currentScene) return [];
      return this.PROPS_ALLOCATIONS.filter((a) => a.scene_id === this.currentScene.id);
    },
    ...mapGetters([
      'ORDERED_SCENES',
      'ACT_BY_ID',
      'SCENERY_LIST',
      'SCENERY_TYPES',
      'SCENERY_TYPE_BY_ID',
      'SCENERY_ALLOCATIONS',
      'PROPS_LIST',
      'PROP_TYPES',
      'PROP_TYPE_BY_ID',
      'PROPS_ALLOCATIONS',
    ]),
  },
  async mounted() {
    await Promise.all([
      this.GET_ACT_LIST(),
      this.GET_SCENE_LIST(),
      this.GET_SCENERY_TYPES(),
      this.GET_SCENERY_LIST(),
      this.GET_SCENERY_ALLOCATIONS(),
      this.GET_PROP_TYPES(),
      this.GET_PROPS_LIST(),
      this.GET_PROPS_ALLOCATIONS(),
    ]);
    this.loaded = true;
    this.calculateNavbarHeight();
  },
  created() {
    window.addEventListener('resize', this.calculateNavbarHeight);
  },
  destroyed() {
    window.removeEventListener('resize', this.calculateNavbarHeight);
  },
  methods: {
    calculateNavbarHeight() {
      const navbar = document.querySelector('.navbar');
      if (navbar) {
        this.navbarHeight = navbar.offsetHeight;
      } else {
        this.navbarHeight = 56;
      }
    },
    incrScene() {
      if (this.currentSceneIndex < this.orderedScenes.length - 1) {
        this.currentSceneIndex += 1;
      }
    },
    decrScene() {
      if (this.currentSceneIndex > 0) {
        this.currentSceneIndex -= 1;
      }
    },
    resetGoToSceneForm() {
      this.goToSceneFormState = {
        scene_index: null,
      };
      this.$nextTick(() => {
        this.$v.$reset();
      });
    },
    onSubmitGoToScene(event) {
      this.$v.goToSceneFormState.$touch();
      if (this.$v.goToSceneFormState.$anyError) {
        event.preventDefault();
      } else {
        this.currentSceneIndex = this.goToSceneFormState.scene_index;
        this.resetGoToSceneForm();
      }
    },
    validateGoToSceneState(name) {
      const { $dirty, $error } = this.$v.goToSceneFormState[name];
      return $dirty ? !$error : null;
    },
    resetAddSceneryForm() {
      this.addSceneryFormState = { scenery_id: null };
      this.$nextTick(() => {
        this.$v.addSceneryFormState.$reset();
      });
    },
    validateAddSceneryState(name) {
      const { $dirty, $error } = this.$v.addSceneryFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitAddScenery(event) {
      this.$v.addSceneryFormState.$touch();
      if (this.$v.addSceneryFormState.$anyError) {
        event.preventDefault();
        return;
      }
      await this.ADD_SCENERY_ALLOCATION({
        scenery_id: this.addSceneryFormState.scenery_id,
        scene_id: this.currentScene.id,
      });
      this.resetAddSceneryForm();
    },
    resetAddPropForm() {
      this.addPropFormState = { props_id: null };
      this.$nextTick(() => {
        this.$v.addPropFormState.$reset();
      });
    },
    validateAddPropState(name) {
      const { $dirty, $error } = this.$v.addPropFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitAddProp(event) {
      this.$v.addPropFormState.$touch();
      if (this.$v.addPropFormState.$anyError) {
        event.preventDefault();
        return;
      }
      await this.ADD_PROPS_ALLOCATION({
        props_id: this.addPropFormState.props_id,
        scene_id: this.currentScene.id,
      });
      this.resetAddPropForm();
    },
    getSceneryById(id) {
      return this.SCENERY_LIST.find((s) => s.id === id);
    },
    getPropById(id) {
      return this.PROPS_LIST.find((p) => p.id === id);
    },
    async deleteSceneryAllocation(allocation) {
      const scenery = this.getSceneryById(allocation.scenery_id);
      const msg = `Remove "${scenery?.name}" from this scene?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await this.DELETE_SCENERY_ALLOCATION(allocation.id);
      }
    },
    async deletePropAllocation(allocation) {
      const prop = this.getPropById(allocation.props_id);
      const msg = `Remove "${prop?.name}" from this scene?`;
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        await this.DELETE_PROPS_ALLOCATION(allocation.id);
      }
    },
    ...mapActions([
      'GET_ACT_LIST',
      'GET_SCENE_LIST',
      'GET_SCENERY_TYPES',
      'GET_SCENERY_LIST',
      'GET_SCENERY_ALLOCATIONS',
      'ADD_SCENERY_ALLOCATION',
      'DELETE_SCENERY_ALLOCATION',
      'GET_PROP_TYPES',
      'GET_PROPS_LIST',
      'GET_PROPS_ALLOCATIONS',
      'ADD_PROPS_ALLOCATION',
      'DELETE_PROPS_ALLOCATION',
    ]),
  },
};
</script>

<style scoped>
.stage-manager-container {
  position: relative;
}

.sticky-header {
  position: sticky;
  z-index: 100;
  padding: 10px 0;
  border-bottom: 1px solid #dee2e6;
  background: var(--body-background);
}
</style>
