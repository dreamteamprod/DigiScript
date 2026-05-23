<template>
  <div ref="paneContainer" class="stage-manager-pane">
    <div class="pane-header">
      <h6 class="mb-0">Stage Manager</h6>
    </div>
    <div v-if="!loaded" class="loading-state">
      <BSpinner small variant="light" />
    </div>
    <div v-else-if="showStore.orderedScenes.length === 0" class="empty-state">
      <small class="text-muted">No scenes configured</small>
    </div>
    <div v-else ref="scrollContainer" class="scenes-container">
      <BCard
        v-for="scene in showStore.orderedScenes"
        :ref="(el) => setSceneCardRef(el, scene.id)"
        :key="scene.id"
        no-body
        class="scene-card mb-2"
        :class="{
          'current-scene': scene.id === currentSceneId,
          'next-scene': scene.id === nextSceneId,
        }"
      >
        <BCardHeader class="p-2 scene-header" role="button" @click="toggleScene(scene.id)">
          <div class="d-flex justify-content-between align-items-center">
            <span class="scene-title">
              <IMdiChevronDown v-if="expandedScenes[scene.id]" class="me-1" />
              <IMdiChevronRight v-else class="me-1" />
              {{ getSceneDisplayName(scene) }}
            </span>
            <span class="scene-badges d-flex align-items-center gap-1">
              <IMdiPin v-if="pinnedScenes[scene.id]" title="Pinned" />
              <BBadge v-if="scene.id === currentSceneId" variant="success" pill>Current</BBadge>
              <BBadge v-else-if="scene.id === nextSceneId" variant="primary" pill>Next</BBadge>
            </span>
          </div>
        </BCardHeader>
        <BCollapse v-model="expandedScenes[scene.id]">
          <BCardBody class="p-2 scene-body">
            <div class="d-flex justify-content-end mb-2">
              <BButton size="sm" variant="primary" @click.stop.prevent="showSMPlanModal(scene)">
                Plan
              </BButton>
            </div>
            <div
              v-if="
                getSceneryForScene(scene.id).length === 0 && getPropsForScene(scene.id).length === 0
              "
              class="empty-scene"
            >
              <small>No props or scenery</small>
            </div>
            <template v-else>
              <div v-if="getSceneryForScene(scene.id).length > 0" class="mb-2">
                <small class="section-label">Scenery</small>
                <ul class="item-list mb-0">
                  <li v-for="item in getSceneryForScene(scene.id)" :key="`scenery-${item.id}`">
                    {{ getSceneryDisplayName(item) }}
                  </li>
                </ul>
              </div>
              <div v-if="getPropsForScene(scene.id).length > 0">
                <small class="section-label">Props</small>
                <ul class="item-list mb-0">
                  <li v-for="item in getPropsForScene(scene.id)" :key="`prop-${item.id}`">
                    {{ getPropDisplayName(item) }}
                  </li>
                </ul>
              </div>
            </template>
          </BCardBody>
        </BCollapse>
      </BCard>
    </div>

    <BModal
      ref="smPlanModal"
      :title="smPlanScene ? `${getSceneDisplayName(smPlanScene)} - Plan` : ''"
      size="lg"
      ok-only
      @hidden="smPlanScene = null"
    >
      <div v-if="smPlanScene">
        <BCard no-body class="mb-2">
          <BCardHeader class="p-2" role="button" @click="smPlanSet = !smPlanSet">
            <IMdiChevronDown v-if="smPlanSet" /><IMdiChevronRight v-else /> Setting
          </BCardHeader>
          <BCollapse v-model="smPlanSet">
            <BCardBody class="p-2">
              <BContainer fluid class="mx-0 px-0">
                <BRow class="plan-header-row">
                  <BCol cols="6" class="plan-header-col border-end"><b>Scenery</b></BCol>
                  <BCol cols="6" class="plan-header-col"><b>Props</b></BCol>
                </BRow>
                <BRow class="plan-content-row">
                  <BCol cols="6" class="plan-content-col border-end">
                    <ul v-if="getSettingScenery(smPlanScene).length > 0" class="item-list mb-0">
                      <li
                        v-for="item in getSettingScenery(smPlanScene)"
                        :key="`set-scenery-${item.id}`"
                      >
                        {{ getSceneryDisplayName(item) }}
                        <div
                          v-if="getCrewNamesForSettingItem(item, 'scenery', smPlanScene).length > 0"
                          class="crew-names"
                        >
                          {{ getCrewNamesForSettingItem(item, 'scenery', smPlanScene).join(', ') }}
                        </div>
                      </li>
                    </ul>
                    <p v-else class="text-muted mb-0">None</p>
                  </BCol>
                  <BCol cols="6" class="plan-content-col">
                    <ul v-if="getSettingProps(smPlanScene).length > 0" class="item-list mb-0">
                      <li v-for="item in getSettingProps(smPlanScene)" :key="`set-prop-${item.id}`">
                        {{ getPropDisplayName(item) }}
                        <div
                          v-if="getCrewNamesForSettingItem(item, 'prop', smPlanScene).length > 0"
                          class="crew-names"
                        >
                          {{ getCrewNamesForSettingItem(item, 'prop', smPlanScene).join(', ') }}
                        </div>
                      </li>
                    </ul>
                    <p v-else class="text-muted mb-0">None</p>
                  </BCol>
                </BRow>
              </BContainer>
            </BCardBody>
          </BCollapse>
        </BCard>
        <BCard no-body class="mb-2">
          <BCardHeader class="p-2" role="button" @click="smPlanStrike = !smPlanStrike">
            <IMdiChevronDown v-if="smPlanStrike" /><IMdiChevronRight v-else /> Striking
          </BCardHeader>
          <BCollapse v-model="smPlanStrike">
            <BCardBody class="p-2">
              <BContainer fluid class="mx-0 px-0">
                <BRow class="plan-header-row">
                  <BCol cols="6" class="plan-header-col border-end"><b>Scenery</b></BCol>
                  <BCol cols="6" class="plan-header-col"><b>Props</b></BCol>
                </BRow>
                <BRow class="plan-content-row">
                  <BCol cols="6" class="plan-content-col border-end">
                    <ul v-if="getStrikingScenery(smPlanScene).length > 0" class="item-list mb-0">
                      <li
                        v-for="item in getStrikingScenery(smPlanScene)"
                        :key="`strike-scenery-${item.id}`"
                      >
                        {{ getSceneryDisplayName(item) }}
                        <div
                          v-if="
                            getCrewNamesForStrikingItem(item, 'scenery', smPlanScene).length > 0
                          "
                          class="crew-names"
                        >
                          {{ getCrewNamesForStrikingItem(item, 'scenery', smPlanScene).join(', ') }}
                        </div>
                      </li>
                    </ul>
                    <p v-else class="text-muted mb-0">None</p>
                  </BCol>
                  <BCol cols="6" class="plan-content-col">
                    <ul v-if="getStrikingProps(smPlanScene).length > 0" class="item-list mb-0">
                      <li
                        v-for="item in getStrikingProps(smPlanScene)"
                        :key="`strike-prop-${item.id}`"
                      >
                        {{ getPropDisplayName(item) }}
                        <div
                          v-if="getCrewNamesForStrikingItem(item, 'prop', smPlanScene).length > 0"
                          class="crew-names"
                        >
                          {{ getCrewNamesForStrikingItem(item, 'prop', smPlanScene).join(', ') }}
                        </div>
                      </li>
                    </ul>
                    <p v-else class="text-muted mb-0">None</p>
                  </BCol>
                </BRow>
              </BContainer>
            </BCardBody>
          </BCollapse>
        </BCard>
      </div>
      <div v-else><p>No scene selected.</p></div>
    </BModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { debounce } from 'lodash';
