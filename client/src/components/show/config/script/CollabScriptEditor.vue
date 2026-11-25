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
        <BCol cols="4" class="text-center">
          <p class="mb-2">
            Current Page: {{ currentPage }}
            <span v-if="scriptConfigStore.hasDraft" class="text-warning ms-2">● Unsaved draft</span>
          </p>
          <BDropdown
            v-if="presenceEntries.length > 0"
            variant="outline-secondary"
            no-caret
            toggle-class="presence-toggle"
            menu-class="presence-menu"
          >
            <template #button-content>
              <span class="presence-stack">
                <PresenceAvatar
                  v-for="entry in visiblePresenceEntries"
                  :key="entry.key"
                  size="sm"
                  :initials="entry.initials"
                  :color="entry.color"
                  :badge="entry.badge"
                  :title="entry.title"
                />
                <span v-if="overflowPresenceCount > 0" class="presence-avatar presence-avatar-sm">
                  +{{ overflowPresenceCount }}
                </span>
              </span>
              <span>{{ presenceCountLabel }}</span>
              <IMdiChevronDown />
            </template>

            <div class="presence-popover-header">
              <strong>Here now</strong>
              <span class="presence-people-count">{{ presenceEntries.length }} people</span>
            </div>
            <template v-for="entry in presenceEntries" :key="entry.key">
              <!-- `presence-row-item` (for locating a row) stays on BDropdownForm/
                   BDropdownItem, but the actual flex layout goes on the inner
                   `presence-row` div instead: both of those components apply a
                   slotted `class` to their own outer <li>, not the inner element the
                   slot content actually renders into, so a layout class placed
                   directly on them would never reach what it's meant to arrange. -->
              <BDropdownForm v-if="entry.isSelf" class="presence-row-item" @click.stop>
                <div class="presence-row">
                  <PresenceAvatar
                    :initials="entry.initials"
                    :color="entry.color"
                    :badge="entry.badge"
                    :title="entry.title"
                  />
                  <span class="presence-row-body">
                    <span class="presence-row-name">
                      {{ entry.username }}
                      <BBadge pill variant="secondary" class="presence-you-pill">You</BBadge>
                    </span>
                    <span class="presence-row-sub">{{ entry.subText }}</span>
                  </span>
                  <span class="presence-row-side">
                    <BBadge pill :variant="entry.roleVariant" class="presence-role-pill">{{
                      entry.role
                    }}</BBadge>
                  </span>
                </div>
              </BDropdownForm>
              <BDropdownItem
                v-else
                class="presence-row-item"
                :disabled="entry.page == null"
                @click="jumpToMember(entry)"
              >
                <div class="presence-row">
                  <PresenceAvatar
                    :initials="entry.initials"
                    :color="entry.color"
                    :badge="entry.badge"
                    :title="entry.title"
                  />
                  <span class="presence-row-body">
                    <span class="presence-row-name">{{ entry.username }}</span>
                    <span class="presence-row-sub">{{ entry.subText }}</span>
                  </span>
                  <span class="presence-row-side">
                    <BBadge pill :variant="entry.roleVariant" class="presence-role-pill">{{
                      entry.role
                    }}</BBadge>
                    <span v-if="entry.page != null" class="presence-jump">
                      Jump to <IMdiArrowRight />
                    </span>
                  </span>
                </div>
              </BDropdownItem>
            </template>
          </BDropdown>
        </BCol>
        <BCol cols="2" style="text-align: left">
          <BButton variant="success" :disabled="atLastDraftPage" @click="incrPage">
            Next Page
          </BButton>
        </BCol>
        <BCol cols="2">
          <BButtonGroup v-if="systemStore.isScriptEditor">
            <template v-if="scriptConfigStore.cutMode">
              <BButton variant="warning" @click="stopCutting">Stop Cutting</BButton>
              <BButton
                variant="success"
                :disabled="!cutsChanged || cuttingSaveInProgress"
                @click="saveCuts"
              >
                Save Cuts
              </BButton>
            </template>
            <template v-else-if="!isEditor">
              <BButton variant="warning" :disabled="hasCutters" @click="requestEdit">Edit</BButton>
              <BButton
                variant="warning"
                :disabled="cutsDisabledReason !== null"
                :title="cutsDisabledReason ?? undefined"
                @click="requestCuts"
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
      <BCol ref="linesContainer" cols="12">
        <template v-if="usesLiveRender">
          <template v-for="(line, index) in draftLines" :key="line._uid">
            <CollabScriptLineEditor
              v-if="editingLines.has(line._uid)"
              :data-line-uid="line._uid"
              :class="{ 'jump-highlight': jumpTargetLineUid === line._uid }"
              :page="currentPage"
              :line="line"
              :acts="showStore.actList"
              :scenes="showStore.sceneList"
              :characters="showStore.characterList"
              :character-groups="showStore.characterGroupList"
              :previous-line="draftPages.previousLineOf(currentPage, index)"
              :next-line="draftLines[index + 1] ?? null"
              :stage-direction-styles="scriptStore.stageDirectionStyles"
              :remote-editors="remoteEditorsByLineUid[line._uid] ?? []"
              @done-editing="doneEditingLine(line._uid)"
              @finish-and-add-line="finishAndAddLine(index)"
              @delete-line="deleteLine(line._uid)"
              @navigate-up="navigateUp(index)"
              @navigate-down="navigateDown(index)"
              @retype-line="retypeLine(line._uid, index, $event)"
            />
            <ScriptLineViewer
              v-else
              :data-line-uid="line._uid"
              :class="{ 'jump-highlight': jumpTargetLineUid === line._uid }"
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
              :remote-editors="remoteEditorsByLineUid[line._uid] ?? []"
              :stage-direction-styles="scriptStore.stageDirectionStyles"
              :stage-direction-style-overrides="userStore.stageDirectionStyleOverrides"
              :selected="isLineSelected(line._uid)"
              :previewed="isLinePreviewChanging(line._uid)"
              @edit-line="beginEditingLine(line._uid)"
              @toggle-select="onToggleSelect(line._uid, index)"
              @hover-checkbox="onHoverCheckbox(index)"
              @unhover-checkbox="onUnhoverCheckbox(index)"
            />
            <BRow
              v-if="canEditDraft && index < draftLines.length - 1"
              :class="{
                'add-line-divider-row-selected':
                  isLineSelected(line._uid) || isNextLineSelected(index),
              }"
            >
              <BCol cols="1" />
              <BCol cols="1" />
              <BCol cols="1" />
              <BCol>
                <AddLineDivider :line-number="index + 1" @add="insertLineAt(index, $event)" />
              </BCol>
              <BCol cols="1" />
            </BRow>
          </template>
        </template>
        <template v-else>
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
            :can-edit="scriptConfigStore.cutMode"
            :line-part-cuts="linePartCuts"
            :stage-direction-styles="scriptStore.stageDirectionStyles"
            :stage-direction-style-overrides="userStore.stageDirectionStyleOverrides"
            @cut-line-part="cutLinePart"
          />
        </template>
      </BCol>
    </BRow>
    <BRow v-if="canEditDraft" class="script-row add-end-footer">
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

    <SetCharacterOrGroupDialog
      ref="setCharDialog"
      :lines="selectionPreviewLines"
      :characters="showStore.characterList"
      :character-groups="showStore.characterGroupList"
      @apply="onSetCharacterApply"
    />

    <BulkActSceneModal
      ref="moveToSceneModal"
      :previous-line-of-start="bulkPreviousLine"
      :next-line-of-end="bulkNextLine"
      :acts="showStore.actList"
      :scenes="showStore.sceneList"
      @apply="onMoveToSceneApply"
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
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
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
import { useConfirm } from '@/composables/useConfirm';
import { toast } from '@/js/toast';
import { snapshotPagesToScriptLines } from '@/js/yjs/draftAdapter';
import { firstInvalidDraftLine } from '@/js/scriptDraftValidation';
import { lineTypeLabel } from '@/js/lineTypeLabels';
import { nextSelectionRange } from '@/js/scriptSelectionModel';
import { parseDbId } from '@/js/yjs/yjsSnapshot';
import ScriptLineViewer from './ScriptLineViewer.vue';
import CollabScriptLineEditor from './CollabScriptLineEditor.vue';
import AddLineDivider from './AddLineDivider.vue';
import SelectionBar from './SelectionBar.vue';
import SetCharacterOrGroupDialog, {
  type SelectedLinePreview,
} from './SetCharacterOrGroupDialog.vue';
import BulkActSceneModal from './BulkActSceneModal.vue';
import SaveProgressModal from './SaveProgressModal.vue';
import PresenceAvatar from './PresenceAvatar.vue';
import { presenceInitials, presenceColor, SELF_AVATAR_COLOR } from '@/js/presenceUtils';
import type { ScriptLine } from '@/types/api/script';
import type { DraftScriptLine } from '@/js/yjs/draftAdapter';
import type { LineUid } from '@/js/yjs/yjsSnapshot';
import type { BulkEditPayload } from '@/types/bulkEdit';

