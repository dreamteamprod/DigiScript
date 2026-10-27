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
          <p>
            Current Page: {{ currentPage }}
            <span v-if="scriptConfigStore.hasDraft" class="text-warning ms-2">● Unsaved draft</span>
          </p>
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
            <template v-else>
              <BButton variant="warning" :disabled="draftStore.isDraftSaving" @click="stopEditing">
                Stop Editing
              </BButton>
              <BButton
                variant="success"
                :disabled="!canSave"
                :title="saveDisabledReason ?? undefined"
                @click="saveScript"
              >
                Save
              </BButton>
              <BButton
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
          <template v-for="(line, index) in draftLines" :key="line._uid">
            <CollabScriptLineEditor
              v-if="editingLines.has(line._uid)"
              :page="currentPage"
              :line="line"
              :line-type="line.line_type"
              :acts="showStore.actList"
              :scenes="showStore.sceneList"
              :characters="showStore.characterList"
              :character-groups="showStore.characterGroupList"
              :previous-line="draftPages.previousLineOf(currentPage, index)"
              :next-line="draftLines[index + 1] ?? null"
              :stage-direction-styles="scriptStore.stageDirectionStyles"
              @done-editing="doneEditingLine(line._uid)"
              @delete-line="deleteLine(line._uid)"
            />
            <ScriptLineViewer
              v-else
              :line-index="index"
              :line="line"
              :page="draftLines"
              :acts="showStore.actList"
              :scenes="showStore.sceneList"
              :characters="showStore.characterList"
              :character-groups="showStore.characterGroupList"
              :previous-line="draftPages.previousLineOf(currentPage, index)"
              :can-edit="canEditDraft"
              :line-part-cuts="[]"
              :stage-direction-styles="scriptStore.stageDirectionStyles"
              :stage-direction-style-overrides="userStore.stageDirectionStyleOverrides"
              :bulk-edit-mode="bulkEditMode"
              :is-bulk-start="isBulkStart(line)"
              :is-bulk-end="isBulkEnd(line)"
              @edit-line="beginEditingLine(line._uid)"
              @insert-dialogue="insertLineAt(index, LINE_TYPES.DIALOGUE)"
              @insert-stage-direction="insertLineAt(index, LINE_TYPES.STAGE_DIRECTION)"
              @insert-cue-line="insertLineAt(index, LINE_TYPES.CUE_LINE)"
              @insert-spacing="insertLineAt(index, LINE_TYPES.SPACING)"
              @delete-line="deleteLine(line._uid)"
              @set-bulk-start="onSetBulkStart(index)"
              @set-bulk-end="onSetBulkEnd(index)"
            />
          </template>
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
    <BRow v-if="canEditDraft" class="script-row pt-1">
      <BCol cols="10" class="ms-auto">
        <BButtonGroup style="float: right">
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

    <SaveProgressModal
      ref="saveModal"
      :in-progress="draftStore.isDraftSaving"
      :current-page="draftStore.pageSaveProgress?.page ?? 0"
      :total-pages="draftStore.pageSaveProgress?.total ?? 0"
      :error="!draftStore.isDraftSaving ? draftStore.lastCollabError : null"
    />

    <BulkEditModal
      ref="bulkModal"
      :previous-line-of-start="bulkPreviousLine"
      :next-line-of-end="bulkNextLine"
      :acts="showStore.actList"
      :scenes="showStore.sceneList"
      :characters="showStore.characterList"
      :character-groups="showStore.characterGroupList"
      @apply="onBulkApply"
    />

    <BModal ref="stopEditingModal" title="Stop Editing" hide-footer>
      <p>This draft has unsaved changes.</p>
      <p v-if="otherEditorUsernames.length > 0" class="text-warning">
        {{ otherEditorUsernames.join(', ') }}
        {{ otherEditorUsernames.length > 1 ? 'are' : 'is' }} also editing — discarding will clear
        their unsaved work too, not just yours.
      </p>
      <div class="d-flex justify-content-end gap-2">
        <BButton variant="secondary" @click="stopEditingModal?.hide()">Keep Editing</BButton>
        <BButton variant="warning" @click="keepDraftAndStop">Keep Draft</BButton>
        <BButton variant="danger" @click="discardAndStop">Discard</BButton>
      </div>
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
import { LINE_TYPES } from '@/constants/lineTypes';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import { useScriptStore } from '@/stores/script';
import { useScriptConfigStore } from '@/stores/scriptConfig';
import { useScriptDraftStore } from '@/stores/scriptDraft';
import { useUserStore } from '@/stores/user';
import { useWebSocketStore } from '@/stores/websocket';
import { useWebSocket } from '@/composables/useWebSocket';
import { useDraftPages } from '@/composables/useDraftPages';
import { useDraftWriter } from '@/composables/useDraftWriter';
import { useAutoSave } from '@/composables/useAutoSave';
import { toast } from '@/js/toast';
import { snapshotPagesToScriptLines } from '@/js/yjs/draftAdapter';
import { firstInvalidDraftLine } from '@/js/scriptDraftValidation';
import ScriptLineViewer from './ScriptLineViewer.vue';
import CollabScriptLineEditor from './CollabScriptLineEditor.vue';
import SaveProgressModal from './SaveProgressModal.vue';
import BulkEditModal from './BulkEditModal.vue';
import type { ScriptLine } from '@/types/api/script';
import type { DraftScriptLine } from '@/js/yjs/draftAdapter';
import type { LineUid } from '@/js/yjs/yjsSnapshot';