import { useShowStore } from '@/stores/show';
import { useStageStore } from '@/stores/stage';
import { useScriptStore } from '@/stores/script';
import type { Scene } from '@/types/api/show';
import type { Props, Scenery } from '@/types/api/stage';

const props = defineProps<{
  sessionFollowData: Record<string, unknown>;
}>();

const showStore = useShowStore();
const stageStore = useStageStore();
const scriptStore = useScriptStore();

const loaded = ref(false);
const expandedScenes = ref<Record<number, boolean>>({});
const pinnedScenes = ref<Record<number, boolean>>({});
const smPlanScene = ref<Scene | null>(null);
const smPlanSet = ref(true);
const smPlanStrike = ref(true);
const paneContainer = ref<HTMLElement | null>(null);
const scrollContainer = ref<HTMLElement | null>(null);
const smPlanModal = ref<InstanceType<typeof import('bootstrap-vue-next').BModal> | null>(null);
const sceneCardRefs = ref<Record<number, Element>>({});

function setSceneCardRef(el: unknown, sceneId: number): void {
  if (el && (el as Element).tagName) sceneCardRefs.value[sceneId] = el as Element;
}

const currentSceneId = computed((): number | null => {
  const lineRef = props.sessionFollowData?.current_line as string | undefined;
  if (!lineRef) return null;
  const parts = lineRef.split('_');
  if (parts.length < 4) return null;
  const page = Number.parseInt(parts[1], 10);
  const lineIdx = Number.parseInt(parts[3], 10);
  return scriptStore.getScriptPage(page)[lineIdx]?.scene_id ?? null;
});