/**
 * The script editor for collaborative mode (`collaborative_script_editing` on). An
 * editor joins the shared draft, browses and edits it with line/text changes writing
 * straight through `useDraftWriter` (Phase 3 Step 3), saves/stops/discards it and
 * bulk-edits a selection of lines (Step 4, see `applyToSelection`). Everyone else also joins the room, as a
 * read-only viewer (Phase 4 Step A) — the server decides the role from `is_editor` at
 * join time, so a plain viewer sees the *live* draft, not stale saved content. Cut
 * mode (Step 5) is the one exception: it stays REST, like the classic editor's,
 * entered via `REQUEST_SCRIPT_CUTS` rather than `REQUEST_SCRIPT_EDIT` — exclusive with
 * draft mode, enforced server-side — so the REST render path is still used whenever
 * `cutMode` is on, even though the viewer is also quietly joined to the room in the
 * background by then. The classic `ScriptEditor.vue` is untouched and is what renders
 * when the setting is off.
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
const { confirm } = useConfirm();

const loaded = ref(false);
const currentPage = ref(1);
const navbarHeight = ref(56);
const changingPage = ref(false);
const pageInputNo = ref(1);
const pageError = ref<string | null>(null);
const goToPageModal = ref<InstanceType<typeof BModal>>();
const saveModal = ref<InstanceType<typeof SaveProgressModal>>();
const stopEditingModal = ref<InstanceType<typeof BModal>>();
const setCharDialog = ref<InstanceType<typeof SetCharacterOrGroupDialog>>();
const moveToSceneModal = ref<InstanceType<typeof BulkActSceneModal>>();
// Presence popover's "Jump to": the container line rows are rendered into, so a
// jump can find the target line's DOM node to scroll it into view, and the line
// uid to transiently flash-highlight (see jumpToMember below).
const linesContainer = ref<{ $el: HTMLElement } | null>(null);
const jumpTargetLineUid = ref<string | null>(null);
let jumpHighlightTimer: ReturnType<typeof setTimeout> | null = null;
// Cut mode (D11): REST, exclusive with draft mode, entered via REQUEST_SCRIPT_CUTS
// rather than REQUEST_SCRIPT_EDIT. scriptConfigStore.cutMode is a local-only flag
// shared with the classic editor and ScriptLineViewer (which reads it directly to
// decide whether to render its cut-clickable UI) — not derived from the server's
// `cutters` list, matching the classic editor's own optimistic set-then-roll-back
// pattern (requestEditFailure already resets it to false on a rejected request).
const linePartCuts = ref<number[]>([]);
const cuttingSaveInProgress = ref(false);
// D6: a stable key, not an index — an insert/delete elsewhere in the draft (ours or
// another editor's) must not silently shift which lines a bulk edit lands on. Resolved
// back to a position only when the edit is actually applied (see applyToSelection).
const bulkEditStart = ref<{ page: number; lineUid: LineUid } | null>(null);
const bulkEditEnd = ref<{ page: number; lineUid: LineUid } | null>(null);
// True from a successful `stopEditing()` send until the server confirms we are no
// longer an editor. STOP_SCRIPT_EDIT itself never closes the room — the caller is
// re-added to it as a viewer (Phase 4 Step A) — but an unrelated ROOM_CLOSED (e.g.
// another editor discarding) can still race it, arriving before the
// GET_SCRIPT_CONFIG_STATUS broadcast that reflects our own stop's already-committed
// demotion lands. Without this flag, that gap would show the "could not open the
// script draft" alert — with a Retry that would rejoin the room we just asked to
// leave — for that one round trip.
const stopRequested = ref(false);
// True for a brief grace window after any ROOM_CLOSED — our own (though
// stopRequested above already covers that case on its own) or another editor's,
// whether from a discard or from closing the draft via the REST DELETE endpoint.
// The server always commits any resulting demotion before sending ROOM_CLOSED; the
// GET_SCRIPT_CONFIG_STATUS broadcast that usually follows it only triggers the
// client's refetch of that already-committed state, it doesn't demote anyone
// itself — and not every room-closing path sends one (e.g. toggling collaborative
// editing off closes the room on its own WS_SETTINGS_CHANGED alone, and a show
// change closes it unconditionally — even with a still-dirty editor in it — on
// SHOW_CHANGED alone, which reloads the page outright so it doesn't matter here),
// but most paths that can still leave an editor in the room do. Without this
// window, `joinFailed` would flash the "could not open the script draft" alert for
// that gap. Cleared as soon as isEditor actually resolves (below), or — if the
// editors refresh never arrives or never drops us — after ROOM_CLOSE_GRACE_MS, so a
// genuinely stuck room still lands on Retry rather than staying silently suppressed
// forever.
const roomClosedGrace = ref(false);
const ROOM_CLOSE_GRACE_MS = 3_000;
let roomClosedGraceTimer: ReturnType<typeof setTimeout> | null = null;
function clearRoomClosedGrace(): void {
  if (roomClosedGraceTimer !== null) {
    clearTimeout(roomClosedGraceTimer);
    roomClosedGraceTimer = null;
  }
  roomClosedGrace.value = false;
}
function armRoomClosedGrace(): void {
  clearRoomClosedGrace();
  roomClosedGrace.value = true;
  roomClosedGraceTimer = setTimeout(() => {
    roomClosedGraceTimer = null;
    roomClosedGrace.value = false;
  }, ROOM_CLOSE_GRACE_MS);
}
// A plain viewer's backoff schedule for recovering from a room close with no
// action of their own — see the draftStore.status watch below.
const VIEWER_RECOVERY_DELAYS_MS = [3_000, 5_000, 10_000, 15_000, 30_000];
let viewerRecoveryTimer: ReturnType<typeof setTimeout> | null = null;
let viewerRecoveryAttempt = 0;
function clearViewerRecoveryTimer(): void {
  if (viewerRecoveryTimer !== null) {
    clearTimeout(viewerRecoveryTimer);
    viewerRecoveryTimer = null;
  }
}
// Lines currently open in a CollabScriptLineEditor, keyed by `_uid` — never by index or
// position, so another editor's concurrent insert/delete elsewhere on the page can't
// desync this set the way the classic editor's `page_N_line_I` keys would.
const editingLines = ref(new Set<string>());

// We are an editor when the server lists us among the editors. The server commits
// `is_editor` before it broadcasts GET_SCRIPT_CONFIG_STATUS, so this is also the moment
// the room will assign us the editor role on join.
const isEditor = computed(
  () =>
    wsStore.internalUUID !== null &&
    scriptConfigStore.editors.some((e) => e.internal_id === wsStore.internalUUID)
);
const hasCutters = computed(() => scriptConfigStore.cutters.length > 0);

// Phase 4 Step B: a presence badge row. ROOM_MEMBERS (draftStore.members) already
// carries everyone in the room with a role of 'editor' or 'viewer' — but a cutter
// auto-joins as a background viewer too (D11: cuts stay REST-always, the join is
// just for live sync), so that role alone would show them as merely "viewing",
// not cutting. Cross-referencing scriptConfigStore.cutters (keyed by the same
// internal_id/client_id) lets the badge say "cutting" instead — but only for an
// actual viewer: an editor who is also cutting (e.g. mid-REQUEST_SCRIPT_CUTS
// while still holding the edit lock) must keep showing as "editor", since that's
// the stronger/more specific role and what the rest of this page's state tracks.
interface PresenceEntry {
  key: string;
  clientId: string | null;
  username: string;
  role: 'editor' | 'viewer' | 'cutting';
  roleVariant: 'warning' | 'info' | 'secondary';
  isSelf: boolean;
  initials: string;
  color: string;
  badge: 'editing' | 'cutting' | null;
  title: string;
  /** The page this member is on, or null when no awareness broadcast has arrived
   * yet for them (self is always known, from `currentPage` directly). */
  page: number | null;
  openLineCount: number;
  subText: string;
}
const presenceEntries = computed<PresenceEntry[]>(() => {
  const cutterIds = new Set(scriptConfigStore.cutters.map((c) => c.internal_id));
  return draftStore.members.map((m, i) => {
    const isSelf = m.client_id !== null && m.client_id === wsStore.internalUUID;
    const role: PresenceEntry['role'] =
      m.role === 'editor'
        ? 'editor'
        : m.client_id && cutterIds.has(m.client_id)
          ? 'cutting'
          : m.role;
    const awareness = m.client_id ? draftStore.remoteAwareness[m.client_id] : undefined;
    const page = isSelf ? currentPage.value : (awareness?.currentPage ?? null);
    const openLineCount = isSelf ? editingLines.value.size : (awareness?.openLineUids.length ?? 0);
    const subTextParts = [page != null ? `Page ${page}` : 'Page unknown'];
    if (role === 'editor' && openLineCount > 0) {
      subTextParts.push(`${openLineCount} line${openLineCount > 1 ? 's' : ''} open`);
    }
    return {
      key: m.client_id ?? `${m.user_id ?? 'unknown'}-${i}`,
      clientId: m.client_id,
      username: m.username,
      role,
      roleVariant: role === 'editor' ? 'warning' : role === 'cutting' ? 'info' : 'secondary',
      isSelf,
      initials: presenceInitials(m.username),
      color: isSelf ? SELF_AVATAR_COLOR : presenceColor(m.username),
      badge: role === 'editor' ? 'editing' : role === 'cutting' ? 'cutting' : null,
      title: `${m.username}${isSelf ? ' (you)' : ''}, ${role}`,
      page,
      openLineCount,
      subText: subTextParts.join(' · '),
    };
  });
});
// Avatar-stack preview on the popover's own toggle button — capped so a busy room
// doesn't blow the header out, with a "+N" overflow chip for the rest.
const PRESENCE_STACK_LIMIT = 4;
const visiblePresenceEntries = computed(() => presenceEntries.value.slice(0, PRESENCE_STACK_LIMIT));
const overflowPresenceCount = computed(() =>
  Math.max(0, presenceEntries.value.length - PRESENCE_STACK_LIMIT)
);
const presenceCountLabel = computed(() =>
  presenceEntries.value.length <= 1 ? 'Only you' : `${presenceEntries.value.length} here`
);
// Phase 4 Step C: inverts draftStore.remoteAwareness (client_id -> open line uids) into
// line uid -> usernames, so a line row can look up "who else has this open" by its own
// _uid. A client_id with no resolvable username (e.g. briefly, during a role/member
// transition) is skipped rather than shown as "unknown" — the entry self-heals on the
// next ROOM_MEMBERS or awareness broadcast.
const remoteEditorsByLineUid = computed<Record<string, string[]>>(() => {
  const result: Record<string, string[]> = {};
  for (const [clientId, awareness] of Object.entries(draftStore.remoteAwareness)) {
    const username = draftStore.members.find((m) => m.client_id === clientId)?.username;
    if (!username) continue;
    for (const uid of awareness.openLineUids) {
      // Two different client_ids (e.g. two tabs/sessions of the same user — the e2e
      // harness for this exact feature logs both browsers in as "admin", so this is
      // the normal setup, not a corner case) can both have the same line open: dedupe
      // by username rather than pushing every occurrence, or RemoteEditorsBadge's
      // own v-for :key would collide on the repeated name.
      result[uid] ??= [];
      if (!result[uid].includes(username)) result[uid].push(username);
    }
  }
  return result;
});
// A set comparison, not an ordered one: cutLinePart() splice-then-pushes, so toggling
// an already-saved cut off and back on (without saving in between) reorders the same
// *set* of ids — an ordered JSON.stringify compare would see that as a change and
// spuriously enable Save Cuts for a no-op save.
const cutsChanged = computed(() => {
  if (linePartCuts.value.length !== scriptStore.cuts.length) return true;
  const saved = new Set(scriptStore.cuts);
  return linePartCuts.value.some((id) => !saved.has(id));
});
// Proactive client-side disable, mirroring _op_request_script_cuts's own rejection
// order — the server enforces every one of these regardless, this just avoids a
// round trip to find out.
const cutsDisabledReason = computed<string | null>(() => {
  if (hasCutters.value) return 'Someone else is already cutting the script';
  if (scriptConfigStore.editors.length > 0) return 'Script editing is in progress';
  if (scriptConfigStore.hasDraft) return 'Cuts are blocked while an unsaved draft exists';
  return null;
});

