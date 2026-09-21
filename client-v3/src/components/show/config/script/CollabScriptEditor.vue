<template>
  <BContainer v-if="loaded" class="mx-0 px-0 script-editor-container" fluid>
    <div class="sticky-header" :style="{ top: navbarHeight + 'px' }">
      <BRow class="script-row">
        <BCol cols="2">
          <BButton variant="success" @click="openGoToPage">Go to Page</BButton>
        </BCol>
        <BCol cols="2" style="text-align: right">
          <BButton variant="success" :disabled="currentPage === 1" @click="decrPage">
            Prev Page
          </BButton>
        </BCol>
        <BCol cols="4">
          <p>Current Page: {{ currentPage }}</p>
        </BCol>
        <BCol cols="2" style="text-align: left">
          <BButton variant="success" :disabled="atLastDraftPage" @click="incrPage">
            Next Page
          </BButton>
        </BCol>
        <BCol cols="2">
          <BButtonGroup v-if="systemStore.isScriptEditor">
            <template v-if="!isEditor">
              <BButton variant="warning" :disabled="hasCutters" @click="requestEdit">Edit</BButton>
              <BButton
                variant="warning"
                disabled
                title="Cut mode is not yet available with collaborative editing"
              >
                Cuts
              </BButton>
            </template>
            <BButton v-else variant="warning" @click="stopEditing">Stop Editing</BButton>
          </BButtonGroup>
        </BCol>
      </BRow>
      <BRow class="script-row">
        <BCol cols="1">Act</BCol>
        <BCol cols="1">Scene</BCol>
        <BCol>Line</BCol>
        <BCol cols="1" />
      </BRow>
    </div>

    <BAlert :model-value="joinFailed" variant="danger" class="mt-3">
      <div class="d-flex justify-content-between align-items-center">
        <span>
          Could not open the script draft.
          <template v-if="draftStore.lastCollabError">{{ draftStore.lastCollabError }}</template>
        </span>
        <BButton size="sm" variant="outline-danger" @click="retryJoin">Retry</BButton>
      </div>
    </BAlert>

    <BRow v-if="isEditor && draftStore.status === 'joining'">
      <BCol class="text-center py-5"><BSpinner label="Opening draft" /></BCol>
    </BRow>

    <BRow v-else class="script-row">
      <BCol cols="12">
        <template v-if="draftReady">
          <ScriptLineViewer
            v-for="(line, index) in draftLines"
            :key="line._uid"
            :line-index="index"
            :line="line"
            :page="draftLines"
            :acts="showStore.actList"
            :scenes="showStore.sceneList"
            :characters="showStore.characterList"
            :character-groups="showStore.characterGroupList"
            :previous-line="draftPages.previousLineOf(currentPage, index)"
            :can-edit="false"
            :line-part-cuts="[]"
            :stage-direction-styles="scriptStore.stageDirectionStyles"
            :stage-direction-style-overrides="userStore.stageDirectionStyleOverrides"
          />
        </template>
        <template v-else-if="!isEditor">
          <ScriptLineViewer
            v-for="(line, index) in viewerLines"
            :key="`page_${currentPage}_line_${index}`"
            :line-index="index"
            :line="line"
            :page="viewerLines"
            :acts="showStore.actList"
            :scenes="showStore.sceneList"
            :characters="showStore.characterList"
            :character-groups="showStore.characterGroupList"
            :previous-line="viewerPreviousLine(index)"
            :can-edit="false"
            :line-part-cuts="[]"
            :stage-direction-styles="scriptStore.stageDirectionStyles"
            :stage-direction-style-overrides="userStore.stageDirectionStyleOverrides"
          />
        </template>
      </BCol>
    </BRow>

    <BModal
      ref="goToPageModal"
      title="Go to Page"
      size="sm"
      :no-header-close="changingPage"
      :no-footer="changingPage"
      :no-close-on-backdrop="changingPage"
      :no-close-on-esc="changingPage"
      @ok.prevent="goToPage"
    >
      <BForm @submit.stop.prevent="">
        <BFormGroup label="Page" label-for="page-input" label-cols="auto">
          <BFormInput id="page-input" v-model.number="pageInputNo" type="number" :min="1" />
        </BFormGroup>
        <p v-if="pageError" class="text-danger mb-0" data-testid="page-error">{{ pageError }}</p>
      </BForm>
    </BModal>
  </BContainer>

  <BContainer v-else class="mx-0 px-0 script-editor-container" fluid>
    <BRow>
      <BCol class="text-center py-5"><BSpinner label="Loading" /></BCol>
    </BRow>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import { useScriptStore } from '@/stores/script';
import { useScriptConfigStore } from '@/stores/scriptConfig';
import { useScriptDraftStore } from '@/stores/scriptDraft';
import { useUserStore } from '@/stores/user';
import { useWebSocketStore } from '@/stores/websocket';
import { useWebSocket } from '@/composables/useWebSocket';
import { useDraftPages } from '@/composables/useDraftPages';
import ScriptLineViewer from './ScriptLineViewer.vue';
import type { ScriptLine } from '@/types/api/script';

/**
 * The script editor for collaborative mode (`collaborative_script_editing` on). Step 2:
 * read-only. An editor joins the shared draft and browses it; everyone else reads saved
 * pages over REST exactly as the classic editor's viewer does. The classic
 * `ScriptEditor.vue` is untouched and is what renders when the setting is off.
 */

