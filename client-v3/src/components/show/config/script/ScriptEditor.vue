<template>
  <BContainer v-if="loaded" class="mx-0 px-0 script-editor-container" fluid>
    <div class="sticky-header" :style="{ top: navbarHeight + 'px' }">
      <BRow class="script-row">
        <BCol cols="2">
          <BButton variant="success" @click="goToPageModal?.show()">Go to Page</BButton>
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
          <BButton variant="success" @click="incrPage">Next Page</BButton>
        </BCol>
        <BCol cols="2">
          <BButtonGroup v-if="systemStore.isScriptEditor">
            <template v-if="!isEditor">
              <BButton
                variant="warning"
                :disabled="!scriptConfigStore.editStatus.canRequestEdit"
                @click="requestEdit"
              >
                Edit
              </BButton>
              <BButton
                variant="warning"
                :disabled="!scriptConfigStore.editStatus.canRequestEdit"
                @click="requestCutEdit"
              >
                Cuts
              </BButton>
            </template>
            <template v-else>
              <BButton
                variant="warning"
                :disabled="savingInProgress || isAutoSaving"
                @click="stopEditing"
              >
                Stop Editing
              </BButton>
              <BButton variant="success" :disabled="!canSave && !isAutoSaving" @click="saveScript">
                Save
              </BButton>
              <BButton
                v-if="canEdit && !scriptConfigStore.cutMode"
                :variant="bulkEditMode ? 'info' : 'outline-info'"
                @click="bulkEditMode ? exitBulkEditMode() : enterBulkEditMode()"
              >
                {{ bulkEditMode ? 'Exit Bulk Edit' : 'Bulk Edit' }}
              </BButton>
            </template>
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
    <BRow class="script-row">
      <BCol cols="12">
        <template
          v-for="(line, index) in currentPageLines"
          :key="`page_${currentPage}_line_${index}`"
        >
          <template v-if="!deletedLines.includes(index)">
            <ScriptLineEditor
              v-if="editingLines.has(`page_${currentPage}_line_${index}`)"
              :line-index="index"
              :current-edit-page="currentPage"
              :acts="showStore.actList"
              :scenes="showStore.sceneList"
              :characters="showStore.characterList"
              :character-groups="showStore.characterGroupList"
              :model-value="line"
              :previous-line="getPreviousLine(index)"
              :next-line="getNextLine(index)"
              :line-type="line.line_type"
              :stage-direction-styles="scriptStore.stageDirectionStyles"
              @update:model-value="onLineChange(index, $event)"
              @done-editing="doneEditingLine(currentPage, index)"
              @delete-line="deleteLine(currentPage, index)"
            />
            <ScriptLineViewer
              v-else
              :line-index="index"
              :line="line"
              :page="currentPageLines"
              :acts="showStore.actList"
              :scenes="showStore.sceneList"
              :characters="showStore.characterList"
              :character-groups="showStore.characterGroupList"
              :previous-line="currentPageLines[index - 1] ?? null"
              :can-edit="canEdit"
              :line-part-cuts="linePartCuts"
              :stage-direction-styles="scriptStore.stageDirectionStyles"
              :stage-direction-style-overrides="userStore.stageDirectionStyleOverrides"
              :bulk-edit-mode="bulkEditMode"
              :is-bulk-start="isBulkStart(index)"
              :is-bulk-end="isBulkEnd(index)"
              @edit-line="beginEditingLine(currentPage, index)"
              @cut-line-part="cutLinePart"
              @insert-dialogue="insertLineAt(currentPage, index, LINE_TYPES.DIALOGUE)"
              @insert-stage-direction="insertLineAt(currentPage, index, LINE_TYPES.STAGE_DIRECTION)"
              @insert-cue-line="insertLineAt(currentPage, index, LINE_TYPES.CUE_LINE)"
              @insert-spacing="insertLineAt(currentPage, index, LINE_TYPES.SPACING)"
              @delete-line="deleteLine(currentPage, index)"
              @set-bulk-start="onSetBulkStart(index)"
              @set-bulk-end="onSetBulkEnd(index)"
            />
          </template>
        </template>
      </BCol>
    </BRow>
    <BRow class="script-row pt-1">
      <BCol cols="10" class="ms-auto">
        <BButtonGroup v-show="canEdit && !scriptConfigStore.cutMode" style="float: right">
          <BButton variant="primary" @click="addNewLine(LINE_TYPES.DIALOGUE)">Add Dialogue</BButton>
          <BDropdown variant="primary" end toggle-class="dropdown-toggle-split">
            <BDropdownItem @click="addNewLine(LINE_TYPES.STAGE_DIRECTION)"
              >Add Stage Direction</BDropdownItem
            >
            <BDropdownItem @click="addNewLine(LINE_TYPES.CUE_LINE)">Add Cue Line</BDropdownItem>
            <BDropdownItem @click="addNewLine(LINE_TYPES.SPACING)">Add Spacing</BDropdownItem>
          </BDropdown>
        </BButtonGroup>
      </BCol>
    </BRow>

    <!-- Save modal -->
    <BModal
      ref="saveModal"
      title="Saving Script"
      size="md"
      :no-header-close="savingInProgress"
      :no-footer="savingInProgress"
      :ok-disabled="savingInProgress"
      :no-close-on-backdrop="savingInProgress"
      :no-close-on-esc="savingInProgress"
      ok-only
    >
      <div>
        <b v-if="savingInProgress">Saving page {{ curSavePage }} of {{ totalSavePages }}</b>
        <template v-else>
          <b v-if="saveError">Could not save script changes.</b>
          <b v-else>Finished saving script.</b>
        </template>
      </div>
      <BProgress
        :value="curSavePage"
        :max="totalSavePages ?? 0"
        :variant="saveProgressVariant"
        show-value
        :animated="savingInProgress"
      />
    </BModal>

    <BulkEditModal
      ref="bulkModal"
      :previous-line-of-start="previousLineOfStart"
      :next-line-of-end="nextLineOfEnd"
      :acts="showStore.actList"
      :scenes="showStore.sceneList"
      :characters="showStore.characterList"
      :character-groups="showStore.characterGroupList"
      @apply="onBulkApply"
    />

    <!-- Go-to-page modal -->
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import { LINE_TYPES } from '@/constants/lineTypes';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import { useScriptStore } from '@/stores/script';
import { useScriptConfigStore, computePageStatus } from '@/stores/scriptConfig';
import { useUserStore } from '@/stores/user';
import { useWebSocket } from '@/composables/useWebSocket';
import { useWebSocketStore } from '@/stores/websocket';
import { useConfirm } from '@/composables/useConfirm';
import { toast } from '@/js/toast';
import ScriptLineEditor from './ScriptLineEditor.vue';
import ScriptLineViewer from './ScriptLineViewer.vue';
import BulkEditModal from './BulkEditModal.vue';
import type { ScriptLine } from '@/types/api/script';