// Phase 4 Step A: a plain viewer joins the room too, so draftReady no longer implies
// isEditor — canEditDraft is the one that still does.
const draftReady = computed(() => draftStore.isDraftSynced);
const canEditDraft = computed(() => isEditor.value && draftReady.value);
// Cuts stay REST always (D11), even once a cutter is also quietly joined to the room
// as a viewer in the background — the live Y.Doc branch must not win over the REST
// cutting branch just because the viewer-join made draftReady true.
const usesLiveRender = computed(() => draftReady.value && !scriptConfigStore.cutMode);

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

// BulkActSceneModal's (Move to Scene) act/scene dropdowns use these to work out which acts/scenes are
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

// Resolves the stored {page, lineUid} boundaries to positions on demand, never
// cached across a render — an insert/delete elsewhere (ours or another editor's)
// must not let this read a stale index.
const selectionBounds = computed<{ startIndex: number; endIndex: number } | null>(() => {
  if (!bulkEditStart.value || !bulkEditEnd.value) return null;
  if (bulkEditStart.value.page !== currentPage.value) return null;
  const startIndex = draftLines.value.findIndex((l) => l._uid === bulkEditStart.value!.lineUid);
  const endIndex = draftLines.value.findIndex((l) => l._uid === bulkEditEnd.value!.lineUid);
  if (startIndex === -1 || endIndex === -1) return null;
  return { startIndex, endIndex };
});