/**
 * The script editor for collaborative mode (`collaborative_script_editing` on). An
 * editor joins the shared draft, browses and edits it with line/text changes writing
 * straight through `useDraftWriter` (Phase 3 Step 3), saves/stops/discards it and
 * bulk-edits it (Step 4, see `onBulkApply`). Everyone else reads saved pages over
 * REST exactly as the classic editor's viewer does. Cuts are not yet implemented.
 * The classic `ScriptEditor.vue` is untouched and is what renders when the setting
 * is off.
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
const writer = useDraftWriter();

const loaded = ref(false);
const currentPage = ref(1);
const navbarHeight = ref(56);
const changingPage = ref(false);
const pageInputNo = ref(1);
const pageError = ref<string | null>(null);
const goToPageModal = ref<InstanceType<typeof BModal>>();
const saveModal = ref<InstanceType<typeof SaveProgressModal>>();
const stopEditingModal = ref<InstanceType<typeof BModal>>();
const bulkModal = ref<InstanceType<typeof BulkEditModal>>();
const bulkEditMode = ref(false);
// D6: a stable key, not an index — an insert/delete elsewhere in the draft (ours or
// another editor's) must not silently shift which lines a bulk edit lands on. Resolved
// back to a position only when the edit is actually applied (see onBulkApply).
const bulkEditStart = ref<{ page: number; lineUid: LineUid } | null>(null);
const bulkEditEnd = ref<{ page: number; lineUid: LineUid } | null>(null);
// True from a successful `stopEditing()` send until the server confirms we are no
// longer an editor. STOP_SCRIPT_EDIT's own ROOM_CLOSED (for the last editor) arrives
// before its GET_SCRIPT_CONFIG_STATUS broadcast, so without this flag `joinFailed`
// would show the "could not open the script draft" alert — with a Retry that would
// rejoin the room we just asked to leave — for that one round trip.
const stopRequested = ref(false);
// Lines currently open in a CollabScriptLineEditor, keyed by `_uid` — never by index or
// position, so another editor's concurrent insert/delete elsewhere on the page can't
// desync this set the way the classic editor's `page_N_line_I` keys would.
const editingLines = ref(new Set<string>());
// The most recently auto-added line (from "Add Dialogue"), so finishing it chains
// straight into another blank one for continuous typing, matching the classic editor.
const latestAddedLine = ref<string | null>(null);

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
const canEditDraft = computed(() => isEditor.value && draftReady.value);

// D1: the client-side half of "incomplete lines abort the whole save" — mirrors the
// server's exact validation rules so Save can disable itself with a reason before the
// round trip even happens, rather than letting the server reject it. `script_mode` is
// FULL for the value 1 (see ShowScriptType in models/show.py); anything else is treated
// as compact, matching the existing `scriptMode === 1` convention used elsewhere.
const isCompactMode = computed(() => systemStore.currentShow?.script_mode !== 1);
const firstInvalidLine = computed(() =>
  draftReady.value
    ? firstInvalidDraftLine(
        snapshotPagesToScriptLines(draftStore.pageSnapshots),
        isCompactMode.value
      )
    : null
);

// D8 (revised): the store's own canSaveDraft already covers dirty-or-has-a-kept-draft
// and not-already-saving; this adds the two things only this component knows about —
// a locally open line editor, and D1's whole-snapshot validity.
const canSave = computed(
  () => draftStore.canSaveDraft && editingLines.value.size === 0 && firstInvalidLine.value === null
);
const saveDisabledReason = computed<string | null>(() => {
  if (canSave.value) return null;
  if (editingLines.value.size > 0) return 'Finish editing the open line(s) before saving';
  if (firstInvalidLine.value) {
    return `Page ${firstInvalidLine.value.page}: ${firstInvalidLine.value.error}`;
  }
  return null; // nothing to save, or already saving — no specific reason to show
});

const otherEditorUsernames = computed(() =>
  scriptConfigStore.editors
    .filter((e) => e.internal_id !== wsStore.internalUUID)
    .map((e) => e.username)
);

// BulkEditModal's act/scene dropdowns use these to work out which acts/scenes are
// valid to offer without crossing into the surrounding, unselected lines — no
// page-preload needed (the whole draft doc syncs on join, unlike the classic editor's
// per-page REST loads), so these are plain reactive reads over the already-synced doc.
const bulkPreviousLine = computed<DraftScriptLine | null>(() => {
  if (!bulkEditStart.value) return null;
  const { page, lineUid } = bulkEditStart.value;
  const index = draftPages.linesFor(page).findIndex((l) => l._uid === lineUid);
  return index < 0 ? null : draftPages.previousLineOf(page, index);
});
const bulkNextLine = computed<DraftScriptLine | null>(() => {
  if (!bulkEditEnd.value) return null;
  const { page, lineUid } = bulkEditEnd.value;
  const lines = draftPages.linesFor(page);
  const index = lines.findIndex((l) => l._uid === lineUid);
  if (index < 0) return null;
  if (index + 1 < lines.length) return lines[index + 1] ?? null;
  for (let p = page + 1; p <= draftPages.maxPage.value; p += 1) {
    const nextPageLines = draftPages.linesFor(p);
    if (nextPageLines.length > 0) return nextPageLines[0] ?? null;
  }
  return null;
});

function isBulkStart(line: DraftScriptLine): boolean {
  return (
    bulkEditStart.value?.page === currentPage.value && bulkEditStart.value?.lineUid === line._uid
  );
}
function isBulkEnd(line: DraftScriptLine): boolean {
  return bulkEditEnd.value?.page === currentPage.value && bulkEditEnd.value?.lineUid === line._uid;
}

// Editor whose room is gone: a rejected join, ROOM_CLOSED, or the socket not up. Without
// this the user is an editor with no room and no way out but Stop Editing. Suppressed
// while our own stopEditing() is still awaiting confirmation (see stopRequested).
const joinFailed = computed(
  () => loaded.value && isEditor.value && !stopRequested.value && draftStore.status === 'idle'
);
const maxPage = draftPages.maxPage;
const atLastDraftPage = computed(() => draftReady.value && currentPage.value >= maxPage.value);

const draftLines = computed(() => (draftReady.value ? draftPages.linesFor(currentPage.value) : []));
const viewerLines = computed<ScriptLine[]>(() => scriptStore.getScriptPage(currentPage.value));

function viewerPreviousLine(index: number): ScriptLine | null {
  if (index > 0) return viewerLines.value[index - 1] ?? null;
  return scriptStore.getScriptPage(currentPage.value - 1).at(-1) ?? null;
}

function beginEditingLine(lineUid: string): void {
  editingLines.value.add(lineUid);
}

function doneEditingLine(lineUid: string): void {
  editingLines.value.delete(lineUid);
  if (latestAddedLine.value === lineUid) {
    latestAddedLine.value = null;
    addNewLine(LINE_TYPES.DIALOGUE);
  }
}

function deleteLine(lineUid: string): void {
  // Clear this first: a delete must never chain into another auto-added line the way
  // finishing one normally would.
  if (latestAddedLine.value === lineUid) latestAddedLine.value = null;
  writer.deleteLine(currentPage.value, lineUid);
  editingLines.value.delete(lineUid);
}

// `addLine` creates the new line's first part in the same transaction (so a peer, or a
// save, never observes a dialogue/stage-direction line with none) — that means a fresh
// line already has one part by the time CollabScriptLineEditor mounts, so its own
// onMounted seeding (guarded on `line_parts.length === 0`) never runs for it. Seed the
// character here instead, the same lookup addLinePart() does for a part added later.
function seedFirstPart(
  lineType: number,
  anchor: DraftScriptLine | null | undefined
): { characterId?: number | null; characterGroupId?: number | null } | undefined {
  if (lineType !== LINE_TYPES.DIALOGUE || !anchor) return undefined;
  const prevPart = anchor.line_parts[0];
  if (!prevPart) return undefined;
  if (prevPart.character_id != null) return { characterId: prevPart.character_id };
  if (prevPart.character_group_id != null) return { characterGroupId: prevPart.character_group_id };
  return undefined;
}

function addNewLine(lineType: number): void {
  const insertIndex = draftLines.value.length;
  const prev = draftPages.previousLineOf(currentPage.value, insertIndex);
  const { lineUid } = writer.addLine(currentPage.value, {
    lineType,
    actId: prev?.act_id ?? null,
    sceneId: prev?.scene_id ?? null,
    part: seedFirstPart(lineType, prev),
  });
  editingLines.value.add(lineUid);
  latestAddedLine.value = lineUid;
}

function insertLineAt(index: number, lineType: number): void {
  const anchor: DraftScriptLine | undefined = draftLines.value[index];
  const { lineUid } = writer.addLine(currentPage.value, {
    lineType,
    actId: anchor?.act_id ?? null,
    sceneId: anchor?.scene_id ?? null,
    index: index + 1,
    part: seedFirstPart(lineType, anchor),
  });
  editingLines.value.add(lineUid);
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
  if (!Number.isInteger(target) || target < 1) {
    pageError.value = 'Enter a page number of 1 or more.';
    return;
  }
  if (draftReady.value && target > maxPage.value) {
    pageError.value = `Page ${target} does not exist yet — the last page is ${maxPage.value}.`;
    return;
  }
  pageError.value = null;
  changingPage.value = true;
  try {
    await navigateTo(target);
    goToPageModal.value?.hide();
  } catch {
    pageError.value = 'Could not load that page — check the connection and try again.';
  } finally {
    changingPage.value = false;
  }
}

function requestEdit(): void {
  if (!sendObj({ OP: 'REQUEST_SCRIPT_EDIT', DATA: { collab: true } })) {
    toast.error('Cannot edit script: not connected to the server');
  }
}

// STOP only: the server only demotes, checkpoints and closes the room for a client
// that is still in it (LEAVE_SCRIPT_ROOM first would remove us before STOP arrives,
// so the server would skip both). ROOM_CLOSED (if we were the last editor) or the
// isEditor watcher below then tears down the local draft.
function sendStop(): void {
  if (sendObj({ OP: 'STOP_SCRIPT_EDIT', DATA: {} })) {
    stopRequested.value = true;
  } else {
    toast.error('Cannot stop editing: not connected to the server');
  }
}

// D9: with nothing unsaved, stop immediately (today's behaviour) — only an actually
// dirty or previously-kept draft needs the keep-or-discard choice.
function stopEditing(): void {
  if (!draftStore.isDraftDirty && !scriptConfigStore.hasDraft) {
    sendStop();
    return;
  }
  stopEditingModal.value?.show();
}

function keepDraftAndStop(): void {
  stopEditingModal.value?.hide();
  sendStop();
}

function discardAndStop(): void {
  stopEditingModal.value?.hide();
  if (draftStore.discardDraft()) {
    // Same reason as sendStop(): ROOM_CLOSED can arrive before the
    // GET_SCRIPT_CONFIG_STATUS broadcast that drops us from `editors`, which
    // would otherwise flash the "could not open the script draft" alert for
    // that one round trip. Only set once the frame actually sent — setting it
    // unconditionally would hide that alert even when nothing was sent.
    stopRequested.value = true;
  }
}

function retryJoin(): void {
  if (!draftStore.isDraftActive) draftStore.joinScriptRoom();
}

function saveScript(): void {
  if (!canSave.value) return;
  // Show the modal only once the save has actually started — saveDraft() can
  // fail synchronously (socket down) without ever setting isDraftSaving or
  // lastCollabError, which would otherwise leave the modal showing "Finished
  // saving script." for a save that never left the browser.
  if (draftStore.saveDraft()) {
    saveModal.value?.show();
  }
}

// D10, lighter-touch per Tim's decision: no blocking modal (the draft is already
// synced/checkpointed server-side, so autosave's own stakes are lower than the classic
// editor's REST-only edits), and silently skip rather than error when the snapshot
// currently fails D1's validator — a half-typed line elsewhere in the draft would
// otherwise fail *every* editor's autosave tick, not just show a local error. A real
// manual Save still runs the full round trip and surfaces a real SAVE_ERROR on failure.
function autosaveTick(): void {
  if (!canSave.value) return;
  draftStore.saveDraft();
}

const autoSave = useAutoSave(autosaveTick);

function setupAutoSave(): void {
  const settings = userStore.userSettings as {
    enable_script_auto_save?: boolean;
    script_auto_save_interval?: number;
  };
  autoSave.restart(
    canEditDraft.value && !!settings.enable_script_auto_save,
    settings.script_auto_save_interval ?? 5
  );
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
}

function onSetBulkStart(index: number): void {
  const line = draftLines.value[index];
  if (!line) return;
  bulkEditStart.value = { page: currentPage.value, lineUid: line._uid };
  bulkEditEnd.value = null;
}

function onSetBulkEnd(index: number): void {
  const line = draftLines.value[index];
  if (!line) return;
  if (bulkEditStart.value) {
    const { page: startPage, lineUid: startUid } = bulkEditStart.value;
    if (currentPage.value < startPage) {
      toast.error('End line must come after start line');
      return;
    }
    if (currentPage.value === startPage) {
      const startIndex = draftLines.value.findIndex((l) => l._uid === startUid);
      if (startIndex !== -1 && index <= startIndex) {
        toast.error('End line must come after start line');
        return;
      }
    }
  }
  bulkEditEnd.value = { page: currentPage.value, lineUid: line._uid };
}

// D6: bulk edit resolves its stored {page, lineUid} boundaries back to a position only
// here, at apply time — an insert/delete elsewhere since the boundaries were picked
// (ours or another editor's) shifts indices but never the line this was meant to cover.
// If either boundary line is gone by now, abort rather than guess a new range.
function applyBulkActScene(
  page: number,
  line: DraftScriptLine,
  actId: number,
  sceneId: number
): void {
  writer.setLineActScene(page, line._uid, actId, sceneId);
}

function applyBulkCharacter(
  page: number,
  line: DraftScriptLine,
  targetPartIndex: number,
  characterId: number | null,
  characterGroupId: number | null
): void {
  const sortedParts = [...line.line_parts].sort(
    (a, b) => (a.part_index ?? 0) - (b.part_index ?? 0)
  );
  const targetPart = sortedParts[targetPartIndex];
  if (targetPart) {
    writer.setPartCharacter(page, line._uid, targetPart._uid, characterId, characterGroupId);
  }
}

/** What onBulkApply() applies to a single line, pulled out of its double-nested loop. */
function applyBulkEditToLine(
  page: number,
  line: DraftScriptLine,
  actScene: { actId: number; sceneId: number } | null,
  character: {
    targetPartIndex: number;
    characterId: number | null;
    characterGroupId: number | null;
  } | null
): void {
  if (actScene) applyBulkActScene(page, line, actScene.actId, actScene.sceneId);
  if (character) {
    applyBulkCharacter(
      page,
      line,
      character.targetPartIndex,
      character.characterId,
      character.characterGroupId
    );
  }
}