const showStore = useShowStore();
const systemStore = useSystemStore();
const scriptStore = useScriptStore();
const scriptConfigStore = useScriptConfigStore();
const draftStore = useScriptDraftStore();
const userStore = useUserStore();
const wsStore = useWebSocketStore();
const { sendObj } = useWebSocket();
const draftPages = useDraftPages();

const loaded = ref(false);
const currentPage = ref(1);
const navbarHeight = ref(56);
const changingPage = ref(false);
const pageInputNo = ref(1);
const pageError = ref<string | null>(null);
const goToPageModal = ref<InstanceType<typeof BModal>>();

// We are an editor when the server lists us among the editors. The server commits
// `is_editor` before it broadcasts GET_SCRIPT_CONFIG_STATUS, so this is also the moment
// the room will assign us the editor role on join.
const isEditor = computed(
  () =>
    wsStore.internalUUID !== null &&
    scriptConfigStore.editors.some((e) => e.internal_id === wsStore.internalUUID)
);
const hasCutters = computed(() => scriptConfigStore.cutters.length > 0);

const draftReady = computed(() => isEditor.value && draftStore.isDraftSynced);
// Editor whose room is gone: a rejected join, ROOM_CLOSED, or the socket not up. Without
// this the user is an editor with no room and no way out but Stop Editing.
const joinFailed = computed(() => loaded.value && isEditor.value && draftStore.status === 'idle');
const maxPage = draftPages.maxPage;
const atLastDraftPage = computed(() => draftReady.value && currentPage.value >= maxPage.value);

const draftLines = computed(() => (draftReady.value ? draftPages.linesFor(currentPage.value) : []));
const viewerLines = computed<ScriptLine[]>(() => scriptStore.getScriptPage(currentPage.value));

function viewerPreviousLine(index: number): ScriptLine | null {
  if (index > 0) return viewerLines.value[index - 1] ?? null;
  return scriptStore.getScriptPage(currentPage.value - 1).at(-1) ?? null;
}

async function loadViewerPage(page: number): Promise<void> {
  if (page > 1) await scriptStore.loadScriptPage(page - 1);
  await scriptStore.loadScriptPage(page);
}

async function navigateTo(page: number): Promise<void> {
  if (!draftReady.value) await loadViewerPage(page);
  currentPage.value = page;
}

function decrPage(): Promise<void> {
  return currentPage.value > 1 ? navigateTo(currentPage.value - 1) : Promise.resolve();
}

function incrPage(): Promise<void> {
  // A client can't create a page (two editors creating the same one lose data); the
  // server's empty trailing page is the last one that exists.
  if (atLastDraftPage.value) return Promise.resolve();
  return navigateTo(currentPage.value + 1);
}

function openGoToPage(): void {
  pageError.value = null;
  pageInputNo.value = currentPage.value;
  goToPageModal.value?.show();
}

async function goToPage(): Promise<void> {
  const target = pageInputNo.value;
  if (!Number.isInteger(target) || target < 1) return;
  if (draftReady.value && target > maxPage.value) {
    pageError.value = `Page ${target} does not exist yet — the last page is ${maxPage.value}.`;
    return;
  }
  pageError.value = null;
  changingPage.value = true;
  try {
    await navigateTo(target);
  } finally {
    changingPage.value = false;
  }
  goToPageModal.value?.hide();
}

function requestEdit(): void {
  sendObj({ OP: 'REQUEST_SCRIPT_EDIT', DATA: { collab: true } });
}

function stopEditing(): void {
  draftStore.leaveScriptRoom();
  sendObj({ OP: 'STOP_SCRIPT_EDIT', DATA: {} });
}

function retryJoin(): void {
  if (!draftStore.isDraftActive) draftStore.joinScriptRoom();
}

function calculateNavbarHeight(): void {
  const navbar = document.querySelector('.navbar');
  navbarHeight.value = navbar ? (navbar as HTMLElement).offsetHeight : 56;
}

watch(isEditor, async (now, was) => {
  if (now && !was) {
    retryJoin();
  } else if (!now && was) {
    draftStore.leaveScriptRoom();
    await loadViewerPage(currentPage.value);
  }
});

// Pages are never removed, but the stored page (or a page from before a rejoin) may be
// past the last one that exists.
watch([draftReady, maxPage], () => {
  if (draftReady.value && currentPage.value > maxPage.value) {
    currentPage.value = maxPage.value;
  }
});

watch(currentPage, (val) => {
  localStorage.setItem('scriptEditPage', val.toString());
});

onMounted(async () => {
  window.addEventListener('resize', calculateNavbarHeight);
  calculateNavbarHeight();

  await Promise.all([
    showStore.getActList(),
    showStore.getSceneList(),
    showStore.getCharacterList(),
    showStore.getCharacterGroupList(),
    scriptStore.getStageDirectionStyles(),
    scriptConfigStore.getScriptConfigStatus(),
  ]);

  const storedPage = Number.parseInt(localStorage.getItem('scriptEditPage') ?? '1', 10);
  currentPage.value = Number.isInteger(storedPage) && storedPage > 0 ? storedPage : 1;
  await loadViewerPage(currentPage.value);

  loaded.value = true;
  // A reload while editing: the server kept our editor flag under the new client id, so
  // we are an editor again before this component ever saw the change.
  if (isEditor.value) retryJoin();
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', calculateNavbarHeight);
  // Leaving the tab leaves the room (the editor flag is kept, so coming back rejoins).
  if (draftStore.isDraftActive) draftStore.leaveScriptRoom();
});
</script>

<style scoped>
.script-editor-container {
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