const nextSceneId = computed((): number | null => {
  if (currentSceneId.value === null) return null;
  const idx = showStore.orderedScenes.findIndex((s) => s.id === currentSceneId.value);
  if (idx === -1 || idx >= showStore.orderedScenes.length - 1) return null;
  return showStore.orderedScenes[idx + 1].id;
});

watch(currentSceneId, (newId, oldId) => {
  if (newId !== null && newId !== oldId) {
    const idx = showStore.orderedScenes.findIndex((s) => s.id === newId);
    const autoExpand = new Set([newId]);
    if (idx !== -1 && idx < showStore.orderedScenes.length - 1) {
      autoExpand.add(showStore.orderedScenes[idx + 1].id);
    }
    showStore.orderedScenes.forEach((s) => {
      if (!autoExpand.has(s.id) && !pinnedScenes.value[s.id]) {
        expandedScenes.value[s.id] = false;
      }
    });
    autoExpand.forEach((id) => {
      expandedScenes.value[id] = true;
    });
    nextTick(() => autoScrollToCurrentScene(newId));
  }
});

watch(
  () => showStore.orderedScenes,
  (scenes) => {
    scenes.forEach((scene, index) => {
      if (expandedScenes.value[scene.id] === undefined) {
        expandedScenes.value[scene.id] = index === 0;
      }
    });
  },
  { immediate: true }
);

const debounceComputeContentSize = debounce(computeContentSize, 100);

onMounted(async () => {
  await Promise.all([
    showStore.getActList(),
    showStore.getSceneList(),
    stageStore.getPropsList(),
    stageStore.getSceneryList(),
    stageStore.getPropsAllocations(),
    stageStore.getSceneryAllocations(),
    stageStore.getPropTypes(),
    stageStore.getSceneryTypes(),
    stageStore.getCrewList(),
    stageStore.getCrewAssignments(),
  ]);
  loaded.value = true;
  await nextTick();
  computeContentSize();
  window.addEventListener('resize', debounceComputeContentSize);
});

onUnmounted(() => window.removeEventListener('resize', debounceComputeContentSize));

function computeContentSize(): void {
  if (!paneContainer.value) return;
  const top = paneContainer.value.getBoundingClientRect().top;
  paneContainer.value.style.height = `${document.documentElement.clientHeight - top}px`;
}

function toggleScene(sceneId: number): void {
  const isExpanded = expandedScenes.value[sceneId];
  expandedScenes.value[sceneId] = !isExpanded;
  pinnedScenes.value[sceneId] = !isExpanded;
}

function getSceneDisplayName(scene: Scene): string {
  const act = showStore.actById(scene.act);
  return `${act?.name ?? 'Unknown Act'}: ${scene.name}`;
}

function getPropsForScene(sceneId: number): Props[] {
  return stageStore.propsAllocations
    .filter((a) => a.scene_id === sceneId)
    .map((a) => stageStore.propById(a.props_id)!)
    .filter(Boolean);
}

function getSceneryForScene(sceneId: number): Scenery[] {
  return stageStore.sceneryAllocations
    .filter((a) => a.scene_id === sceneId)
    .map((a) => stageStore.sceneryById(a.scenery_id)!)
    .filter(Boolean);
}

function getPreviousScene(scene: Scene): Scene | null {
  const idx = showStore.orderedScenes.findIndex((s) => s.id === scene.id);
  return idx > 0 ? showStore.orderedScenes[idx - 1] : null;
}

function getSettingProps(scene: Scene): Props[] {
  const current = getPropsForScene(scene.id);
  const prev = getPreviousScene(scene);
  if (!prev) return current;
  const prevIds = new Set(getPropsForScene(prev.id).map((p) => p.id));
  return current.filter((p) => !prevIds.has(p.id));
}

function getStrikingProps(scene: Scene): Props[] {
  const prev = getPreviousScene(scene);
  if (!prev) return [];
  const currentIds = new Set(getPropsForScene(scene.id).map((p) => p.id));
  return getPropsForScene(prev.id).filter((p) => !currentIds.has(p.id));
}

function getSettingScenery(scene: Scene): Scenery[] {
  const current = getSceneryForScene(scene.id);
  const prev = getPreviousScene(scene);
  if (!prev) return current;
  const prevIds = new Set(getSceneryForScene(prev.id).map((s) => s.id));
  return current.filter((s) => !prevIds.has(s.id));
}

function getStrikingScenery(scene: Scene): Scenery[] {
  const prev = getPreviousScene(scene);
  if (!prev) return [];
  const currentIds = new Set(getSceneryForScene(scene.id).map((s) => s.id));
  return getSceneryForScene(prev.id).filter((s) => !currentIds.has(s.id));
}