const MRU_LOOK_BACK = 4;

const showStore = useShowStore();
const systemStore = useSystemStore();
const scriptStore = useScriptStore();
const scriptConfigStore = useScriptConfigStore();
const userStore = useUserStore();
const { sendObj } = useWebSocket();
const wsStore = useWebSocketStore();
const { confirm } = useConfirm();

const loaded = ref(false);
const currentPage = ref(1);
const navbarHeight = ref(56);
const editingLines = ref(new Set<string>());
const latestAddedLine = ref<string | null>(null);
const linePartCuts = ref<number[]>([]);
const savingInProgress = ref(false);
const saveError = ref(false);
const curSavePage = ref(0);
const totalSavePages = ref<number | null>(null);
const changingPage = ref(false);
const isAutoSaving = ref(false);
const autoSaveInterval = ref<ReturnType<typeof setInterval> | null>(null);
const bulkEditMode = ref(false);
const bulkEditStart = ref<{ page: number; lineIndex: number } | null>(null);
const bulkEditEnd = ref<{ page: number; lineIndex: number } | null>(null);
const previousLineOfStart = ref<ScriptLine | null>(null);
const nextLineOfEnd = ref<ScriptLine | null>(null);
const pageInputNo = ref(1);

const saveModal = ref<InstanceType<typeof BModal>>();
const goToPageModal = ref<InstanceType<typeof BModal>>();
const bulkModal = ref<InstanceType<typeof BulkEditModal>>();