function isLineSelected(lineUid: LineUid): boolean {
  const bounds = selectionBounds.value;
  if (!bounds) return false;
  const index = draftLines.value.findIndex((l) => l._uid === lineUid);
  return index !== -1 && index >= bounds.startIndex && index <= bounds.endIndex;
}

/** For the add-line-divider row sitting right after `index` — whether the
 * line below it is selected, so the divider can pick up the same highlight
 * (see ScriptEditor.vue's add-line-divider-row-selected for why). */
function isNextLineSelected(index: number): boolean {
  const nextLine = draftLines.value[index + 1];
  return nextLine != null && isLineSelected(nextLine._uid);
}

// ── Hover preview — see ScriptEditor.vue's own copy of this for the "why" ──

const hoveredIndex = ref<number | null>(null);

function onHoverCheckbox(index: number): void {
  hoveredIndex.value = index;
}

function onUnhoverCheckbox(index: number): void {
  if (hoveredIndex.value === index) hoveredIndex.value = null;
}

const previewRange = computed(() => {
  if (hoveredIndex.value == null) return null;
  return nextSelectionRange(selectionBounds.value, hoveredIndex.value);
});

function isLinePreviewChanging(lineUid: LineUid): boolean {
  if (hoveredIndex.value == null) return false;
  const index = draftLines.value.findIndex((l) => l._uid === lineUid);
  if (index === -1) return false;
  const range = previewRange.value;
  const inPreview = range != null && index >= range.startIndex && index <= range.endIndex;
  return inPreview !== isLineSelected(lineUid);
}