function getPropDisplayName(prop: Props): string {
  const type = stageStore.propTypeById(prop.prop_type_id);
  return type ? `${type.name}: ${prop.name}` : (prop.name ?? '');
}

function getSceneryDisplayName(scenery: Scenery): string {
  const type = stageStore.sceneryTypeById(scenery.scenery_type_id);
  return type ? `${type.name}: ${scenery.name}` : (scenery.name ?? '');
}

function formatCrewName(crewId: number | null): string {
  const c = stageStore.crewById(crewId);
  if (!c) return 'Unknown';
  return c.last_name ? `${c.first_name} ${c.last_name}` : (c.first_name ?? '');
}

function getCrewNamesForSettingItem(
  item: Props | Scenery,
  itemType: 'prop' | 'scenery',
  scene: Scene
): string[] {
  const assignments =
    itemType === 'prop'
      ? (stageStore.crewAssignmentsByProp[item.id] ?? [])
      : (stageStore.crewAssignmentsByScenery[item.id] ?? []);
  return assignments
    .filter((a) => a.assignment_type === 'set' && a.scene_id === scene.id)
    .map((a) => formatCrewName(a.crew_id));
}

function getCrewNamesForStrikingItem(
  item: Props | Scenery,
  itemType: 'prop' | 'scenery',
  scene: Scene
): string[] {
  const prev = getPreviousScene(scene);
  if (!prev) return [];
  const assignments =
    itemType === 'prop'
      ? (stageStore.crewAssignmentsByProp[item.id] ?? [])
      : (stageStore.crewAssignmentsByScenery[item.id] ?? []);
  return assignments
    .filter((a) => a.assignment_type === 'strike' && a.scene_id === prev.id)
    .map((a) => formatCrewName(a.crew_id));
}

function autoScrollToCurrentScene(currentId: number): void {
  if (!scrollContainer.value) return;
  const idx = showStore.orderedScenes.findIndex((s) => s.id === currentId);
  const targetId = idx > 0 ? showStore.orderedScenes[idx - 1].id : currentId;
  const el = sceneCardRefs.value[targetId];
  if (!el) return;
  const containerTop = scrollContainer.value.getBoundingClientRect().top;
  const elTop = el.getBoundingClientRect().top;
  scrollContainer.value.scrollTo({
    top: elTop - containerTop + scrollContainer.value.scrollTop,
    behavior: 'smooth',
  });
}

function showSMPlanModal(scene: Scene): void {
  smPlanScene.value = scene;
  smPlanSet.value = true;
  smPlanStrike.value = true;
  smPlanModal.value?.show();
}
</script>

<style scoped>
.stage-manager-pane {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  overflow: hidden;
  background-color: var(--body-background, #222);
}
.pane-header {
  flex-shrink: 0;
  padding: 0.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background-color: rgba(0, 0, 0, 0.2);
}
.scenes-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0.5rem;
  min-height: 0;
}
.loading-state,
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  flex: 1;
  padding: 1rem;
}
.scene-card {
  background-color: #303030;
  border: 1px solid #444;
  border-radius: 0.25rem;
}
.scene-card.current-scene {
  border-color: #28a745;
  border-width: 2px;
}
.scene-card.next-scene {
  border-color: #2863a7;
  border-width: 2px;
}
.scene-header {
  cursor: pointer;
  background-color: #3a3a3a;
  border-bottom: 1px solid #444;
  transition: background-color 0.15s ease-in-out;
}
.scene-header:hover {
  background-color: #454545;
}
.current-scene .scene-header {
  background-color: #1a472a;
}
.next-scene .scene-header {
  background-color: #1a3147;
}
.current-scene .scene-header:hover {
  background-color: #215d35;
}
.next-scene .scene-header:hover {
  background-color: #28476b;
}
.scene-title {
  font-size: 0.8rem;
  font-weight: 500;
  color: #dee2e6;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.scene-badges {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.scene-body {
  background-color: #303030;
}
.section-label {
  display: block;
  color: #6c757d;
  font-weight: 600;
  text-transform: uppercase;
  margin-bottom: 0.25rem;
}
.item-list {
  list-style: none;
  padding-left: 0.5rem;
  margin: 0;
}
.item-list li {
  color: #adb5bd;
  padding: 0.1rem 0;
}
.empty-scene {
  color: #6c757d;
  font-style: italic;
}
.plan-header-row {
  margin: 0;
  padding: 0;
  border-bottom: 1px solid #dee2e6;
}
.plan-header-col {
  padding: 0.5rem 0.75rem;
}
.plan-content-row {
  margin: 0;
  padding: 0;
}
.plan-content-col {
  padding: 0.5rem 0.75rem;
}
.crew-names {
  color: #6c757d;
  font-size: 0.8rem;
  padding-left: 0.5rem;
  font-style: italic;
}
</style>