const currentPageLines = computed(() => scriptConfigStore.getTmpPage(currentPage.value));
const deletedLines = computed(() => scriptConfigStore.getDeletedLines(currentPage.value));

const isEditor = computed(
  () =>
    wsStore.internalUUID !== null &&
    wsStore.internalUUID === scriptConfigStore.editStatus.currentEditor
);
const canEdit = computed(() => isEditor.value);

const saveProgressVariant = computed(() => {
  if (savingInProgress.value) return 'primary';
  return saveError.value ? 'danger' : 'success';
});

const pagesWithOpenEdits = computed(() =>
  [...editingLines.value].map((x) => Number.parseInt(x.split('_')[1], 10))
);

const scriptChanges = computed<boolean>(() => {
  if (scriptConfigStore.cutMode) {
    return JSON.stringify(linePartCuts.value) !== JSON.stringify(scriptStore.cuts);
  }
  return Object.keys(scriptConfigStore.tmpScript).some((pageStr) => {
    const actual = scriptStore.getScriptPage(pageStr);
    const tmp = scriptConfigStore.getTmpPage(pageStr);
    const deleted = scriptConfigStore.getDeletedLines(pageStr);
    const inserted = scriptConfigStore.getInsertedLines(pageStr);
    if (deleted.length > 0 || inserted.length > 0) return true;
    if (actual.length !== tmp.length) return true;
    return JSON.stringify(actual) !== JSON.stringify(tmp);
  });
});

const canSave = computed(() => {
  if (scriptConfigStore.cutMode) return scriptChanges.value;
  return scriptChanges.value && editingLines.value.size === 0;
});

// Previous/next line helpers (synchronous — adjacent pages preloaded)
function getPreviousLine(lineIndex: number): ScriptLine | null {
  const deletedOnPage = scriptConfigStore.getDeletedLines(currentPage.value);
  const pageLines = scriptConfigStore.getTmpPage(currentPage.value);
  for (let i = lineIndex - 1; i >= 0; i--) {
    if (!deletedOnPage.includes(i)) return pageLines[i];
  }
  if (currentPage.value > 1) {
    const prevLines = scriptConfigStore.getTmpPage(currentPage.value - 1);
    const deletedOnPrev = scriptConfigStore.getDeletedLines(currentPage.value - 1);
    for (let i = prevLines.length - 1; i >= 0; i--) {
      if (!deletedOnPrev.includes(i)) return prevLines[i];
    }
  }
  return null;
}

function getNextLine(lineIndex: number): ScriptLine | null {
  const deletedOnPage = scriptConfigStore.getDeletedLines(currentPage.value);
  const pageLines = scriptConfigStore.getTmpPage(currentPage.value);
  for (let i = lineIndex + 1; i < pageLines.length; i++) {
    if (!deletedOnPage.includes(i)) return pageLines[i];
  }
  // Check next preloaded page
  const nextPageLines = scriptConfigStore.getTmpPage(currentPage.value + 1);
  const deletedOnNext = scriptConfigStore.getDeletedLines(currentPage.value + 1);
  for (let i = 0; i < nextPageLines.length; i++) {
    if (!deletedOnNext.includes(i)) return nextPageLines[i];
  }
  return null;
}

function requestEdit(): void {
  sendObj({ OP: 'REQUEST_SCRIPT_EDIT', DATA: {} });
}

function requestCutEdit(): void {
  scriptConfigStore.setCutMode(true);
  sendObj({ OP: 'REQUEST_SCRIPT_EDIT', DATA: {} });
}