function onBulkApply(payload: {
  actId: number | null;
  sceneId: number | null;
  partIndex: number | null;
  characterId: number | null;
  characterGroupId: number | null;
}): void {
  if (!bulkEditStart.value || !bulkEditEnd.value) return;
  const { page: startPage, lineUid: startUid } = bulkEditStart.value;
  const { page: endPage, lineUid: endUid } = bulkEditEnd.value;

  const startIndex = draftPages.linesFor(startPage).findIndex((l) => l._uid === startUid);
  const endIndex = draftPages.linesFor(endPage).findIndex((l) => l._uid === endUid);
  if (startIndex === -1 || endIndex === -1) {
    toast.error('Could not apply the bulk edit — the start or end line no longer exists');
    bulkModal.value?.hide();
    exitBulkEditMode();
    return;
  }

  const actScene =
    payload.actId != null && payload.sceneId != null
      ? { actId: payload.actId, sceneId: payload.sceneId }
      : null;
  const applyCharacter =
    payload.partIndex != null && (payload.characterId != null || payload.characterGroupId != null);
  const targetPartIndex = (payload.partIndex ?? 1) - 1;

  // transact() is reentrant: each writer call below opens its own transaction with
  // the same LOCAL_EDIT_ORIGIN, which Yjs merges into this already-open outer one
  // rather than committing separately — so the whole bulk edit reaches peers as one
  // update.
  const character = applyCharacter
    ? {
        targetPartIndex,
        characterId: payload.characterId,
        characterGroupId: payload.characterGroupId,
      }
    : null;

  writer.transact(() => {
    for (let p = startPage; p <= endPage; p += 1) {
      const pageLines = draftPages.linesFor(p);
      const fromIndex = p === startPage ? startIndex : 0;
      const toIndex = p === endPage ? endIndex : pageLines.length - 1;
      for (let i = fromIndex; i <= toIndex; i += 1) {
        const line = pageLines[i];
        if (!line) continue; // the page shrank since linesFor() was read for the loop bounds
        applyBulkEditToLine(p, line, actScene, character);
      }
    }
  });

  bulkModal.value?.hide();
  exitBulkEditMode();
}

