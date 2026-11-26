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
      <!-- A disabled button's own title attribute never shows as a tooltip — Chromium
           (and most browsers) suppress hover events, including the ones a native
           tooltip needs, for a disabled form control entirely. The title is kept on
           the button too (for anything that does read it, e.g. assistive tech), but
           this is the only thing that actually puts the reason somewhere visible. -->
      <BRow v-if="saveDisabledReason" class="script-row">
        <BCol cols="12" class="text-end">
          <small class="text-muted save-disabled-reason">{{ saveDisabledReason }}</small>
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
              :previewed="isLinePreviewChanging(index)"
              @edit-line="beginEditingLine(currentPage, index)"
              @cut-line-part="cutLinePart"
              @toggle-select="onToggleSelect(index)"
              @hover-checkbox="onHoverCheckbox(index)"
              @unhover-checkbox="onUnhoverCheckbox(index)"
            />
            <BRow
              v-if="canEdit && !scriptConfigStore.cutMode && index < currentPageLines.length - 1"
              :class="{
                'add-line-divider-row-selected': isLineSelected(index) || isLineSelected(index + 1),
              }"
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
import { useAutoSave, autoSaveSettings } from '@/composables/useAutoSave';
import { toast } from '@/js/toast';
import { lineTypeLabel } from '@/js/lineTypeLabels';
import { firstInvalidScriptLine } from '@/js/scriptDraftValidation';
import { nextSelectionRange, type SelectionRange } from '@/js/scriptSelectionModel';
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
import { applyBulkPayloadToLine, narrowAssignee } from '@/js/bulkEditLine';

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
//
// Within a loaded page, only lines this session actually added or changed are
// validated — not every line on it. Two reasons: a soft-deleted line is a
// tombstone still sitting in the array (see scriptConfig.ts's deleteLine),
// hidden from the viewer with nothing on screen to fix it if it fails; and a
// pre-existing line the server already accepted (e.g. a legacy null act/scene,
// which the DB allows but this validator doesn't) must not block Save just for
// having been on a page this session happened to load, when it was never
// touched. computePageStatus (the same diff saveScript() itself uses to decide
// what to send) is what already answers "added or changed" correctly, splice
// shifts and all — reusing it here keeps this in sync with that for free.
const isCompactMode = computed(() => systemStore.currentShow?.script_mode !== 1);
const firstInvalidLine = computed(() => {
  if (scriptConfigStore.cutMode) return null;
  const toValidate: Record<string, ScriptLine[]> = {};
  for (const pageStr of Object.keys(scriptConfigStore.tmpScript)) {
    const tmpPage = scriptConfigStore.getTmpPage(pageStr);
    if (tmpPage.length === 0) continue;
    const deletedOnPage = scriptConfigStore.getDeletedLines(pageStr);
    const status = computePageStatus(
      scriptStore.getScriptPage(pageStr),
      tmpPage,
      deletedOnPage,
      scriptConfigStore.getInsertedLines(pageStr)
    );
    // computePageStatus splices every inserted line into its own comparison copy
    // at the same index before diffing, so an inserted line always equals
    // itself and lands in neither added nor updated — status.inserted is the
    // only place it's tracked at all, and must be included explicitly here.
    const toCheck = new Set(
      [...status.added, ...status.updated, ...status.inserted].filter(
        (i) => !deletedOnPage.includes(i)
      )
    );
    toValidate[pageStr] = tmpPage.filter((_, i) => toCheck.has(i));
  }
  return firstInvalidScriptLine(toValidate, isCompactMode.value);
});

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
  // insertBlankLine takes one of two paths depending on whether newLineIndex is
  // already a tombstoned slot: a real splice (every later index shifts up), or a
  // same-length replace into that slot (nothing shifts — see scriptConfig.ts's
  // own comment on this). editingLines must only shift for the former, or an
  // open editor past the reused slot ends up pointing at the wrong line.
  const willSplice = !scriptConfigStore.getDeletedLines(pageIndex).includes(newLineIndex);
  const line = blankLine(lineType);
  scriptConfigStore.insertBlankLine(pageIndex, newLineIndex, line);
  // The selection is raw-index-based and never remapped when lines shift (unlike
  // editingLines just below, which is) — clearing it is simpler and safer than
  // trying to shift it too, and inserting mid-selection is a narrow enough case
  // that losing the selection there is an acceptable trade.
  clearSelection();

  if (willSplice) {
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
  }

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
  // The checkbox the hover-preview is tracking is about to disappear (this
  // row turns into an edit card) — Chrome fires neither blur nor mouseleave
  // for a removed element, so without this the dashed preview could linger
  // on other rows until the mouse happens to cross another checkbox.
  hoveredIndex.value = null;
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
  const deletedOnPage = scriptConfigStore.getDeletedLines(pageIndex);
  let target = lineIndex - 1;
  while (target >= 0 && deletedOnPage.includes(target)) target--;
  if (target < 0) return;
  doneEditingLine(pageIndex, lineIndex);
  beginEditingLine(pageIndex, target);
}