async function stopEditing(): Promise<void> {
  if (scriptChanges.value) {
    const ok = await confirm(
      'Are you sure you want to stop editing the script? This will cause all unsaved changes to be lost.'
    );
    if (!ok) return;
  }
  const wasCutMode = scriptConfigStore.cutMode;
  editingLines.value.clear();
  exitBulkEditMode();
  linePartCuts.value = [...scriptStore.cuts];
  scriptConfigStore.setCutMode(false);
  scriptConfigStore.setEditStatus({
    canRequestEdit: scriptConfigStore.editStatus.canRequestEdit,
    currentEditor: null,
  });
  sendObj({ OP: 'STOP_SCRIPT_EDIT', DATA: {} });
  if (!wasCutMode) {
    scriptConfigStore.emptyScript();
    await loadPage(currentPage.value);
  }
}

async function loadPage(page: number): Promise<void> {
  if (!scriptConfigStore.tmpScript[String(page)]) {
    await scriptStore.loadScriptPage(page);
    scriptConfigStore.addPage(page, scriptStore.getScriptPage(page));
  }
}

async function decrPage(): Promise<void> {
  if (currentPage.value <= 1) return;
  const targetPage = currentPage.value - 1;
  await loadPage(targetPage);
  if (currentPageLines.value.length === 0) {
    scriptConfigStore.removePage(currentPage.value);
  }
  currentPage.value--;
  // Preload page before
  if (currentPage.value > 1) {
    await loadPage(currentPage.value - 1);
  }
}

async function incrPage(): Promise<void> {
  currentPage.value++;
  await loadPage(currentPage.value);
  // Preload next page
  await loadPage(currentPage.value + 1);
}

async function goToPageInner(page: number): Promise<void> {
  const lookBackStart = Math.max(1, page - MRU_LOOK_BACK);
  for (let p = lookBackStart; p < page; p++) {
    await loadPage(p);
  }
  await loadPage(page);
  currentPage.value = page;
  await loadPage(page + 1);
}

async function goToPage(): Promise<void> {
  if (!pageInputNo.value || pageInputNo.value < 1) return;
  changingPage.value = true;
  await goToPageInner(pageInputNo.value);
  changingPage.value = false;
  goToPageModal.value?.hide();
}

function blankLine(lineType: number): ScriptLine {
  return {
    id: null,
    act_id: null,
    scene_id: null,
    page: currentPage.value,
    line_type: lineType,
    line_parts: [],
    stage_direction_style_id: null,
  };
}

async function addNewLine(lineType: number): Promise<void> {
  const line = blankLine(lineType);
  scriptConfigStore.addBlankLine(currentPage.value, line);
  const pageLines = scriptConfigStore.getTmpPage(currentPage.value);
  const lineIndex = pageLines.length - 1;
  const lineIdent = `page_${currentPage.value}_line_${lineIndex}`;
  editingLines.value.add(lineIdent);
  latestAddedLine.value = lineIdent;
  const prev = getPreviousLine(lineIndex);
  if (prev) {
    scriptConfigStore.setLine(currentPage.value, lineIndex, {
      ...pageLines[lineIndex],
      act_id: prev.act_id,
      scene_id: prev.scene_id,
    });
  }
}

async function insertLineAt(pageIndex: number, lineIndex: number, lineType: number): Promise<void> {
  const pageLines = scriptConfigStore.getTmpPage(pageIndex);
  if (pageLines.length - 1 === lineIndex) {
    await addNewLine(lineType);
    return;
  }
  const newLineIndex = lineIndex + 1;
  const line = blankLine(lineType);
  scriptConfigStore.insertBlankLine(pageIndex, newLineIndex, line);

  // Shift all open edit indices that are >= newLineIndex up by 1
  const shifted = new Set<string>();
  editingLines.value.forEach((ident) => {
    const parts = ident.split('_');
    const ep = Number.parseInt(parts[1], 10);
    const ei = Number.parseInt(parts[3], 10);
    if (ep === pageIndex && ei >= newLineIndex) {
      shifted.add(`page_${ep}_line_${ei + 1}`);
    } else {
      shifted.add(ident);
    }
  });
  editingLines.value = shifted;

  const newIdent = `page_${currentPage.value}_line_${newLineIndex}`;
  editingLines.value.add(newIdent);

  const prev = getPreviousLine(newLineIndex);
  if (prev) {
    const updatedLines = scriptConfigStore.getTmpPage(pageIndex);
    scriptConfigStore.setLine(pageIndex, newLineIndex, {
      ...updatedLines[newLineIndex],
      act_id: prev.act_id,
      scene_id: prev.scene_id,
    });
  }
}