const selectionCount = computed(() => {
  const bounds = selectionBounds.value;
  return bounds ? bounds.endIndex - bounds.startIndex + 1 : 0;
});

const selectionRangeLabel = computed(() => {
  const bounds = selectionBounds.value;
  if (!bounds) return '';
  const first = bounds.startIndex + 1;
  const last = bounds.endIndex + 1;
  return first === last ? `Line ${first}` : `Lines ${first} to ${last}`;
});

const selectionPreviewLines = computed<SelectedLinePreview[]>(() => {
  const bounds = selectionBounds.value;
  if (!bounds) return [];
  const result: SelectedLinePreview[] = [];
  for (let i = bounds.startIndex; i <= bounds.endIndex; i++) {
    const line = draftLines.value[i];
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

function clearSelection(): void {
  bulkEditStart.value = null;
  bulkEditEnd.value = null;
}

/** A plain click always extends/shrinks/collapses the range to the clicked
 * line — see nextSelectionRange's own doc comment for exactly what each case
 * does; the range-transition logic lives there (shared with ScriptEditor.vue
 * and both editors' own hover-preview computation). `lineUid` is kept as a
 * parameter even though the body re-derives it from `index` via draftLines,
 * so the two editors' onToggleSelect keep a matching call shape. */
function onToggleSelect(lineUid: LineUid, index: number): void {
  const next = nextSelectionRange(selectionBounds.value, index);
  if (!next) {
    clearSelection();
    return;
  }
  const startUid = draftLines.value[next.startIndex]?._uid ?? lineUid;
  const endUid = draftLines.value[next.endIndex]?._uid ?? lineUid;
  bulkEditStart.value = { page: currentPage.value, lineUid: startUid };
  bulkEditEnd.value = { page: currentPage.value, lineUid: endUid };
}

// Editor whose room is gone: a rejected join, ROOM_CLOSED, or the socket not up. Without
// this the user is an editor with no room and no way out but Stop Editing. Suppressed
// while our own stopEditing() is still awaiting confirmation (see stopRequested), and
// for a brief grace window after any ROOM_CLOSED (see roomClosedGrace above).
const joinFailed = computed(
  () =>
    loaded.value &&
    isEditor.value &&
    !stopRequested.value &&
    !roomClosedGrace.value &&
    draftStore.status === 'idle'
);
const maxPage = draftPages.maxPage;
const atLastDraftPage = computed(() => draftReady.value && currentPage.value >= maxPage.value);

const draftLines = computed(() => (draftReady.value ? draftPages.linesFor(currentPage.value) : []));
const viewerLines = computed<ScriptLine[]>(() => scriptStore.getScriptPage(currentPage.value));

function viewerPreviousLine(index: number): ScriptLine | null {
  if (index > 0) return viewerLines.value[index - 1] ?? null;
  return scriptStore.getScriptPage(currentPage.value - 1).at(-1) ?? null;
}

// Phase 4 Step C (extended for presence): tell everyone else in the room which
// lines this client currently has open, and which page it's on, over the
// YJS_AWARENESS channel (ephemeral, not part of the Y.Doc itself). Called after
// every editingLines mutation, on every page navigation (see navigateTo below),
// and on any ROOM_MEMBERS change so a freshly-joined member learns the current
// state promptly rather than waiting for someone else's next open/close/navigate.
// Unconditional on role: a plain viewer's editingLines is always empty, but its
// page is still worth broadcasting so the presence popover's "Jump to" can find
// them too, not just editors.
function broadcastOpenLines(): void {
  draftStore.sendOpenLines(Array.from(editingLines.value), currentPage.value);
}

function beginEditingLine(lineUid: string): void {
  editingLines.value.add(lineUid);
  broadcastOpenLines();
  // See ScriptEditor.vue's own beginEditingLine: the hovered checkbox is
  // about to disappear, and Chrome fires neither blur nor mouseleave for a
  // removed element, so the dashed preview would otherwise linger.
  hoveredIndex.value = null;
}

function doneEditingLine(lineUid: string): void {
  editingLines.value.delete(lineUid);
  broadcastOpenLines();
}

/** Enter in the text field (Design E's keyboard flow): close this line and open a
 * fresh blank dialogue line right after it. Distinct from plain `doneEditingLine`
 * (Done/Esc), which never adds anything. */
function finishAndAddLine(index: number): void {
  const line = draftLines.value[index];
  if (!line) return;
  doneEditingLine(line._uid);
  insertLineAt(index, LINE_TYPES.DIALOGUE);
}

function navigateUp(index: number): void {
  if (index <= 0) return;
  const line = draftLines.value[index];
  const target = draftLines.value[index - 1];
  if (!line || !target) return;
  doneEditingLine(line._uid);
  beginEditingLine(target._uid);
}

function navigateDown(index: number): void {
  const line = draftLines.value[index];
  const target = draftLines.value[index + 1];
  if (!line || !target) return;
  doneEditingLine(line._uid);
  beginEditingLine(target._uid);
}

/** LineTypeSegmented changed type on a line that has never been saved — there is no
 * `line_type` mutation in the draft schema (see draftWriter.ts's `LineField` union),
 * so this deletes the line and adds a fresh blank one of the new type at the same
 * position, carrying the open-editor bookkeeping across to the new uid. Only ever
 * invoked for an unsaved line — CollabScriptLineEditor.vue disables the control
 * otherwise. */
function retypeLine(oldUid: string, index: number, newType: number): void {
  writer.deleteLine(currentPage.value, oldUid);
  const { lineUid } = writer.addLine(currentPage.value, {
    lineType: newType,
    actId: draftLines.value[index - 1]?.act_id ?? null,
    sceneId: draftLines.value[index - 1]?.scene_id ?? null,
    index,
  });
  editingLines.value.delete(oldUid);
  editingLines.value.add(lineUid);
  broadcastOpenLines();
}

function deleteLine(lineUid: string): void {
  writer.deleteLine(currentPage.value, lineUid);
  editingLines.value.delete(lineUid);
  broadcastOpenLines();
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
  broadcastOpenLines();
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
  broadcastOpenLines();
}

async function loadViewerPage(page: number): Promise<void> {
  if (page > 1) await scriptStore.loadScriptPage(page - 1);
  await scriptStore.loadScriptPage(page);
}

async function navigateTo(page: number): Promise<void> {
  if (!usesLiveRender.value) await loadViewerPage(page);
  currentPage.value = page;
  // Selection is confined to the current page (see onToggleSelect) — a line
  // checkbox ticked on a page you've since navigated away from can't stay ticked.
  clearSelection();
  // Covers every way the page can change — Prev/Next, Go to Page, and jumpToMember
  // below — in one place, rather than re-announcing it from each caller.
  broadcastOpenLines();
}

/**
 * Finds the first of `clientId`'s currently-open lines that's actually on the page
 * now loaded — an editor keeps a line open across their own page navigation, so
 * their open line can be on a different page from the one their awareness last
 * reported as "current" (that field updates on every navigateTo, their open-line
 * set does not).
 */
function findMemberLineOnCurrentPage(clientId: string | null): string | null {
  if (!clientId) return null;
  const uids = draftStore.remoteAwareness[clientId]?.openLineUids ?? [];
  if (uids.length === 0) return null;
  const pageLineUids = new Set(draftLines.value.map((l) => l._uid));
  return uids.find((uid) => pageLineUids.has(uid)) ?? null;
}

const JUMP_HIGHLIGHT_MS = 2_000;

/**
 * The presence popover's "Jump to": switch to that member's page if we're not
 * already on it, then (live render only — a REST/cut-mode viewer only has saved
 * content to show, there's no open-line editor to scroll to) scroll their open
 * line into view and flash-highlight it. A page of `null` means no awareness has
 * arrived for them yet — the popover disables Jump to in that case, but this
 * still no-ops defensively if called anyway.
 */
async function jumpToMember(entry: PresenceEntry): Promise<void> {
  if (entry.isSelf || entry.page == null) return;
  if (entry.page !== currentPage.value) {
    await navigateTo(entry.page);
  }
  if (!usesLiveRender.value) return;
  await nextTick();
  const lineUid = findMemberLineOnCurrentPage(entry.clientId);
  if (!lineUid) return;
  jumpTargetLineUid.value = lineUid;
  linesContainer.value?.$el
    .querySelector(`[data-line-uid="${lineUid}"]`)
    ?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  if (jumpHighlightTimer) clearTimeout(jumpHighlightTimer);
  jumpHighlightTimer = setTimeout(() => {
    jumpHighlightTimer = null;
    jumpTargetLineUid.value = null;
  }, JUMP_HIGHLIGHT_MS);
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

function requestCuts(): void {
  scriptConfigStore.setCutMode(true);
  if (!sendObj({ OP: 'REQUEST_SCRIPT_CUTS', DATA: {} })) {
    toast.error('Cannot cut script: not connected to the server');
    scriptConfigStore.setCutMode(false);
  }
}

// Confirms first when there are unsaved cuts, matching the classic editor's
// stopEditing() (ScriptEditor.vue) for the equivalent case — stopping without saving
// would otherwise silently discard them.
async function stopCutting(): Promise<void> {
  if (cutsChanged.value) {
    const ok = await confirm(
      'Are you sure you want to stop cutting? This will discard your unsaved cuts.'
    );
    if (!ok) return;
  }
  scriptConfigStore.setCutMode(false);
  if (!sendObj({ OP: 'STOP_SCRIPT_EDIT', DATA: {} })) {
    toast.error('Cannot stop cutting: not connected to the server');
  }
}

async function saveCuts(): Promise<void> {
  cuttingSaveInProgress.value = true;
  try {
    await scriptStore.saveCuts(linePartCuts.value);
    linePartCuts.value = [...scriptStore.cuts];
  } finally {
    cuttingSaveInProgress.value = false;
  }
}

function cutLinePart(linePartId: number): void {
  const idx = linePartCuts.value.indexOf(linePartId);
  if (idx === -1) linePartCuts.value.push(linePartId);
  else linePartCuts.value.splice(idx, 1);
}

// STOP only: the server demotes, and checkpoints if now dirty with no editors left
// (LEAVE_SCRIPT_ROOM first would remove us before STOP arrives, so the server would
// skip both) — but re-adds the caller to the room as a viewer either way, never
// sending ROOM_CLOSED itself (see stopRequested above). The isEditor watcher below
// tears down the local draft once the resulting GET_SCRIPT_CONFIG_STATUS refresh
// lands.
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
    // GET_SCRIPT_CONFIG_STATUS broadcast that reflects our already-committed
    // demotion from `editors`, which would otherwise flash the "could not open
    // the script draft" alert for that one round trip. Only set once the frame
    // actually sent — setting it unconditionally would hide that alert even
    // when nothing was sent.
    stopRequested.value = true;
  }
}

// Join if not already in the room; otherwise just ask the server to re-evaluate our
// role (editor vs viewer) from the current is_editor flag, without tearing down the
// already-synced Y.Doc — used both for the first join (any role) and for every later
// isEditor transition while we stay on the page (Phase 4 Step A).
function retryJoin(): void {
  if (draftStore.isDraftActive) {
    draftStore.refreshRoomRole();
  } else {
    draftStore.joinScriptRoom();
  }
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

function openSetCharacterDialog(): void {
  setCharDialog.value?.show();
}

function openMoveToSceneDialog(): void {
  moveToSceneModal.value?.show();
}

/** Applies a change to every line in the active selection — shared by "Set Character
 * or Group" and "Move to Scene", each building its own half of a `BulkEditPayload`
 * (the other half stays null). Selection is confined to the current page (see
 * `onToggleSelect`), so this never needs to cross pages the way the old boundary-
 * resolution comment above once did. */
function applyToSelection(payload: BulkEditPayload): void {
  const bounds = selectionBounds.value;
  if (!bounds) return;
  const character = payload.assignee
    ? {
        targetPartIndex: payload.assignee.partIndex - 1,
        characterId: payload.assignee.characterId,
        characterGroupId: payload.assignee.characterGroupId,
      }
    : null;
  // transact() is reentrant: each writer call below opens its own transaction with
  // the same LOCAL_EDIT_ORIGIN, which Yjs merges into this already-open outer one
  // rather than committing separately — so the whole change reaches peers as one update.
  writer.transact(() => {
    for (let i = bounds.startIndex; i <= bounds.endIndex; i += 1) {
      const line = draftLines.value[i];
      if (!line) continue;
      if (payload.actScene) {
        applyBulkActScene(
          currentPage.value,
          line,
          payload.actScene.actId,
          payload.actScene.sceneId
        );
      }
      if (character) {
        applyBulkCharacter(
          currentPage.value,
          line,
          character.targetPartIndex,
          character.characterId,
          character.characterGroupId
        );
      }
    }
  });
}

function onSetCharacterApply(assignee: {
  partIndex: number;
  characterId: number | null;
  characterGroupId: number | null;
}): void {
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

/** Deletes the whole selection in one transaction, by uid (captured up front, before
 * any delete) — unlike the classic editor's index-based delete, uid addressing means
 * deletion order doesn't matter here. */
function onDeleteSelection(): void {
  const bounds = selectionBounds.value;
  if (!bounds) return;
  const uids = draftLines.value.slice(bounds.startIndex, bounds.endIndex + 1).map((l) => l._uid);
  writer.transact(() => {
    for (const uid of uids) writer.deleteLine(currentPage.value, uid);
  });
  clearSelection();
}

// Covers every way cutMode can go true -> false, not just our own stopCutting()/
// saveCuts(): a server-side rejection of REQUEST_SCRIPT_CUTS (requestEditFailure()
// in scriptConfig.ts) also resets cutMode, and any line part clicked during the
// brief optimistic window before that rejection arrives must not leak into the
// next cut session.
watch(
  () => scriptConfigStore.cutMode,
  (now, was) => {
    if (!now && was) linePartCuts.value = [...scriptStore.cuts];
  }
);

function calculateNavbarHeight(): void {
  const navbar = document.querySelector('.navbar');
  navbarHeight.value = navbar ? (navbar as HTMLElement).offsetHeight : 56;
}

// Phase 4 Step A (Tim's decision): stopping editing downgrades to viewer and keeps
// watching live, rather than leaving the room and falling back to stale REST — the
// whole point of Step A is that nobody should see stale content once live viewing
// exists. The room is only actually left on unmount (see onBeforeUnmount).
watch(isEditor, (now, was) => {
  // Either direction means the editors list has caught up with whatever closed our
  // room — the grace window armed below has done its job, if it was running.
  clearRoomClosedGrace();
  if (!now && was) {
    // The server has confirmed we're no longer an editor (our own stop, or losing
    // the lock some other way) — stopRequested has done its job, if it was set.
    stopRequested.value = false;
    editingLines.value.clear();
    broadcastOpenLines();
    clearSelection();
  }
  retryJoin();
});

// Arms the grace window (see roomClosedGrace above) on every ROOM_CLOSED; the
// isEditor watch above cancels it as soon as the editors refresh actually lands.
watch(
  () => draftStore.roomClosedByServer,
  (closed) => {
    if (closed) armRoomClosedGrace();
  }
);

// Phase 4 Step C: re-announce this client's open lines whenever room membership
// changes (join, leave, role change) — awareness has no sync-on-join of its own, so
// without this a freshly-joined viewer would see nobody's open lines until each
// existing editor happens to open or close one themselves.
watch(
  () => draftStore.members,
  () => broadcastOpenLines()
);

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
    broadcastOpenLines();
  }
});

// Entering cut mode (or any other path that flips usesLiveRender false) switches the
// template to the REST viewerLines branch — but the current page may never have been
// REST-fetched if it was only ever reached via the live Y.Doc (e.g. navigating pages
// while live-viewing, not cutting). Backfill it so the page isn't blank.
watch(usesLiveRender, (isLive, wasLive) => {
  if (wasLive && !isLive) void loadViewerPage(currentPage.value);
});

// A plain viewer's room can close with no action of their own (e.g. an editor
// discarding the draft closes it for everyone) — unlike an editor's own failed
// join, there's no Retry alert for a viewer (joinFailed is scoped to isEditor),
// so without this a viewer would be stuck on a REST render that may itself be
// stale/blank for the rest of the visit, even once someone else resumes
// editing and a new room exists to rejoin. Backs off (capped) rather than
// retrying forever if nothing ever picks editing back up.
//
// Gated on roomClosedByServer, not just status reaching 'idle': a *rejected*
// join (blocked edit, missing revision, a live session, a bad Y.Doc) also
// ends at 'idle', but collabError() already toasts and tears down for that —
// reacting here too would pile on repeated duplicate toasts over the whole
// backoff schedule for a join that was never going to succeed differently on
// a retry. Also skipped during a live session, same as the mount join above:
// retrying mid-show would reproduce the exact toast noise that fix removed.
watch(
  () => draftStore.status,
  (status) => {
    if (status === 'synced') {
      viewerRecoveryAttempt = 0;
      return;
    }
    if (status !== 'idle' || isEditor.value || stopRequested.value) return;
    if (!draftStore.roomClosedByServer) return;
    clearViewerRecoveryTimer();
    void loadViewerPage(currentPage.value);
    if (viewerRecoveryAttempt >= VIEWER_RECOVERY_DELAYS_MS.length) return;
    const delay = VIEWER_RECOVERY_DELAYS_MS[viewerRecoveryAttempt]!;
    viewerRecoveryAttempt += 1;
    viewerRecoveryTimer = setTimeout(() => {
      viewerRecoveryTimer = null;
      if (!isEditor.value && !systemStore.currentShow?.current_session_id) retryJoin();
    }, delay);
  }
);

watch(canEditDraft, () => setupAutoSave());
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

  const storedPage = Number.parseInt(localStorage.getItem('scriptEditPage') ?? '1', 10);
  currentPage.value = Number.isInteger(storedPage) && storedPage > 0 ? storedPage : 1;
  await loadViewerPage(currentPage.value);

  loaded.value = true;
  // Join unconditionally (Phase 4 Step A) — the server decides editor vs viewer role
  // from is_editor, so this is how a plain viewer gets live content too, not just an
  // editor. Covers both a brief reconnect and a full page reload for an editor
  // specifically: the server holds is_editor through a short reconnect grace window
  // (issue #1419, fixed by #1427 — REFRESH_CLIENT resumes the session row, confirmed
  // once AUTHENTICATE succeeds), so isEditor is already true here by the time this
  // component re-mounts, and retryJoin() rejoins as editor directly.
  //
  // Skipped entirely during a live session: _op_join_script_room rejects every join
  // (viewer or editor) while one is active, and nobody can be an editor then anyway
  // — joining would only earn every plain viewer who opens this tab an error toast
  // for a join nobody asked for and that could never have succeeded.
  if (!systemStore.currentShow?.current_session_id) retryJoin();
  setupAutoSave();
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', calculateNavbarHeight);
  clearViewerRecoveryTimer();
  clearRoomClosedGrace();
  if (jumpHighlightTimer) clearTimeout(jumpHighlightTimer);
  // Leaving the tab leaves the room (the editor flag is kept, so coming back rejoins).
  if (draftStore.isDraftActive) draftStore.leaveScriptRoom();
});
</script>

