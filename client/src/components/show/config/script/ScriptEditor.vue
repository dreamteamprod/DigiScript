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
              <BButton
                variant="success"
                :disabled="!canSave && !isAutoSaving"
                :title="saveDisabledReason ?? undefined"
                @click="saveScript"
              >
                Save
              </BButton>
            </template>
          </BButtonGroup>
        </BCol>
      </BRow>
      <BRow class="script-row">
        <BCol cols="1" />
        <BCol cols="1">Act</BCol>
        <BCol cols="1">Scene</BCol>
        <BCol>Line</BCol>
      </BRow>
    </div>

    <SelectionBar
      v-if="selectionCount > 0"
      :count="selectionCount"
      :range-label="selectionRangeLabel"
      @set-character="openSetCharacterDialog"
      @move-to-scene="openMoveToSceneDialog"
      @delete="onDeleteSelection"
      @clear="clearSelection"
    />

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
              :stage-direction-styles="scriptStore.stageDirectionStyles"
              @update:model-value="onLineChange(index, $event)"
              @done-editing="doneEditingLine(currentPage, index)"
              @finish-and-add-line="finishAndAddLine(currentPage, index)"
              @delete-line="deleteLine(currentPage, index)"
              @navigate-up="navigateUp(currentPage, index)"
              @navigate-down="navigateDown(currentPage, index)"
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
              :selected="isLineSelected(index)"
              @edit-line="beginEditingLine(currentPage, index)"
              @cut-line-part="cutLinePart"
              @toggle-select="onToggleSelect(index)"
            />
            <BRow
              v-if="canEdit && !scriptConfigStore.cutMode && index < currentPageLines.length - 1"
            >
              <BCol cols="1" />
              <BCol cols="1" />
              <BCol cols="1" />
              <BCol>
                <AddLineDivider
                  :line-number="index + 1"
                  @add="insertLineAt(currentPage, index, $event)"
                />
              </BCol>
              <BCol cols="1" />
            </BRow>
          </template>
        </template>
      </BCol>
    </BRow>
    <BRow v-if="canEdit && !scriptConfigStore.cutMode" class="script-row add-end-footer">
      <BCol cols="12" class="d-flex align-items-center flex-wrap gap-2">
        <span class="text-muted small me-1">Add to end of page</span>
        <BButton variant="primary" @click="addNewLine(LINE_TYPES.DIALOGUE)">Add Dialogue</BButton>
        <BButton variant="outline-light" @click="addNewLine(LINE_TYPES.STAGE_DIRECTION)"
          >Add Direction</BButton
        >
        <BButton variant="outline-light" @click="addNewLine(LINE_TYPES.CUE_LINE)">Add Cue</BButton>
        <BButton variant="outline-light" @click="addNewLine(LINE_TYPES.SPACING)">Add Gap</BButton>
      </BCol>
    </BRow>

    <SaveProgressModal
      ref="saveModal"
      :in-progress="savingInProgress"
      :current-page="curSavePage"
      :total-pages="totalSavePages ?? 0"
      :error="saveError ? 'Could not save script changes.' : null"
    />

    <SetCharacterOrGroupDialog
      ref="setCharDialog"
      :lines="selectionPreviewLines"
      :characters="showStore.characterList"
      :character-groups="showStore.characterGroupList"
      @apply="onSetCharacterApply"
    />

    <BulkActSceneModal
      ref="moveToSceneModal"
      :previous-line-of-start="previousLineOfStart"
      :next-line-of-end="nextLineOfEnd"
      :acts="showStore.actList"
      :scenes="showStore.sceneList"
      @apply="onMoveToSceneApply"
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
import log from 'loglevel';
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
import { useAutoSave } from '@/composables/useAutoSave';
import { toast } from '@/js/toast';
import { lineTypeLabel } from '@/js/lineTypeLabels';
import { firstInvalidScriptLine } from '@/js/scriptDraftValidation';
import ScriptLineEditor from './ScriptLineEditor.vue';
import ScriptLineViewer from './ScriptLineViewer.vue';
import AddLineDivider from './AddLineDivider.vue';
import SelectionBar from './SelectionBar.vue';
import SetCharacterOrGroupDialog, {
  type SelectedLinePreview,
} from './SetCharacterOrGroupDialog.vue';
import BulkActSceneModal from './BulkActSceneModal.vue';
import SaveProgressModal from './SaveProgressModal.vue';
import type { ScriptLine } from '@/types/api/script';
import type { BulkEditPayload } from '@/types/bulkEdit';
import { applyBulkPayloadToLine } from '@/js/bulkEditLine';

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
const linePartCuts = ref<number[]>([]);
const savingInProgress = ref(false);
const saveError = ref(false);
const curSavePage = ref(0);
const totalSavePages = ref<number | null>(null);
const changingPage = ref(false);
const isAutoSaving = ref(false);
// Selection range (Design E's "tick a line number"), confined to the current page —
// navigating pages clears it (see decrPage/incrPage/goToPage below). Kept as the same
// {page, lineIndex} shape the old Bulk Edit used, since Move to Scene's valid-act/
// scene calculation still needs the line just before/after the range.
const bulkEditStart = ref<{ page: number; lineIndex: number } | null>(null);
const bulkEditEnd = ref<{ page: number; lineIndex: number } | null>(null);
const previousLineOfStart = ref<ScriptLine | null>(null);
const nextLineOfEnd = ref<ScriptLine | null>(null);
const pageInputNo = ref(1);