function onLineChange(lineIndex: number, line: ScriptLine): void {
  scriptConfigStore.setLine(currentPage.value, lineIndex, line);
}

function beginEditingLine(pageIndex: number, lineIndex: number): void {
  editingLines.value.add(`page_${pageIndex}_line_${lineIndex}`);
}

function doneEditingLine(pageIndex: number, lineIndex: number): void {
  const lineIdent = `page_${pageIndex}_line_${lineIndex}`;
  editingLines.value.delete(lineIdent);
  if (latestAddedLine.value === lineIdent) {
    addNewLine(LINE_TYPES.DIALOGUE);
  }
}

function deleteLine(pageIndex: number, lineIndex: number): void {
  const lineIdent = `page_${pageIndex}_line_${lineIndex}`;
  if (latestAddedLine.value === lineIdent) latestAddedLine.value = null;
  scriptConfigStore.deleteLine(pageIndex, lineIndex);
  doneEditingLine(pageIndex, lineIndex);

  const shifted = new Set<string>();
  editingLines.value.forEach((ident) => {
    const parts = ident.split('_');
    const ep = Number.parseInt(parts[1], 10);
    const ei = Number.parseInt(parts[3], 10);
    if (ep === pageIndex && ei >= lineIndex) {
      shifted.add(`page_${ep}_line_${ei - 1}`);
    } else {
      shifted.add(ident);
    }
  });
  editingLines.value = shifted;

  if (latestAddedLine.value) {
    const parts = latestAddedLine.value.split('_');
    const ep = Number.parseInt(parts[1], 10);
    const ei = Number.parseInt(parts[3], 10);
    if (ep === pageIndex && ei >= lineIndex) {
      latestAddedLine.value = `page_${pageIndex}_line_${ei - 1}`;
    }
  }
}

function cutLinePart(linePartId: number): void {
  const idx = linePartCuts.value.indexOf(linePartId);
  if (idx === -1) linePartCuts.value.push(linePartId);
  else linePartCuts.value.splice(idx, 1);
}

async function saveScript(): Promise<void> {
  if (scriptConfigStore.cutMode) {
    savingInProgress.value = true;
    await scriptStore.saveCuts(linePartCuts.value);
    linePartCuts.value = [...scriptStore.cuts];
    setupAutoSave();
    savingInProgress.value = false;
    return;
  }

  if (!scriptChanges.value) {
    toast.warning('No changes to save!');
    return;
  }

  savingInProgress.value = true;
  saveError.value = false;
  const maxPageOk = await scriptStore.getMaxPage();
  if (!maxPageOk) {
    toast.error('Unable to save script — could not determine page count. Please try again.');
    savingInProgress.value = false;
    return;
  }
  const tmpPageKeys = Object.keys(scriptConfigStore.tmpScript).map((x) => Number.parseInt(x, 10));
  const maxPage = Math.max(scriptStore.maxPage, ...tmpPageKeys, 0);
  totalSavePages.value = maxPage;
  curSavePage.value = 0;
  saveModal.value?.show();

  for (let pageNo = 1; pageNo <= maxPage; pageNo++) {
    curSavePage.value = pageNo;
    const tmpPage = scriptConfigStore.getTmpPage(pageNo);
    if (tmpPage.length === 0) continue;

    const actualPage = scriptStore.getScriptPage(pageNo);
    let ok: boolean;

    if (actualPage.length === 0) {
      ok = await scriptStore.saveNewPage(
        pageNo,
        tmpPage.filter((_, i) => !scriptConfigStore.getDeletedLines(pageNo).includes(i))
      );
    } else {
      const status = computePageStatus(
        actualPage,
        tmpPage,
        scriptConfigStore.getDeletedLines(pageNo),
        scriptConfigStore.getInsertedLines(pageNo)
      );
      const hasChanges =
        status.added.length > 0 ||
        status.updated.length > 0 ||
        status.deleted.length > 0 ||
        status.inserted.length > 0;
      if (!hasChanges) continue;

      ok = await scriptStore.saveChangedPage(pageNo, { page: tmpPage, status });
    }

    if (ok) {
      await scriptStore.loadScriptPage(pageNo);
      scriptConfigStore.addPage(pageNo, scriptStore.getScriptPage(pageNo));
      scriptConfigStore.resetTracking(pageNo);
    } else {
      toast.error('Unable to save script. Please try again.');
      saveError.value = true;
      break;
    }
  }

  savingInProgress.value = false;
  setupAutoSave();
  await scriptStore.getMaxPage();
}

