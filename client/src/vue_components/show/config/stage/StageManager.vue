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
          <b-col cols="2" />
        </b-row>
      </div>
      <!-- Allocations card -->
      <b-card no-body class="section-card mt-2">
        <b-card-header
          class="section-card-header"
          @click="allocationsExpanded = !allocationsExpanded"
        >
          <div class="d-flex justify-content-between align-items-center">
            <span>
              Allocations
              <b-badge variant="light" class="ml-1">
                {{ currentSceneSceneryAllocations.length + currentScenePropsAllocations.length }}
              </b-badge>
            </span>
            <b-icon-chevron-down v-if="!allocationsExpanded" font-scale="0.8" />
            <b-icon-chevron-up v-else font-scale="0.8" />
          </div>
        </b-card-header>
        <b-collapse :visible="allocationsExpanded">
          <b-card-body>
            <div class="d-flex justify-content-end mb-2">
              <b-dropdown :disabled="orderedScenes.length === 0" right text="Add" variant="success">
                <b-dropdown-item-button v-b-modal.add-scenery> Scenery </b-dropdown-item-button>
                <b-dropdown-item-button v-b-modal.add-prop> Prop </b-dropdown-item-button>
              </b-dropdown>
            </div>
            <b-row>
              <b-col cols="6" style="border-right: 1px solid #dee2e6">
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
                    {{
                      SCENERY_TYPE_BY_ID(getSceneryById(data.item.scenery_id)?.scenery_type_id)
                        ?.name
                    }}
                  </template>
                  <template #cell(btn)="data">
                    <b-button
                      variant="danger"
                      size="sm"
                      @click="deleteSceneryAllocation(data.item)"
                    >
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
              <b-col cols="6">
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
          </b-card-body>
        </b-collapse>
      </b-card>

      <!-- SET card -->
      <b-card v-if="setItems.length > 0" no-body class="section-card mt-2">
        <b-card-header class="section-card-header" @click="setExpanded = !setExpanded">
          <div class="d-flex justify-content-between align-items-center">
            <span>
              SET
              <b-badge variant="light" class="ml-1">{{ setItems.length }}</b-badge>
            </span>
            <span class="d-flex align-items-center">
              <b-badge v-if="unassignedSetCount > 0" variant="warning" class="mr-1">
                {{ unassignedSetCount }} unassigned
              </b-badge>
              <b-icon-chevron-down v-if="!setExpanded" font-scale="0.8" />
              <b-icon-chevron-up v-else font-scale="0.8" />
            </span>
          </div>
        </b-card-header>
        <b-collapse :visible="setExpanded">
          <b-card-body class="crew-card-body">
            <div class="boundary-items-grid">
              <div
                v-for="item in setItems"
                :key="'set-' + item.itemType + '-' + item.itemId"
                class="boundary-item"
              >
                <div class="boundary-item-header">
                  <span class="item-name">{{ item.name }}</span>
                  <b-badge variant="secondary" pill class="ml-1">{{ item.itemType }}</b-badge>
                </div>
                <div class="assignment-list">
                  <span
                    v-for="assignment in getAssignmentsForItem(item.itemId, item.itemType, 'set')"
                    :key="assignment.id"
                    class="crew-badge"
                  >
                    {{ formatCrewName(CREW_MEMBER_BY_ID(assignment.crew_id)) }}
                    <b-button
                      variant="link"
                      size="sm"
                      class="remove-btn text-danger p-0 ml-1"
                      :disabled="savingAssignment"
                      @click="removeCrewAssignment(assignment)"
                    >
                      <b-icon-x />
                    </b-button>
                  </span>
                  <span
                    v-if="getAssignmentsForItem(item.itemId, item.itemType, 'set').length === 0"
                    class="text-muted small"
                  >
                    No crew assigned
                  </span>
                </div>
                <div class="add-crew-container mt-1">
                  <b-form-select
                    :value="newCrewSelections[crewSelectionKey(item.itemId, item.itemType, 'set')]"
                    :options="getAvailableCrewForItem(item.itemId, item.itemType, 'set')"
                    :disabled="savingAssignment"
                    size="sm"
                    class="add-crew-select"
                    @input="
                      $set(
                        newCrewSelections,
                        crewSelectionKey(item.itemId, item.itemType, 'set'),
                        $event
                      )
                    "
                  >
                    <template #first>
                      <b-form-select-option :value="null" disabled>
                        + Add crew
                      </b-form-select-option>
                    </template>
                  </b-form-select>
                  <b-button
                    v-show="newCrewSelections[crewSelectionKey(item.itemId, item.itemType, 'set')]"
                    variant="primary"
                    size="sm"
                    :disabled="savingAssignment"
                    @click="addCrewAssignment(item.itemId, item.itemType, 'set')"
                  >
                    Add
                  </b-button>
                </div>
              </div>
            </div>
          </b-card-body>
        </b-collapse>
      </b-card>

      <!-- STRIKE card -->
      <b-card v-if="strikeItems.length > 0" no-body class="section-card mt-2">
        <b-card-header class="section-card-header" @click="strikeExpanded = !strikeExpanded">
          <div class="d-flex justify-content-between align-items-center">
            <span>
              STRIKE
              <b-badge variant="light" class="ml-1">{{ strikeItems.length }}</b-badge>
            </span>
            <span class="d-flex align-items-center">
              <b-badge v-if="unassignedStrikeCount > 0" variant="warning" class="mr-1">
                {{ unassignedStrikeCount }} unassigned
              </b-badge>
              <b-icon-chevron-down v-if="!strikeExpanded" font-scale="0.8" />
              <b-icon-chevron-up v-else font-scale="0.8" />
            </span>
          </div>
        </b-card-header>
        <b-collapse :visible="strikeExpanded">
          <b-card-body class="crew-card-body">
            <div class="boundary-items-grid">
              <div
                v-for="item in strikeItems"
                :key="'strike-' + item.itemType + '-' + item.itemId"
                class="boundary-item"
              >
                <div class="boundary-item-header">
                  <span class="item-name">{{ item.name }}</span>
                  <b-badge variant="secondary" pill class="ml-1">{{ item.itemType }}</b-badge>
                </div>
                <div class="assignment-list">
                  <span
                    v-for="assignment in getAssignmentsForItem(
                      item.itemId,
                      item.itemType,
                      'strike'
                    )"
                    :key="assignment.id"
                    class="crew-badge"
                  >
                    {{ formatCrewName(CREW_MEMBER_BY_ID(assignment.crew_id)) }}
                    <b-button
                      variant="link"
                      size="sm"
                      class="remove-btn text-danger p-0 ml-1"
                      :disabled="savingAssignment"
                      @click="removeCrewAssignment(assignment)"
                    >
                      <b-icon-x />
                    </b-button>
                  </span>
                  <span
                    v-if="getAssignmentsForItem(item.itemId, item.itemType, 'strike').length === 0"
                    class="text-muted small"
                  >
                    No crew assigned
                  </span>
                </div>
                <div class="add-crew-container mt-1">
                  <b-form-select
                    :value="
                      newCrewSelections[crewSelectionKey(item.itemId, item.itemType, 'strike')]
                    "
                    :options="getAvailableCrewForItem(item.itemId, item.itemType, 'strike')"
                    :disabled="savingAssignment"
                    size="sm"
                    class="add-crew-select"
                    @input="
                      $set(
                        newCrewSelections,
                        crewSelectionKey(item.itemId, item.itemType, 'strike'),
                        $event
                      )
                    "
                  >
                    <template #first>
                      <b-form-select-option :value="null" disabled>
                        + Add crew
                      </b-form-select-option>
                    </template>
                  </b-form-select>
                  <b-button
                    v-show="
                      newCrewSelections[crewSelectionKey(item.itemId, item.itemType, 'strike')]
                    "
                    variant="primary"
                    size="sm"
                    :disabled="savingAssignment"
                    @click="addCrewAssignment(item.itemId, item.itemType, 'strike')"
                  >
                    Add
                  </b-button>
                </div>
              </div>
            </div>
          </b-card-body>
        </b-collapse>
      </b-card>
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
import { findOrphanedAssignments } from '@/js/blockOrphanUtils';

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
      savingAssignment: false,
      newCrewSelections: {},
      allocationsExpanded: true,
      setExpanded: false,
      strikeExpanded: false,
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
    previousSceneInAct() {
      if (this.currentSceneIndex <= 0 || !this.currentScene) return null;
      const prev = this.orderedScenes[this.currentSceneIndex - 1];
      return prev && prev.act === this.currentScene.act ? prev : null;
    },
    nextSceneInAct() {
      if (!this.currentScene || this.currentSceneIndex >= this.orderedScenes.length - 1)
        return null;
      const next = this.orderedScenes[this.currentSceneIndex + 1];
      return next && next.act === this.currentScene.act ? next : null;
    },
    setItems() {
      if (!this.currentScene) return [];
      const items = [];
      const sceneId = this.currentScene.id;
      const prevSceneId = this.previousSceneInAct?.id;

      for (const scenery of this.SCENERY_LIST) {
        const allocs = this.SCENERY_ALLOCATIONS_BY_ITEM[scenery.id] || [];
        const inCurrent = allocs.some((a) => a.scene_id === sceneId);
        if (!inCurrent) continue;
        const inPrev = prevSceneId && allocs.some((a) => a.scene_id === prevSceneId);
        if (!inPrev) {
          items.push({ itemId: scenery.id, itemType: 'scenery', name: scenery.name });
        }
      }

      for (const prop of this.PROPS_LIST) {
        const allocs = this.PROPS_ALLOCATIONS_BY_ITEM[prop.id] || [];
        const inCurrent = allocs.some((a) => a.scene_id === sceneId);
        if (!inCurrent) continue;
        const inPrev = prevSceneId && allocs.some((a) => a.scene_id === prevSceneId);
        if (!inPrev) {
          items.push({ itemId: prop.id, itemType: 'prop', name: prop.name });
        }
      }

      return items;
    },
    strikeItems() {
      if (!this.currentScene) return [];
      const items = [];
      const sceneId = this.currentScene.id;
      const nextSceneId = this.nextSceneInAct?.id;

      for (const scenery of this.SCENERY_LIST) {
        const allocs = this.SCENERY_ALLOCATIONS_BY_ITEM[scenery.id] || [];
        const inCurrent = allocs.some((a) => a.scene_id === sceneId);
        if (!inCurrent) continue;
        const inNext = nextSceneId && allocs.some((a) => a.scene_id === nextSceneId);
        if (!inNext) {
          items.push({ itemId: scenery.id, itemType: 'scenery', name: scenery.name });
        }
      }

      for (const prop of this.PROPS_LIST) {
        const allocs = this.PROPS_ALLOCATIONS_BY_ITEM[prop.id] || [];
        const inCurrent = allocs.some((a) => a.scene_id === sceneId);
        if (!inCurrent) continue;
        const inNext = nextSceneId && allocs.some((a) => a.scene_id === nextSceneId);
        if (!inNext) {
          items.push({ itemId: prop.id, itemType: 'prop', name: prop.name });
        }
      }

      return items;
    },
    unassignedSetCount() {
      return this.setItems.filter(
        (item) => this.getAssignmentsForItem(item.itemId, item.itemType, 'set').length === 0
      ).length;
    },
    unassignedStrikeCount() {
      return this.strikeItems.filter(
        (item) => this.getAssignmentsForItem(item.itemId, item.itemType, 'strike').length === 0
      ).length;
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
      'SCENERY_ALLOCATIONS_BY_ITEM',
      'PROPS_LIST',
      'PROP_TYPES',
      'PROP_TYPE_BY_ID',
      'PROPS_ALLOCATIONS',
      'PROPS_ALLOCATIONS_BY_ITEM',
      'CREW_LIST',
      'CREW_MEMBER_BY_ID',
      'CREW_ASSIGNMENTS_BY_PROP',
      'CREW_ASSIGNMENTS_BY_SCENERY',
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
      this.GET_CREW_LIST(),
      this.GET_CREW_ASSIGNMENTS(),
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
      const sceneryId = this.addSceneryFormState.scenery_id;
      const orphans = this.findOrphansForItem(sceneryId, 'scenery', 'add', this.currentScene.id);
      if (orphans.length > 0) {
        event.preventDefault();
        const msgVNode = this.buildOrphanWarningVNode(orphans);
        const confirmed = await this.$bvModal.msgBoxConfirm([msgVNode], {
          title: 'Crew assignments will be removed',
          okTitle: 'Continue',
          okVariant: 'warning',
        });
        if (confirmed !== true) return;
        await this.ADD_SCENERY_ALLOCATION({
          scenery_id: sceneryId,
          scene_id: this.currentScene.id,
        });
        this.resetAddSceneryForm();
        this.$bvModal.hide('add-scenery');
      } else {
        await this.ADD_SCENERY_ALLOCATION({
          scenery_id: sceneryId,
          scene_id: this.currentScene.id,
        });
        this.resetAddSceneryForm();
      }
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
      const propsId = this.addPropFormState.props_id;
      const orphans = this.findOrphansForItem(propsId, 'prop', 'add', this.currentScene.id);
      if (orphans.length > 0) {
        event.preventDefault();
        const msgVNode = this.buildOrphanWarningVNode(orphans);
        const confirmed = await this.$bvModal.msgBoxConfirm([msgVNode], {
          title: 'Crew assignments will be removed',
          okTitle: 'Continue',
          okVariant: 'warning',
        });
        if (confirmed !== true) return;
        await this.ADD_PROPS_ALLOCATION({
          props_id: propsId,
          scene_id: this.currentScene.id,
        });
        this.resetAddPropForm();
        this.$bvModal.hide('add-prop');
      } else {
        await this.ADD_PROPS_ALLOCATION({
          props_id: propsId,
          scene_id: this.currentScene.id,
        });
        this.resetAddPropForm();
      }
    },
    getAssignmentsForItem(itemId, itemType, assignmentType) {
      const assignments =
        itemType === 'prop'
          ? this.CREW_ASSIGNMENTS_BY_PROP[itemId] || []
          : this.CREW_ASSIGNMENTS_BY_SCENERY[itemId] || [];
      return assignments.filter(
        (a) => a.assignment_type === assignmentType && a.scene_id === this.currentScene?.id
      );
    },
    getAvailableCrewForItem(itemId, itemType, assignmentType) {
      const assigned = new Set(
        this.getAssignmentsForItem(itemId, itemType, assignmentType).map((a) => a.crew_id)
      );
      return this.CREW_LIST.filter((c) => !assigned.has(c.id)).map((c) => ({
        value: c.id,
        text: this.formatCrewName(c),
      }));
    },
    formatCrewName(crew) {
      if (!crew) return 'Unknown';
      return crew.last_name ? `${crew.first_name} ${crew.last_name}` : crew.first_name;
    },
    crewSelectionKey(itemId, itemType, assignmentType) {
      return `${itemType}-${itemId}-${assignmentType}`;
    },
    async addCrewAssignment(itemId, itemType, assignmentType) {
      const key = this.crewSelectionKey(itemId, itemType, assignmentType);
      const crewId = this.newCrewSelections[key];
      if (!crewId || !this.currentScene || this.savingAssignment) return;

      this.savingAssignment = true;
      try {
        const assignment = {
          crew_id: crewId,
          scene_id: this.currentScene.id,
          assignment_type: assignmentType,
        };
        if (itemType === 'prop') {
          assignment.prop_id = itemId;
        } else {
          assignment.scenery_id = itemId;
        }

        const result = await this.ADD_CREW_ASSIGNMENT(assignment);
        if (result.success) {
          this.$set(this.newCrewSelections, key, null);
        }
      } finally {
        this.savingAssignment = false;
      }
    },
    async removeCrewAssignment(assignment) {
      if (this.savingAssignment) return;

      const crew = this.CREW_MEMBER_BY_ID(assignment.crew_id);
      const crewName = this.formatCrewName(crew);
      const confirmed = await this.$bvModal.msgBoxConfirm(
        `Remove ${crewName} from this ${assignment.assignment_type.toUpperCase()} assignment?`,
        { okTitle: 'Remove', okVariant: 'danger' }
      );
      if (confirmed) {
        this.savingAssignment = true;
        try {
          await this.DELETE_CREW_ASSIGNMENT(assignment.id);
        } finally {
          this.savingAssignment = false;
        }
      }
    },
    getSceneryById(id) {
      return this.SCENERY_LIST.find((s) => s.id === id);
    },
    getPropById(id) {
      return this.PROPS_LIST.find((p) => p.id === id);
    },
    getItemAllocationsForScenery(sceneryId) {
      return this.SCENERY_ALLOCATIONS.filter((a) => a.scenery_id === sceneryId);
    },
    getItemAllocationsForProp(propId) {
      return this.PROPS_ALLOCATIONS.filter((a) => a.props_id === propId);
    },
    findOrphansForItem(itemId, itemType, changeType, sceneId) {
      const allocations =
        itemType === 'scenery'
          ? this.getItemAllocationsForScenery(itemId)
          : this.getItemAllocationsForProp(itemId);
      const crewAssignments =
        itemType === 'scenery'
          ? this.CREW_ASSIGNMENTS_BY_SCENERY[itemId] || []
          : this.CREW_ASSIGNMENTS_BY_PROP[itemId] || [];
      return findOrphanedAssignments({
        orderedScenes: this.orderedScenes,
        currentAllocations: allocations,
        crewAssignments,
        changeType,
        changeSceneId: sceneId,
      });
    },
    buildOrphanWarningVNode(orphanedAssignments) {
      const h = this.$createElement;
      const groups = {};
      for (const assignment of orphanedAssignments) {
        const itemName =
          assignment.prop_id != null
            ? this.getPropById(assignment.prop_id)?.name || 'Unknown Prop'
            : this.getSceneryById(assignment.scenery_id)?.name || 'Unknown Scenery';
        const scene = this.orderedScenes.find((s) => s.id === assignment.scene_id);
        const sceneName = scene?.name || 'Unknown Scene';
        const key = `${itemName} - ${assignment.assignment_type.toUpperCase()} (${sceneName})`;
        if (!groups[key]) groups[key] = [];
        const crew = this.CREW_MEMBER_BY_ID(assignment.crew_id);
        groups[key].push(this.formatCrewName(crew));
      }
      const items = Object.entries(groups).map(([label, names]) =>
        h('li', {}, `${label}: ${names.join(', ')}`)
      );
      return h('div', {}, [
        h('p', {}, 'This action will remove the following crew assignments:'),
        h('ul', { class: 'mb-2' }, items),
        h('p', { class: 'text-muted mb-0' }, 'You can reassign crew after the change.'),
      ]);
    },
    async deleteSceneryAllocation(allocation) {
      const scenery = this.getSceneryById(allocation.scenery_id);
      const orphans = this.findOrphansForItem(
        allocation.scenery_id,
        'scenery',
        'remove',
        this.currentScene.id
      );
      if (orphans.length > 0) {
        const msgVNode = this.buildOrphanWarningVNode(orphans);
        const action = await this.$bvModal.msgBoxConfirm([msgVNode], {
          title: 'Crew assignments will be removed',
          okTitle: 'Continue',
          okVariant: 'danger',
        });
        if (action !== true) return;
      } else {
        const msg = `Remove "${scenery?.name}" from this scene?`;
        const action = await this.$bvModal.msgBoxConfirm(msg, {});
        if (action !== true) return;
      }
      await this.DELETE_SCENERY_ALLOCATION(allocation.id);
    },
    async deletePropAllocation(allocation) {
      const prop = this.getPropById(allocation.props_id);
      const orphans = this.findOrphansForItem(
        allocation.props_id,
        'prop',
        'remove',
        this.currentScene.id
      );
      if (orphans.length > 0) {
        const msgVNode = this.buildOrphanWarningVNode(orphans);
        const action = await this.$bvModal.msgBoxConfirm([msgVNode], {
          title: 'Crew assignments will be removed',
          okTitle: 'Continue',
          okVariant: 'danger',
        });
        if (action !== true) return;
      } else {
        const msg = `Remove "${prop?.name}" from this scene?`;
        const action = await this.$bvModal.msgBoxConfirm(msg, {});
        if (action !== true) return;
      }
      await this.DELETE_PROPS_ALLOCATION(allocation.id);
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
      'GET_CREW_LIST',
      'GET_CREW_ASSIGNMENTS',
      'ADD_CREW_ASSIGNMENT',
      'DELETE_CREW_ASSIGNMENT',
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

.section-card-header {
  cursor: pointer;
  padding: 0.5rem 0.75rem;
  font-size: 0.9rem;
  font-weight: 600;
}

.crew-card-body {
  padding: 0.75rem;
}

.boundary-items-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 0.5rem;
}

.boundary-item {
  padding: 0.5rem 0.65rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

.boundary-item-header {
  margin-bottom: 0.25rem;
  font-weight: 600;
  font-size: 0.85rem;
}

.assignment-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-bottom: 0.25rem;
}

.crew-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.05);
  font-size: 0.8rem;
}

.add-crew-container {
  display: flex;
  gap: 0.4rem;
  align-items: center;
}

.add-crew-select {
  flex: 1;
}
</style>
