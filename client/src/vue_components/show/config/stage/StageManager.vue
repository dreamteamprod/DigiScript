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

<script lang="ts">
import { defineComponent } from 'vue';
import { required } from 'vuelidate/lib/validators';
import { mapActions, mapGetters } from 'vuex';
import { notNull } from '@/js/customValidators';
import { findOrphanedAssignments } from '@/js/blockOrphanUtils';

export default defineComponent({
  name: 'StageManager',
  data() {
    return {
      loaded: false,
      navbarHeight: 0,
      currentSceneIndex: 0,
      goToSceneFormState: {
        scene_index: null as number | null,
      },
      addSceneryFormState: { scenery_id: null as number | null },
      addPropFormState: { props_id: null as number | null },
      savingAssignment: false,
      newCrewSelections: {} as Record<string, number | null>,
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
    orderedScenes(): any[] {
      return (this as any).ORDERED_SCENES;
    },
    currentScene(): any {
      if (
        this.currentSceneIndex >= 0 &&
        this.orderedScenes.length > 0 &&
        this.currentSceneIndex < this.orderedScenes.length
      ) {
        return this.orderedScenes[this.currentSceneIndex];
      }
      return null;
    },
    currentSceneLabel(): string {
      if (this.currentScene != null) {
        return `${(this as any).ACT_BY_ID(this.currentScene.act).name}: ${this.currentScene.name}`;
      }
      return 'N/A';
    },
    sceneFormOptions(): any[] {
      return [
        { value: null, text: 'Please select an option', disabled: true },
        ...this.orderedScenes.map((scene: any, index: number) => ({
          value: index,
          text: `${(this as any).ACT_BY_ID(scene.act).name}: ${scene.name}`,
        })),
      ];
    },
    availableSceneryForScene(): any[] {
      if (!this.currentScene) return [];
      const allocatedIds = (this as any).SCENERY_ALLOCATIONS.filter(
        (a: any) => a.scene_id === this.currentScene.id
      ).map((a: any) => a.scenery_id);
      return (this as any).SCENERY_LIST.filter((s: any) => !allocatedIds.includes(s.id));
    },
    availablePropsForScene(): any[] {
      if (!this.currentScene) return [];
      const allocatedIds = (this as any).PROPS_ALLOCATIONS.filter(
        (a: any) => a.scene_id === this.currentScene.id
      ).map((a: any) => a.props_id);
      return (this as any).PROPS_LIST.filter((p: any) => !allocatedIds.includes(p.id));
    },
    sceneryOptionsByType(): any[] {
      return (this as any).SCENERY_TYPES.map((type: any) => ({
        label: type.name,
        options: this.availableSceneryForScene
          .filter((s: any) => s.scenery_type_id === type.id)
          .map((s: any) => ({ value: s.id, text: s.name })),
      })).filter((group: any) => group.options.length > 0);
    },
    propOptionsByType(): any[] {
      return (this as any).PROP_TYPES.map((type: any) => ({
        label: type.name,
        options: this.availablePropsForScene
          .filter((p: any) => p.prop_type_id === type.id)
          .map((p: any) => ({ value: p.id, text: p.name })),
      })).filter((group: any) => group.options.length > 0);
    },
    previousSceneInAct(): any {
      if (this.currentSceneIndex <= 0 || !this.currentScene) return null;
      const prev = this.orderedScenes[this.currentSceneIndex - 1];
      return prev && prev.act === this.currentScene.act ? prev : null;
    },
    nextSceneInAct(): any {
      if (!this.currentScene || this.currentSceneIndex >= this.orderedScenes.length - 1)
        return null;
      const next = this.orderedScenes[this.currentSceneIndex + 1];
      return next && next.act === this.currentScene.act ? next : null;
    },
    setItems(): any[] {
      if (!this.currentScene) return [];
      const items: any[] = [];
      const sceneId = this.currentScene.id;
      const prevSceneId = this.previousSceneInAct?.id;

      for (const scenery of (this as any).SCENERY_LIST) {
        const allocs = (this as any).SCENERY_ALLOCATIONS_BY_ITEM[scenery.id] || [];
        const inCurrent = allocs.some((a: any) => a.scene_id === sceneId);
        if (!inCurrent) continue;
        const inPrev = prevSceneId && allocs.some((a: any) => a.scene_id === prevSceneId);
        if (!inPrev) {
          items.push({ itemId: scenery.id, itemType: 'scenery', name: scenery.name });
        }
      }

      for (const prop of (this as any).PROPS_LIST) {
        const allocs = (this as any).PROPS_ALLOCATIONS_BY_ITEM[prop.id] || [];
        const inCurrent = allocs.some((a: any) => a.scene_id === sceneId);
        if (!inCurrent) continue;
        const inPrev = prevSceneId && allocs.some((a: any) => a.scene_id === prevSceneId);
        if (!inPrev) {
          items.push({ itemId: prop.id, itemType: 'prop', name: prop.name });
        }
      }

      return items;
    },
    strikeItems(): any[] {
      if (!this.currentScene) return [];
      const items: any[] = [];
      const sceneId = this.currentScene.id;
      const nextSceneId = this.nextSceneInAct?.id;

      for (const scenery of (this as any).SCENERY_LIST) {
        const allocs = (this as any).SCENERY_ALLOCATIONS_BY_ITEM[scenery.id] || [];
        const inCurrent = allocs.some((a: any) => a.scene_id === sceneId);
        if (!inCurrent) continue;
        const inNext = nextSceneId && allocs.some((a: any) => a.scene_id === nextSceneId);
        if (!inNext) {
          items.push({ itemId: scenery.id, itemType: 'scenery', name: scenery.name });
        }
      }

      for (const prop of (this as any).PROPS_LIST) {
        const allocs = (this as any).PROPS_ALLOCATIONS_BY_ITEM[prop.id] || [];
        const inCurrent = allocs.some((a: any) => a.scene_id === sceneId);
        if (!inCurrent) continue;
        const inNext = nextSceneId && allocs.some((a: any) => a.scene_id === nextSceneId);
        if (!inNext) {
          items.push({ itemId: prop.id, itemType: 'prop', name: prop.name });
        }
      }

      return items;
    },
    unassignedSetCount(): number {
      return this.setItems.filter(
        (item: any) => this.getAssignmentsForItem(item.itemId, item.itemType, 'set').length === 0
      ).length;
    },
    unassignedStrikeCount(): number {
      return this.strikeItems.filter(
        (item: any) => this.getAssignmentsForItem(item.itemId, item.itemType, 'strike').length === 0
      ).length;
    },
    currentSceneSceneryAllocations(): any[] {
      if (!this.currentScene) return [];
      return (this as any).SCENERY_ALLOCATIONS.filter(
        (a: any) => a.scene_id === this.currentScene.id
      );
    },
    currentScenePropsAllocations(): any[] {
      if (!this.currentScene) return [];
      return (this as any).PROPS_ALLOCATIONS.filter(
        (a: any) => a.scene_id === this.currentScene.id
      );
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
  async mounted(): Promise<void> {
    await Promise.all([
      (this as any).GET_ACT_LIST(),
      (this as any).GET_SCENE_LIST(),
      (this as any).GET_SCENERY_TYPES(),
      (this as any).GET_SCENERY_LIST(),
      (this as any).GET_SCENERY_ALLOCATIONS(),
      (this as any).GET_PROP_TYPES(),
      (this as any).GET_PROPS_LIST(),
      (this as any).GET_PROPS_ALLOCATIONS(),
      (this as any).GET_CREW_LIST(),
      (this as any).GET_CREW_ASSIGNMENTS(),
    ]);
    this.loaded = true;
    this.calculateNavbarHeight();
  },
  created(): void {
    window.addEventListener('resize', this.calculateNavbarHeight);
  },
  destroyed(): void {
    window.removeEventListener('resize', this.calculateNavbarHeight);
  },
  methods: {
    calculateNavbarHeight(): void {
      const navbar = document.querySelector('.navbar') as HTMLElement | null;
      if (navbar) {
        this.navbarHeight = navbar.offsetHeight;
      } else {
        this.navbarHeight = 56;
      }
    },
    incrScene(): void {
      if (this.currentSceneIndex < this.orderedScenes.length - 1) {
        this.currentSceneIndex += 1;
      }
    },
    decrScene(): void {
      if (this.currentSceneIndex > 0) {
        this.currentSceneIndex -= 1;
      }
    },
    resetGoToSceneForm(): void {
      this.goToSceneFormState = { scene_index: null };
      this.$nextTick(() => {
        (this as any).$v.$reset();
      });
    },
    onSubmitGoToScene(event: Event): void {
      (this as any).$v.goToSceneFormState.$touch();
      if ((this as any).$v.goToSceneFormState.$anyError) {
        event.preventDefault();
      } else {
        this.currentSceneIndex = this.goToSceneFormState.scene_index!;
        this.resetGoToSceneForm();
      }
    },
    validateGoToSceneState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.goToSceneFormState[name];
      return $dirty ? !$error : null;
    },
    resetAddSceneryForm(): void {
      this.addSceneryFormState = { scenery_id: null };
      this.$nextTick(() => {
        (this as any).$v.addSceneryFormState.$reset();
      });
    },
    validateAddSceneryState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.addSceneryFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitAddScenery(event: Event): Promise<void> {
      (this as any).$v.addSceneryFormState.$touch();
      if ((this as any).$v.addSceneryFormState.$anyError) {
        event.preventDefault();
        return;
      }
      const sceneryId = this.addSceneryFormState.scenery_id;
      const orphans = this.findOrphansForItem(sceneryId, 'scenery', 'add', this.currentScene.id);
      if (orphans.length > 0) {
        event.preventDefault();
        const msgVNode = this.buildOrphanWarningVNode(orphans);
        const confirmed = await (this as any).$bvModal.msgBoxConfirm([msgVNode], {
          title: 'Crew assignments will be removed',
          okTitle: 'Continue',
          okVariant: 'warning',
        });
        if (confirmed !== true) return;
        await (this as any).ADD_SCENERY_ALLOCATION({
          scenery_id: sceneryId,
          scene_id: this.currentScene.id,
        });
        this.resetAddSceneryForm();
        (this as any).$bvModal.hide('add-scenery');
      } else {
        await (this as any).ADD_SCENERY_ALLOCATION({
          scenery_id: sceneryId,
          scene_id: this.currentScene.id,
        });
        this.resetAddSceneryForm();
      }
    },
    resetAddPropForm(): void {
      this.addPropFormState = { props_id: null };
      this.$nextTick(() => {
        (this as any).$v.addPropFormState.$reset();
      });
    },
    validateAddPropState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.addPropFormState[name];
      return $dirty ? !$error : null;
    },
    async onSubmitAddProp(event: Event): Promise<void> {
      (this as any).$v.addPropFormState.$touch();
      if ((this as any).$v.addPropFormState.$anyError) {
        event.preventDefault();
        return;
      }
      const propsId = this.addPropFormState.props_id;
      const orphans = this.findOrphansForItem(propsId, 'prop', 'add', this.currentScene.id);
      if (orphans.length > 0) {
        event.preventDefault();
        const msgVNode = this.buildOrphanWarningVNode(orphans);
        const confirmed = await (this as any).$bvModal.msgBoxConfirm([msgVNode], {
          title: 'Crew assignments will be removed',
          okTitle: 'Continue',
          okVariant: 'warning',
        });
        if (confirmed !== true) return;
        await (this as any).ADD_PROPS_ALLOCATION({
          props_id: propsId,
          scene_id: this.currentScene.id,
        });
        this.resetAddPropForm();
        (this as any).$bvModal.hide('add-prop');
      } else {
        await (this as any).ADD_PROPS_ALLOCATION({
          props_id: propsId,
          scene_id: this.currentScene.id,
        });
        this.resetAddPropForm();
      }
    },
    getAssignmentsForItem(itemId: number, itemType: string, assignmentType: string): any[] {
      const assignments =
        itemType === 'prop'
          ? (this as any).CREW_ASSIGNMENTS_BY_PROP[itemId] || []
          : (this as any).CREW_ASSIGNMENTS_BY_SCENERY[itemId] || [];
      return assignments.filter(
        (a: any) => a.assignment_type === assignmentType && a.scene_id === this.currentScene?.id
      );
    },
    getAvailableCrewForItem(itemId: number, itemType: string, assignmentType: string): any[] {
      const assigned = new Set(
        this.getAssignmentsForItem(itemId, itemType, assignmentType).map((a: any) => a.crew_id)
      );
      return (this as any).CREW_LIST.filter((c: any) => !assigned.has(c.id)).map((c: any) => ({
        value: c.id,
        text: this.formatCrewName(c),
      }));
    },
    formatCrewName(crew: any): string {
      if (!crew) return 'Unknown';
      return crew.last_name ? `${crew.first_name} ${crew.last_name}` : crew.first_name;
    },
    crewSelectionKey(itemId: number, itemType: string, assignmentType: string): string {
      return `${itemType}-${itemId}-${assignmentType}`;
    },
    async addCrewAssignment(
      itemId: number,
      itemType: string,
      assignmentType: string
    ): Promise<void> {
      const key = this.crewSelectionKey(itemId, itemType, assignmentType);
      const crewId = this.newCrewSelections[key];
      if (!crewId || !this.currentScene || this.savingAssignment) return;

      this.savingAssignment = true;
      try {
        const assignment: any = {
          crew_id: crewId,
          scene_id: this.currentScene.id,
          assignment_type: assignmentType,
        };
        if (itemType === 'prop') {
          assignment.prop_id = itemId;
        } else {
          assignment.scenery_id = itemId;
        }

        const result = await (this as any).ADD_CREW_ASSIGNMENT(assignment);
        if (result.success) {
          this.$set(this.newCrewSelections, key, null);
        }
      } finally {
        this.savingAssignment = false;
      }
    },
    async removeCrewAssignment(assignment: any): Promise<void> {
      if (this.savingAssignment) return;

      const crew = (this as any).CREW_MEMBER_BY_ID(assignment.crew_id);
      const crewName = this.formatCrewName(crew);
      const confirmed = await (this as any).$bvModal.msgBoxConfirm(
        `Remove ${crewName} from this ${assignment.assignment_type.toUpperCase()} assignment?`,
        { okTitle: 'Remove', okVariant: 'danger' }
      );
      if (confirmed) {
        this.savingAssignment = true;
        try {
          await (this as any).DELETE_CREW_ASSIGNMENT(assignment.id);
        } finally {
          this.savingAssignment = false;
        }
      }
    },
    getSceneryById(id: number): any {
      return (this as any).SCENERY_LIST.find((s: any) => s.id === id);
    },
    getPropById(id: number): any {
      return (this as any).PROPS_LIST.find((p: any) => p.id === id);
    },
    getItemAllocationsForScenery(sceneryId: number): any[] {
      return (this as any).SCENERY_ALLOCATIONS.filter((a: any) => a.scenery_id === sceneryId);
    },
    getItemAllocationsForProp(propId: number): any[] {
      return (this as any).PROPS_ALLOCATIONS.filter((a: any) => a.props_id === propId);
    },
    findOrphansForItem(
      itemId: number | null,
      itemType: string,
      changeType: string,
      sceneId: number
    ): any[] {
      const allocations =
        itemType === 'scenery'
          ? this.getItemAllocationsForScenery(itemId!)
          : this.getItemAllocationsForProp(itemId!);
      const crewAssignments =
        itemType === 'scenery'
          ? (this as any).CREW_ASSIGNMENTS_BY_SCENERY[itemId!] || []
          : (this as any).CREW_ASSIGNMENTS_BY_PROP[itemId!] || [];
      return findOrphanedAssignments({
        orderedScenes: this.orderedScenes,
        currentAllocations: allocations,
        crewAssignments,
        changeType,
        changeSceneId: sceneId,
      });
    },
    buildOrphanWarningVNode(orphanedAssignments: any[]): any {
      const h = this.$createElement;
      const groups: Record<string, string[]> = {};
      for (const assignment of orphanedAssignments) {
        const itemName =
          assignment.prop_id != null
            ? this.getPropById(assignment.prop_id)?.name || 'Unknown Prop'
            : this.getSceneryById(assignment.scenery_id)?.name || 'Unknown Scenery';
        const scene = this.orderedScenes.find((s: any) => s.id === assignment.scene_id);
        const sceneName = scene?.name || 'Unknown Scene';
        const key = `${itemName} - ${assignment.assignment_type.toUpperCase()} (${sceneName})`;
        if (!groups[key]) groups[key] = [];
        const crew = (this as any).CREW_MEMBER_BY_ID(assignment.crew_id);
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
    async deleteSceneryAllocation(allocation: any): Promise<void> {
      const scenery = this.getSceneryById(allocation.scenery_id);
      const orphans = this.findOrphansForItem(
        allocation.scenery_id,
        'scenery',
        'remove',
        this.currentScene.id
      );
      if (orphans.length > 0) {
        const msgVNode = this.buildOrphanWarningVNode(orphans);
        const action = await (this as any).$bvModal.msgBoxConfirm([msgVNode], {
          title: 'Crew assignments will be removed',
          okTitle: 'Continue',
          okVariant: 'danger',
        });
        if (action !== true) return;
      } else {
        const msg = `Remove "${scenery?.name}" from this scene?`;
        const action = await (this as any).$bvModal.msgBoxConfirm(msg, {});
        if (action !== true) return;
      }
      await (this as any).DELETE_SCENERY_ALLOCATION(allocation.id);
    },
    async deletePropAllocation(allocation: any): Promise<void> {
      const prop = this.getPropById(allocation.props_id);
      const orphans = this.findOrphansForItem(
        allocation.props_id,
        'prop',
        'remove',
        this.currentScene.id
      );
      if (orphans.length > 0) {
        const msgVNode = this.buildOrphanWarningVNode(orphans);
        const action = await (this as any).$bvModal.msgBoxConfirm([msgVNode], {
          title: 'Crew assignments will be removed',
          okTitle: 'Continue',
          okVariant: 'danger',
        });
        if (action !== true) return;
      } else {
        const msg = `Remove "${prop?.name}" from this scene?`;
        const action = await (this as any).$bvModal.msgBoxConfirm(msg, {});
        if (action !== true) return;
      }
      await (this as any).DELETE_PROPS_ALLOCATION(allocation.id);
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
});
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