function setupAutoSave(): void {
  const settings = userStore.userSettings as {
    enable_script_auto_save?: boolean;
    script_auto_save_interval?: number;
  };
  const intervalMs = Math.max((settings.script_auto_save_interval ?? 5) * 1000 * 60, 60000);

  if (!isEditor.value && autoSaveInterval.value != null) {
    clearInterval(autoSaveInterval.value);
    autoSaveInterval.value = null;
    return;
  }

  if (isEditor.value) {
    if (autoSaveInterval.value != null) clearInterval(autoSaveInterval.value);
    if (settings.enable_script_auto_save) {
      autoSaveInterval.value = setInterval(autosave, intervalMs);
    } else {
      autoSaveInterval.value = null;
    }
  }
}

async function autosave(): Promise<void> {
  if (isAutoSaving.value) return;
  isAutoSaving.value = true;
  toast.info('Performing autosave...');
  try {
    await saveScript();
    toast.success('Autosave successful');
  } catch {
    toast.error('Autosave failed');
  } finally {
    isAutoSaving.value = false;
  }
}

function calculateNavbarHeight(): void {
  const navbar = document.querySelector('.navbar');
  navbarHeight.value = navbar ? (navbar as HTMLElement).offsetHeight : 56;
}

function enterBulkEditMode(): void {
  bulkEditMode.value = true;
  bulkEditStart.value = null;
  bulkEditEnd.value = null;
}

function exitBulkEditMode(): void {
  bulkEditMode.value = false;
  bulkEditStart.value = null;
  bulkEditEnd.value = null;
  previousLineOfStart.value = null;
  nextLineOfEnd.value = null;
}

function onSetBulkStart(index: number): void {
  bulkEditStart.value = { page: currentPage.value, lineIndex: index };
  bulkEditEnd.value = null;
}

function onSetBulkEnd(index: number): void {
  if (bulkEditStart.value) {
    const { page: startPage, lineIndex: startIndex } = bulkEditStart.value;
    if (startPage === currentPage.value && index <= startIndex) {
      toast.error('End line must come after start line');
      return;
    }
    if (currentPage.value < startPage) {
      toast.error('End line must come after start line');
      return;
    }
  }
  bulkEditEnd.value = { page: currentPage.value, lineIndex: index };
}

function isBulkStart(index: number): boolean {
  return (
    bulkEditStart.value != null &&
    bulkEditStart.value.page === currentPage.value &&
    bulkEditStart.value.lineIndex === index
  );
}

function isBulkEnd(index: number): boolean {
  return (
    bulkEditEnd.value != null &&
    bulkEditEnd.value.page === currentPage.value &&
    bulkEditEnd.value.lineIndex === index
  );
}