<style scoped>
.script-editor-container {
  position: relative;
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
  /* box-shadow, not border-top: see .sticky-header's own comment on why a
     border on a sticky element paints over a popover that should sit above
     it in Chromium. --bs-border-color (what the old border-top used) also
     resolves to Bootstrap's light default on this theme — --bs-gray-700
     instead, same reasoning as ScriptLineEditor.vue's --bs-dark note. */
  box-shadow: 0 -1px 0 0 var(--bs-gray-700);
}
.sticky-header {
  position: sticky;
  z-index: 100;
  padding: 10px 0;
  /* A `box-shadow`, not `border-bottom`: a border on a `position: sticky` element
     paints in a way that ignores a descendant's z-index in Chromium (confirmed via
     `document.elementsFromPoint()` reporting the descendant on top while the
     border still visibly painted over it) — the presence popover below opens
     right over this line, so it has to actually be behind it. A `box-shadow`
     draws the same 1px line without that quirk. */
  box-shadow: 0 1px 0 0 #dee2e6;
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
/* The presence popover — avatar-stack toggle button + "Here now" member list. */
.presence-stack {
  display: inline-flex;
  margin-right: 8px;
}
.presence-stack > * + * {
  margin-left: -8px;
}
/* Matches the design's own dark popover chrome exactly (#303030/#444), not
   Bootstrap's light-theme dropdown-menu defaults (var(--bs-border-color) etc,
   which read as a near-white line against this dark background — that's what
   looked like a stray "white line" cutting through the popover). */
.presence-popover-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid #444;
}
.presence-popover-header .presence-people-count {
  color: #adb5bd;
  font-size: 13px;
}
/* The actual row layout. Deliberately NOT a class on BDropdownForm/BDropdownItem
   themselves — both apply a slotted `class` to their own outer <li>, not the
   inner element the slot content renders into (see the template comment above),
   so this has to be an element inside the slot instead. */
.presence-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  min-height: 56px;
  text-align: left;
}
.presence-row-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.presence-row-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
}
.presence-row-sub {
  color: #adb5bd;
  font-size: 13px;
  line-height: 19px;
}
/* The right-hand column: role pill, and (for anyone but self) "Jump to" below it —
   matches the design's two-column row rather than crowding everything onto the
   left under the name. */
.presence-row-side {
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}
.presence-you-pill,
.presence-role-pill {
  font-size: 12px;
}
.presence-jump {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #54b98f;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}
</style>

<style>
/* Unscoped: BDropdown's own toggle button and menu render outside this
   component's template, so a scoped selector on the toggle button's own class
   (passed via toggle-class/menu-class) would never match it. */
.presence-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.presence-menu {
  width: 380px;
  padding: 0;
  background: #303030;
  border: 1px solid #444;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  /* Without `!important` this loses to Bootstrap's own `.dropdown-menu.show` rule
     (two classes vs. this one) regardless of source order. */
  z-index: 1060 !important;
}
.presence-menu .dropdown-item-text,
.presence-menu .dropdown-item {
  padding: 8px 16px;
  color: #fff;
}
.presence-menu .dropdown-item:hover,
.presence-menu .dropdown-item:focus {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}
</style>