function navigateDown(pageIndex: number, lineIndex: number): void {
  const pageLines = scriptConfigStore.getTmpPage(pageIndex);
  const deletedOnPage = scriptConfigStore.getDeletedLines(pageIndex);
  let target = lineIndex + 1;
  while (target < pageLines.length && deletedOnPage.includes(target)) target++;
  if (target >= pageLines.length) return;
  doneEditingLine(pageIndex, lineIndex);
  beginEditingLine(pageIndex, target);
}

function deleteLine(pageIndex: number, lineIndex: number): void {
  const lineIdent = `page_${pageIndex}_line_${lineIndex}`;
  // A saved line (id != null) is tombstoned in place — nothing splices, so no
  // other index moves. Only an unsaved line is actually spliced out. Checked
  // before the store call below, which is what makes that same decision.
  const willSplice = scriptConfigStore.getTmpPage(pageIndex)[lineIndex]?.id == null;
  scriptConfigStore.deleteLine(pageIndex, lineIndex);
  editingLines.value.delete(lineIdent);
  // See insertLineAt's own comment: the selection is never remapped on a shift,
  // so clear it rather than let it silently point at the wrong lines.
  clearSelection();

  if (willSplice) {
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
  // The Save button is disabled whenever !canSave, but autosave calls this
  // function directly on a timer regardless — without this, it could persist a
  // half-typed open line, or one firstInvalidLine would otherwise catch, that
  // the button itself would never have let through.
  if (editingLines.value.size > 0 || firstInvalidLine.value !== null) return;

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
  const { enabled, intervalMinutes } = autoSaveSettings(userStore.userSettings);
  autoSave.restart(isEditor.value && enabled, intervalMinutes);
}

async function autosave(): Promise<void> {
  // Same gate the Save button's own :disabled already enforces — checked here,
  // before either toast, so a tick that can't actually save anything (an open
  // editor, an invalid line) stays silent instead of claiming success for
  // nothing. saveScript()'s own copy of this guard stays as a backstop.
  if (isAutoSaving.value || !canSave.value) return;
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

/** A plain click always extends/shrinks/collapses the range to the clicked
 * line — no modifier key required, so the whole flow works from the keyboard
 * (Space on a focused checkbox). See nextSelectionRange's own doc comment for
 * exactly what each case does; the range-transition logic itself lives there
 * (shared with the hover preview below, and with CollabScriptEditor.vue) so
 * there's exactly one place that decides what a tick does. */
function onToggleSelect(index: number): void {
  const current = bulkEditStart.value && bulkEditEnd.value ? currentSelectionRange.value : null;
  const next = nextSelectionRange(current, index);
  if (!next) {
    clearSelection();
    return;
  }
  bulkEditStart.value = { page: currentPage.value, lineIndex: next.startIndex };
  bulkEditEnd.value = { page: currentPage.value, lineIndex: next.endIndex };
}

const currentSelectionRange = computed<SelectionRange | null>(() => {
  if (!bulkEditStart.value || !bulkEditEnd.value) return null;
  if (bulkEditStart.value.page !== currentPage.value) return null;
  return { startIndex: bulkEditStart.value.lineIndex, endIndex: bulkEditEnd.value.lineIndex };
});

function isLineSelected(index: number): boolean {
  const range = currentSelectionRange.value;
  return range != null && index >= range.startIndex && index <= range.endIndex;
}

// ── Hover preview (shows which lines would change before the user commits to
// a click — Tim found the contiguous-range model non-obvious until he'd
// already clicked) ─────────────────────────────────────────────────────────

const hoveredIndex = ref<number | null>(null);

function onHoverCheckbox(index: number): void {
  hoveredIndex.value = index;
}

function onUnhoverCheckbox(index: number): void {
  if (hoveredIndex.value === index) hoveredIndex.value = null;
}

const previewRange = computed<SelectionRange | null>(() => {
  if (hoveredIndex.value == null) return null;
  return nextSelectionRange(currentSelectionRange.value, hoveredIndex.value);
});

/** True while hovering shows this line's selected state is about to flip —
 * whichever direction, added to the range or dropped from it. */
function isLinePreviewChanging(index: number): boolean {
  if (hoveredIndex.value == null) return false;
  const inPreview = previewRange.value != null && isInRange(previewRange.value, index);
  return inPreview !== isLineSelected(index);
}

function isInRange(range: SelectionRange, index: number): boolean {
  return index >= range.startIndex && index <= range.endIndex;
}

/** Soft-deleted lines within [startIndex, endIndex] are tombstones still sitting
 * in the array (see scriptConfig.ts's deleteLine) — hidden from the viewer, so
 * they must stay out of anything the user sees as "N lines selected" or that
 * acts on the selection, or a 3-line visible selection containing one hidden
 * tombstone would show as "3 lines selected" with only 2 rows on screen. */
function visibleIndicesInRange(startIndex: number, endIndex: number): number[] {
  const deletedOnPage = scriptConfigStore.getDeletedLines(currentPage.value);
  const indices: number[] = [];
  for (let i = startIndex; i <= endIndex; i++) {
    if (!deletedOnPage.includes(i)) indices.push(i);
  }
  return indices;
}

const selectionCount = computed(() => {
  if (!bulkEditStart.value || !bulkEditEnd.value) return 0;
  return visibleIndicesInRange(bulkEditStart.value.lineIndex, bulkEditEnd.value.lineIndex).length;
});

const selectionRangeLabel = computed(() => {
  if (!bulkEditStart.value || !bulkEditEnd.value) return '';
  const first = bulkEditStart.value.lineIndex + 1;
  const last = bulkEditEnd.value.lineIndex + 1;
  return first === last ? `Line ${first}` : `Lines ${first} to ${last}`;
});

const selectionPreviewLines = computed<SelectedLinePreview[]>(() => {
  if (!bulkEditStart.value || !bulkEditEnd.value) return [];
  const pageLines = scriptConfigStore.getTmpPage(currentPage.value);
  const result: SelectedLinePreview[] = [];
  for (const i of visibleIndicesInRange(
    bulkEditStart.value.lineIndex,
    bulkEditEnd.value.lineIndex
  )) {
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
  const pageLines = scriptConfigStore.getTmpPage(currentPage.value);
  for (const i of visibleIndicesInRange(
    bulkEditStart.value.lineIndex,
    bulkEditEnd.value.lineIndex
  )) {
    if (!pageLines[i]) continue;
    scriptConfigStore.setLine(currentPage.value, i, applyBulkPayloadToLine(pageLines[i]!, payload));
  }
}

function onSetCharacterApply(assignee: {
  partIndex: number;
  characterId: number | null;
  characterGroupId: number | null;
}): void {
  const narrowed = narrowAssignee(assignee);
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
  const visible = visibleIndicesInRange(bulkEditStart.value.lineIndex, bulkEditEnd.value.lineIndex);
  // Descending order: each deleteLine call only shifts indices at or above the
  // one it removed (an unsaved line splices out), so working top-down means
  // every earlier index in this loop is still the right one when its turn comes.
  for (let i = visible.length - 1; i >= 0; i--) {
    deleteLine(currentPage.value, visible[i]!);
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
  hoveredIndex.value = null;
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
/* Matches .line-row-selected in ScriptLineViewer.vue exactly (that rule is
   scoped there and can't be reused directly) — applied to the whole wrapping
   row, not AddLineDivider's own inner element, so it's flush with the line
   rows' own left edge instead of starting a few columns in. Without this a
   selected range's background read as separate highlighted rows with a plain
   gap between each, rather than one continuous block. */
.add-line-divider-row-selected {
  background-color: rgba(var(--bs-success-rgb), 0.08);
  box-shadow: inset 3px 0 0 var(--bs-success);
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