async function loadBoundaryLines(): Promise<void> {
  if (!bulkEditStart.value || !bulkEditEnd.value) return;
  const { page: startPage, lineIndex: startIndex } = bulkEditStart.value;
  const { page: endPage, lineIndex: endIndex } = bulkEditEnd.value;

  if (startIndex === 0 && startPage > 1) await loadPage(startPage - 1);
  const endPageLines = scriptConfigStore.getTmpPage(endPage);
  if (endLines_isLast(endPageLines, endIndex)) await loadPage(endPage + 1);

  const startPageLines = scriptConfigStore.getTmpPage(startPage);
  if (startIndex > 0) {
    previousLineOfStart.value = startPageLines[startIndex - 1] ?? null;
  } else if (startPage > 1) {
    previousLineOfStart.value = scriptConfigStore.getTmpPage(startPage - 1).slice(-1)[0] ?? null;
  } else {
    previousLineOfStart.value = null;
  }

  nextLineOfEnd.value =
    endIndex < endPageLines.length - 1
      ? (endPageLines[endIndex + 1] ?? null)
      : (scriptConfigStore.getTmpPage(endPage + 1)[0] ?? null);
}

function endLines_isLast(lines: ScriptLine[], index: number): boolean {
  return index === lines.length - 1;
}

async function onBulkApply(payload: {
  actId: number | null;
  sceneId: number | null;
  partIndex: number | null;
  characterId: number | null;
  characterGroupId: number | null;
}): Promise<void> {
  if (!bulkEditStart.value || !bulkEditEnd.value) return;
  const { page: startPage, lineIndex: startIndex } = bulkEditStart.value;
  const { page: endPage, lineIndex: endIndex } = bulkEditEnd.value;

  const applyActScene = payload.actId != null && payload.sceneId != null;
  const applyCharacter =
    payload.partIndex != null && (payload.characterId != null || payload.characterGroupId != null);
  const targetPartIdx = (payload.partIndex ?? 1) - 1;

  for (let p = startPage; p <= endPage; p++) {
    await loadPage(p);
    const pageLines = scriptConfigStore.getTmpPage(p);
    const fromIdx = p === startPage ? startIndex : 0;
    const toIdx = p === endPage ? endIndex : pageLines.length - 1;
    const deletedOnPage = scriptConfigStore.getDeletedLines(p);
    for (let i = fromIdx; i <= toIdx; i++) {
      if (deletedOnPage.includes(i)) continue;
      const updatedLine = { ...pageLines[i] };
      if (applyActScene) {
        updatedLine.act_id = payload.actId!;
        updatedLine.scene_id = payload.sceneId!;
      }
      if (applyCharacter) {
        const sortedParts = [...updatedLine.line_parts].sort(
          (a, b) => (a.part_index ?? 0) - (b.part_index ?? 0)
        );
        if (sortedParts.length > targetPartIdx) {
          updatedLine.line_parts = sortedParts.map((part, idx) =>
            idx === targetPartIdx
              ? {
                  ...part,
                  character_id: payload.characterId,
                  character_group_id: payload.characterGroupId,
                }
              : part
          );
        }
      }
      scriptConfigStore.setLine(p, i, updatedLine);
    }
  }

  bulkModal.value?.hide();
  exitBulkEditMode();
}

watch(bulkEditEnd, async (val) => {
  if (val != null) {
    await loadBoundaryLines();
    bulkModal.value?.show();
  }
});

watch(isEditor, () => setupAutoSave());
watch(
  () => userStore.userSettings,
  () => setupAutoSave()
);

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
    scriptStore.getCuts(),
  ]);

  linePartCuts.value = [...scriptStore.cuts];

  const storedPage = localStorage.getItem('scriptEditPage');
  const startPage = storedPage == null ? 1 : Number.parseInt(storedPage, 10);
  await goToPageInner(startPage);

  loaded.value = true;
  setupAutoSave();
});

onUnmounted(() => {
  window.removeEventListener('resize', calculateNavbarHeight);
  if (autoSaveInterval.value != null) clearInterval(autoSaveInterval.value);
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