watch(bulkEditEnd, (val) => {
  if (val != null) bulkModal.value?.show();
});

function calculateNavbarHeight(): void {
  const navbar = document.querySelector('.navbar');
  navbarHeight.value = navbar ? (navbar as HTMLElement).offsetHeight : 56;
}

watch(isEditor, async (now, was) => {
  if (now && !was) {
    retryJoin();
  } else if (!now && was) {
    // The server has confirmed we're no longer an editor (our own stop, or losing
    // the lock some other way) — stopRequested has done its job, if it was set.
    stopRequested.value = false;
    editingLines.value.clear();
    latestAddedLine.value = null;
    draftStore.leaveScriptRoom();
    await loadViewerPage(currentPage.value);
  }
});

// Belt-and-braces: if a STOP frame is sent but never actually registers server-side
// (e.g. the socket drops right after, or the #1427 reconnect grace window keeps
// is_editor alive across it), isEditor never flips false and the watcher above never
// resets stopRequested — it would stay stuck true, silently eating any later real
// join failure. Any fresh join (ours or a resumed one) means that earlier stop, if it
// was ever in flight, is moot, so clear the flag whenever one starts. flush: 'sync' is
// required, not cosmetic: _rejoinAfterReconnect() does _teardown() (-> 'idle') then
// joinScriptRoom() (-> 'joining') synchronously in one tick, and if status was already
// 'joining' when that happens (STOP clicked mid-join, frame lost, fast reconnect before
// the join watchdog fires), the net change over the tick is 'joining' -> 'joining' —
// the default pre-flush watcher would never see an intermediate value and so never
// fire, leaving the flag stuck exactly as before.
watch(
  () => draftStore.status,
  (status) => {
    if (status === 'joining') stopRequested.value = false;
  },
  { flush: 'sync' }
);

// Pages are never removed, but the stored page (or a page from before a rejoin) may be
// past the last one that exists.
watch([draftReady, maxPage], () => {
  if (draftReady.value && currentPage.value > maxPage.value) {
    currentPage.value = maxPage.value;
  }
});

watch(canEditDraft, () => setupAutoSave());
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
  ]);

  const storedPage = Number.parseInt(localStorage.getItem('scriptEditPage') ?? '1', 10);
  currentPage.value = Number.isInteger(storedPage) && storedPage > 0 ? storedPage : 1;
  await loadViewerPage(currentPage.value);

  loaded.value = true;
  // Covers both a brief reconnect and a full page reload: the server holds
  // is_editor through a short reconnect grace window (issue #1419, fixed by #1427 —
  // REFRESH_CLIENT resumes the session row, confirmed once AUTHENTICATE succeeds),
  // so isEditor is already true here by the time this component re-mounts. No
  // client-side change was needed to pick that up.
  if (isEditor.value) retryJoin();
  setupAutoSave();
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