const saveModal = ref<InstanceType<typeof SaveProgressModal>>();
const goToPageModal = ref<InstanceType<typeof BModal>>();
const setCharDialog = ref<InstanceType<typeof SetCharacterOrGroupDialog>>();
const moveToSceneModal = ref<InstanceType<typeof BulkActSceneModal>>();

const currentPageLines = computed(() => scriptConfigStore.getTmpPage(currentPage.value));
const deletedLines = computed(() => scriptConfigStore.getDeletedLines(currentPage.value));

const isEditor = computed(
  () =>
    wsStore.internalUUID !== null &&
    wsStore.internalUUID === scriptConfigStore.editStatus.currentEditor
);
const canEdit = computed(() => isEditor.value);

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

// Only the loaded pages (scriptConfigStore.tmpScript) are checked — an unloaded page
// is untouched saved data, already valid when it was last saved.
const isCompactMode = computed(() => systemStore.currentShow?.script_mode !== 1);
const firstInvalidLine = computed(() =>
  scriptConfigStore.cutMode
    ? null
    : firstInvalidScriptLine(scriptConfigStore.tmpScript, isCompactMode.value)
);

const canSave = computed(() => {
  if (scriptConfigStore.cutMode) return scriptChanges.value;
  return scriptChanges.value && editingLines.value.size === 0 && firstInvalidLine.value === null;
});
const saveDisabledReason = computed<string | null>(() => {
  if (canSave.value || scriptConfigStore.cutMode) return null;
  if (editingLines.value.size > 0) return 'Finish editing the open line(s) before saving';
  if (firstInvalidLine.value) {
    return `Page ${firstInvalidLine.value.page}: ${firstInvalidLine.value.error}`;
  }
  return null;
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
  clearSelection();
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
  clearSelection();
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
  clearSelection();
  currentPage.value++;
  await loadPage(currentPage.value);
  // Preload next page
  await loadPage(currentPage.value + 1);
}

async function goToPageInner(page: number): Promise<void> {
  const MRU_LOOK_BACK = 4;
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
  clearSelection();
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
  editingLines.value.delete(`page_${pageIndex}_line_${lineIndex}`);
}

/** Enter in the text field (Design E's keyboard flow): close this line and open a
 * fresh blank dialogue line right below it. Distinct from plain `doneEditingLine`
 * (Done/Esc), which never adds anything — see ScriptLineEditor.vue's own emits. */
function finishAndAddLine(pageIndex: number, lineIndex: number): void {
  doneEditingLine(pageIndex, lineIndex);
  insertLineAt(pageIndex, lineIndex, LINE_TYPES.DIALOGUE).catch((err) => {
    log.error('Failed to add new line', err);
    toast.error('Unable to add a new line. Please try again.');
  });
}

function navigateUp(pageIndex: number, lineIndex: number): void {
  if (lineIndex <= 0) return;
  doneEditingLine(pageIndex, lineIndex);
  beginEditingLine(pageIndex, lineIndex - 1);
}

function navigateDown(pageIndex: number, lineIndex: number): void {
  const pageLines = scriptConfigStore.getTmpPage(pageIndex);
  if (lineIndex >= pageLines.length - 1) return;
  doneEditingLine(pageIndex, lineIndex);
  beginEditingLine(pageIndex, lineIndex + 1);
}

function deleteLine(pageIndex: number, lineIndex: number): void {
  const lineIdent = `page_${pageIndex}_line_${lineIndex}`;
  scriptConfigStore.deleteLine(pageIndex, lineIndex);
  editingLines.value.delete(lineIdent);

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

const autoSave = useAutoSave(autosave);

function setupAutoSave(): void {
  const settings = userStore.userSettings as {
    enable_script_auto_save?: boolean;
    script_auto_save_interval?: number;
  };
  autoSave.restart(
    isEditor.value && !!settings.enable_script_auto_save,
    settings.script_auto_save_interval ?? 5
  );
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

// ── Selection (Design E's checkboxes, replacing the old Bulk Edit mode toggle) ────

function clearSelection(): void {
  bulkEditStart.value = null;
  bulkEditEnd.value = null;
  previousLineOfStart.value = null;
  nextLineOfEnd.value = null;
}

/** A plain click always extends/collapses the range to the clicked line — no
 * modifier key required, so the whole flow works from the keyboard (Space on a
 * focused checkbox). Clicking inside the current range collapses it back down to
 * just that one line, which doubles as the "restart a selection" gesture. */
function onToggleSelect(index: number): void {
  if (!bulkEditStart.value || !bulkEditEnd.value) {
    bulkEditStart.value = { page: currentPage.value, lineIndex: index };
    bulkEditEnd.value = { page: currentPage.value, lineIndex: index };
    return;
  }
  const { lineIndex: startIndex } = bulkEditStart.value;
  const { lineIndex: endIndex } = bulkEditEnd.value;
  if (index < startIndex) {
    bulkEditStart.value = { page: currentPage.value, lineIndex: index };
  } else if (index > endIndex) {
    bulkEditEnd.value = { page: currentPage.value, lineIndex: index };
  } else {
    bulkEditStart.value = { page: currentPage.value, lineIndex: index };
    bulkEditEnd.value = { page: currentPage.value, lineIndex: index };
  }
}

function isLineSelected(index: number): boolean {
  if (!bulkEditStart.value || !bulkEditEnd.value) return false;
  if (bulkEditStart.value.page !== currentPage.value) return false;
  return index >= bulkEditStart.value.lineIndex && index <= bulkEditEnd.value.lineIndex;
}

const selectionCount = computed(() => {
  if (!bulkEditStart.value || !bulkEditEnd.value) return 0;
  return bulkEditEnd.value.lineIndex - bulkEditStart.value.lineIndex + 1;
});

const selectionRangeLabel = computed(() => {
  if (!bulkEditStart.value || !bulkEditEnd.value) return '';
  const first = bulkEditStart.value.lineIndex + 1;
  const last = bulkEditEnd.value.lineIndex + 1;
  return first === last ? `Line ${first}` : `Lines ${first} to ${last}`;
});

const selectionPreviewLines = computed<SelectedLinePreview[]>(() => {
  if (!bulkEditStart.value || !bulkEditEnd.value) return [];
  const { lineIndex: startIndex } = bulkEditStart.value;
  const { lineIndex: endIndex } = bulkEditEnd.value;
  const pageLines = scriptConfigStore.getTmpPage(currentPage.value);
  const result: SelectedLinePreview[] = [];
  for (let i = startIndex; i <= endIndex; i++) {
    const line = pageLines[i];
    if (!line) continue;
    result.push({
      label: `Line ${i + 1}`,
      lineTypeLabel: lineTypeLabel(line.line_type),
      parts: line.line_parts.map((p) => ({
        characterId: p.character_id,
        characterGroupId: p.character_group_id,
      })),
    });
  }
  return result;
});

async function loadBoundaryLines(): Promise<void> {
  if (!bulkEditStart.value || !bulkEditEnd.value) return;
  const { page: startPage, lineIndex: startIndex } = bulkEditStart.value;
  const { page: endPage, lineIndex: endIndex } = bulkEditEnd.value;

  if (startIndex === 0 && startPage > 1) await loadPage(startPage - 1);
  const endPageLines = scriptConfigStore.getTmpPage(endPage);
  if (endIndex === endPageLines.length - 1) await loadPage(endPage + 1);

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

async function openSetCharacterDialog(): Promise<void> {
  setCharDialog.value?.show();
}

async function openMoveToSceneDialog(): Promise<void> {
  await loadBoundaryLines();
  moveToSceneModal.value?.show();
}

/** Applies a change to every line in the active selection — shared by both the
 * "Set Character or Group" and "Move to Scene" actions, so each only has to build
 * its own half of a `BulkEditPayload` (the other half stays null). */
function applyToSelection(payload: BulkEditPayload): void {
  if (!bulkEditStart.value || !bulkEditEnd.value) return;
  const { lineIndex: startIndex } = bulkEditStart.value;
  const { lineIndex: endIndex } = bulkEditEnd.value;
  const pageLines = scriptConfigStore.getTmpPage(currentPage.value);
  for (let i = startIndex; i <= endIndex; i++) {
    if (!pageLines[i]) continue;
    scriptConfigStore.setLine(currentPage.value, i, applyBulkPayloadToLine(pageLines[i]!, payload));
  }
}

function onSetCharacterApply(assignee: {
  partIndex: number;
  characterId: number | null;
  characterGroupId: number | null;
}): void {
  // SetCharacterOrGroupDialog only emits once one of the two is set (its own
  // canApply gate) — this just narrows that into BulkEditPayload['assignee']'s
  // discriminated union shape.
  const narrowed: BulkEditPayload['assignee'] =
    assignee.characterId != null
      ? { partIndex: assignee.partIndex, characterId: assignee.characterId, characterGroupId: null }
      : assignee.characterGroupId != null
        ? {
            partIndex: assignee.partIndex,
            characterId: null,
            characterGroupId: assignee.characterGroupId,
          }
        : null;
  if (!narrowed) return;
  applyToSelection({ actScene: null, assignee: narrowed });
  setCharDialog.value?.hide();
  clearSelection();
}

function onMoveToSceneApply(payload: { actId: number; sceneId: number }): void {
  applyToSelection({ actScene: payload, assignee: null });
  moveToSceneModal.value?.hide();
  clearSelection();
}

/** Deletes the whole selection in descending index order — each `deleteLine` call
 * only shifts indices at or above the one it removed, so working top-down means
 * every earlier index in the loop is still the right one when its turn comes. */
function onDeleteSelection(): void {
  if (!bulkEditStart.value || !bulkEditEnd.value) return;
  const { lineIndex: startIndex } = bulkEditStart.value;
  const { lineIndex: endIndex } = bulkEditEnd.value;
  for (let i = endIndex; i >= startIndex; i--) {
    deleteLine(currentPage.value, i);
  }
  clearSelection();
}

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
.add-end-footer {
  /* Pinned to the bottom of the viewport regardless of scroll position, like
     .sticky-header is pinned to the top — Tim asked for this after the first
     build only showed it once scrolled all the way to the last line. */
  position: sticky;
  bottom: 0;
  z-index: 90;
  padding: 14px 12px;
  background: var(--body-background);
  /* box-shadow, not border-top: CollabScriptEditor.vue's own .sticky-header
     documents why a border on a sticky element paints over a popover that
     should sit above it in Chromium — same fix applied here pre-emptively.
     --bs-border-color (what the old border-top used) also resolves to
     Bootstrap's light default on this theme — --bs-gray-700 instead, same
     reasoning as ScriptLineEditor.vue's --bs-dark note. */
  box-shadow: 0 -1px 0 0 var(--bs-gray-700);
}
</style>
