<template>
  <BContainer class="mx-0 px-0" fluid>
    <div v-if="loadError" class="cue-load-error" role="alert">
      <p>The cues could not be loaded. Check the connection and try again.</p>
      <button type="button" class="btn btn-outline-light" @click="loadEverything">Try Again</button>
    </div>

    <div v-else-if="!loaded" class="text-center py-5"><BSpinner /></div>

    <CueEmptyState
      v-else-if="showStore.cueTypes.length === 0"
      :can-edit-show="systemStore.isShowEditor"
      @new-type="(suggestion) => emit('new-type', suggestion)"
      @import="emit('import')"
    />

    <template v-else>
      <CueToolbar
        v-model:filter-type-id="filterTypeId"
        :current-page="currentEditPage"
        :max-page="currentMaxPage"
        :busy="changingPage"
        :cue-types="showStore.cueTypes"
        @go-to-page="requestGoToPage"
        @prev="decrPage"
        @next="incrPage"
        @jump="onJump"
      />

      <div v-if="isLiveSession" class="cue-banner" role="status">
        A show is running. You can add cues, but editing and deleting cues is paused until the
        session ends.
      </div>
      <div v-if="!canAddCues" class="cue-banner" role="status">
        View only. You can look at cues but you do not have permission to change them.
      </div>
      <div v-if="notice" class="cue-banner" role="status">{{ notice }}</div>

      <BRow class="script-row cue-colhead">
        <BCol cols="3">Cues</BCol>
        <BCol>Script</BCol>
      </BRow>
      <hr />
      <BRow class="script-row">
        <BCol cols="12">
          <template
            v-for="(line, index) in scriptStore.getScriptPage(currentEditPage)"
            :key="`page_${currentEditPage}_line_${line.id ?? index}`"
          >
            <ScriptLineCueEditor
              :line="line"
              :line-index="index"
              :previous-line="scriptStore.getScriptPage(currentEditPage)[index - 1] ?? null"
              :acts="showStore.actList"
              :scenes="showStore.sceneList"
              :characters="showStore.characterList"
              :character-groups="showStore.characterGroupList"
              :cues="scriptStore.cuesForLine(line.id)"
              :cue-types="showStore.cueTypes"
              :cuts="scriptStore.cuts"
              :active-card="activeCard"
              :filter-type-id="filterTypeId"
              :highlight-line-id="jumpLineId"
              @open="onOpen"
              @close-card="closeCard()"
              @cancel-card="onCancelCard"
              @added="onAdded"
              @dirty="(value) => (groupDirty = value)"
              @target-gone="onTargetGone"
            />
          </template>
        </BCol>
      </BRow>
    </template>

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
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeMount, onBeforeUnmount, ref, watch } from 'vue';
import log from 'loglevel';
import type { BModal } from 'bootstrap-vue-next';
import CueEmptyState from '@/components/show/config/cues/CueEmptyState.vue';
import CueToolbar from '@/components/show/config/cues/CueToolbar.vue';
import ScriptLineCueEditor from '@/components/show/config/cues/ScriptLineCueEditor.vue';
import { useConfirm } from '@/composables/useConfirm';
import { useCueDisplay } from '@/composables/useCueDisplay';
import { useCuePermissions } from '@/composables/useCuePermissions';
import type { SuggestedCueType } from '@/constants/cueTypeSuggestions';
import type { FindMatch } from '@/js/cueFind';
import { toast } from '@/js/toast';
import { useScriptStore } from '@/stores/script';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import { useUserStore } from '@/stores/user';
import type { ActiveCueCard } from '@/types/cueCard';

const emit = defineEmits<{
  /** Empty state: open the new cue type form, pre-filled when a suggestion was chosen. */
  'new-type': [suggestion: SuggestedCueType | null];
  /** Empty state: open the import-from-another-show form. */
  import: [];
}>();

const scriptStore = useScriptStore();
const showStore = useShowStore();
const systemStore = useSystemStore();
const userStore = useUserStore();
const { confirm } = useConfirm();
const { cueLabel, cueGroupLabel } = useCueDisplay();
const { isLiveSession, canAddCues } = useCuePermissions();

const loaded = ref(false);
const currentEditPage = ref(1);
const currentMaxPage = ref(1);
const changingPage = ref(false);
const pageInputNo = ref(1);
const goToPageModal = ref<InstanceType<typeof BModal> | null>(null);

// ── Type filter ─────────────────────────────────────────────────────────────

function storedFilter(): number | null {
  try {
    const raw = Number(localStorage.getItem('cueEditFilter'));
    return raw || null;
  } catch {
    return null;
  }
}
const filterChoice = ref<number | null>(storedFilter());

/** A remembered type that no longer exists is the same as "All". */
const filterTypeId = computed<number | null>({
  get: () =>
    filterChoice.value != null && showStore.cueTypes.some((t) => t.id === filterChoice.value)
      ? filterChoice.value
      : null,
  set: (value) => {
    filterChoice.value = value;
  },
});

watch(filterChoice, (value) => {
  try {
    localStorage.setItem('cueEditFilter', value == null ? '' : String(value));
  } catch {
    // Storage can be unavailable; remembering the filter is only a convenience.
  }
});

watch(currentEditPage, (val) => {
  try {
    localStorage.setItem('cueEditPage', String(val));
  } catch {
    // As above.
  }
});

// ── Loading ─────────────────────────────────────────────────────────────────

function readStoredPage(): string | null {
  try {
    return localStorage.getItem('cueEditPage');
  } catch {
    return null;
  }
}

const loadError = ref(false);

/** Keep a page number inside the script (a remembered or typed page can be past its end now). */
function clampPage(pageNo: number): number {
  const last = Math.max(1, currentMaxPage.value);
  return Math.min(Math.max(1, Math.trunc(pageNo) || 1), last);
}

async function loadEverything(): Promise<void> {
  loadError.value = false;
  let cuesLoaded = true;
  let maxPageLoaded = true;
  try {
    await Promise.all([
      userStore.getCurrentUser().then(() => {
        if (userStore.currentUser != null) {
          return Promise.all([
            userStore.getStageDirectionStyleOverrides(),
            userStore.getCueColourOverrides(),
          ]);
        }
      }),
      showStore.getActList(),
      showStore.getSceneList(),
      showStore.getCharacterList(),
      showStore.getCharacterGroupList(),
      showStore.getCueTypes(),
      showStore.getShowSessionData(),
      scriptStore.loadCues().then((ok) => {
        cuesLoaded = ok;
      }),
      scriptStore.getCuts(),
      scriptStore.getStageDirectionStyles(),
      scriptStore.getMaxPage().then((ok) => {
        maxPageLoaded = ok;
        currentMaxPage.value = scriptStore.maxPage;
      }),
    ]);
    // Showing "no cues" for cues that simply did not arrive would be a lie.
    if (!cuesLoaded || !maxPageLoaded) throw new Error('cues or page count not loaded');

    const storedPage = readStoredPage();
    currentEditPage.value = clampPage(storedPage == null ? 1 : Number.parseInt(storedPage, 10));
    if (!(await goToPageInner(currentEditPage.value))) throw new Error('script page not loaded');
    loaded.value = true;
  } catch (error) {
    log.error('Unable to load the cue editor', error);
    loadError.value = true;
  }
}

onBeforeMount(loadEverything);

/** Load a page and the one before and after it. Only the page itself decides the result. */
async function goToPageInner(pageNo: number): Promise<boolean> {
  if (pageNo > 1) await scriptStore.loadScriptPage(pageNo - 1);
  if (!(await scriptStore.loadScriptPage(pageNo))) return false;
  currentEditPage.value = pageNo;
  await scriptStore.loadScriptPage(pageNo + 1);
  return true;
}

// ── The open card ───────────────────────────────────────────────────────────

const activeCard = ref<ActiveCueCard | null>(null);
const groupDirty = ref(false);
const notice = ref('');
const jumpLineId = ref<number | null>(null);
let openerElement: HTMLElement | null = null;
let openerLineId: number | null = null;
let activeLabel = '';

function sameCard(a: ActiveCueCard | null, b: ActiveCueCard): boolean {
  return (
    a != null &&
    a.lineId === b.lineId &&
    a.kind === b.kind &&
    a.cueId === b.cueId &&
    a.groupId === b.groupId
  );
}

/**
 * Ask before throwing away unsaved group changes. Only group cards report them
 * (`groupDirty`); a single cue has little to lose, so its card closes without asking.
 */
async function confirmDiscard(): Promise<boolean> {
  if (!groupDirty.value) return true;
  return confirm('Discard your changes to this group?', {
    title: 'Discard Changes',
    okVariant: 'danger',
    okTitle: 'Discard Changes',
    cancelTitle: 'Keep Editing',
  });
}

function labelFor(card: ActiveCueCard): string {
  // A group first: a view-only group also carries one of its cues.
  if (card.groupId != null) {
    const entry = scriptStore
      .groupedCuesForLine(card.lineId)
      .groups.find((g) => g.group.id === card.groupId);
    return entry ? cueGroupLabel(entry.group, entry.cues) : 'The group';
  }
  if (card.cueId != null) {
    const cue = scriptStore.cuesForLine(card.lineId).find((c) => c.id === card.cueId);
    return cue ? cueLabel(cue) : 'The cue';
  }
  return '';
}

function closeCard(refocus = true): void {
  const opener = openerElement;
  const lineId = openerLineId;
  activeCard.value = null;
  groupDirty.value = false;
  openerElement = null;
  openerLineId = null;
  if (!refocus) return;
  // Hand focus back to the control that opened the card (or the line's "+ Cue" if it is gone).
  void nextTick(() => {
    const target =
      opener?.isConnected && !(opener as HTMLButtonElement).disabled
        ? opener
        : document.querySelector<HTMLElement>(
            `[data-line-id="${lineId}"] .add-cue-btn:not(:disabled)`
          );
    target?.focus();
  });
}

async function onOpen(card: ActiveCueCard, opener: HTMLElement | null): Promise<void> {
  if (sameCard(activeCard.value, card)) {
    closeCard();
    return;
  }
  if (!(await confirmDiscard())) return;
  notice.value = '';
  activeLabel = labelFor(card);
  activeCard.value = card;
  groupDirty.value = false;
  openerElement = opener;
  openerLineId = card.lineId;
}

async function onCancelCard(): Promise<void> {
  if (await confirmDiscard()) closeCard();
}

function onAdded(typeId: number): void {
  // Someone who adds a cue of a hidden type needs to see it.
  if (filterTypeId.value != null && filterTypeId.value !== typeId) filterTypeId.value = null;
}

function onTargetGone(): void {
  const label = activeLabel || 'The item you were editing';
  closeCard(false);
  notice.value = `${label} was changed or removed by someone else, so the card was closed.`;
}

/**
 * If someone else edits the line the card is on, it gets a new id and the page reloads without
 * it, so the card would vanish with nothing said (and a dirty group would be remembered).
 * Close it and tell the person instead.
 */
watch(
  () => scriptStore.getScriptPage(currentEditPage.value),
  (lines) => {
    const card = activeCard.value;
    if (!card || lines.length === 0) return;
    if (lines.some((l) => l.id === card.lineId)) return;
    closeCard(false);
    notice.value =
      'The line you were working on was changed or removed by someone else, so the card was closed.';
  }
);

// ── Pages ───────────────────────────────────────────────────────────────────

/** Changing page closes the card without asking, unless a group has unsaved changes. */
async function leaveCard(): Promise<boolean> {
  if (!(await confirmDiscard())) return false;
  closeCard(false);
  return true;
}

async function requestGoToPage(): Promise<void> {
  if (!(await leaveCard())) return;
  goToPageModal.value?.show();
}

async function goToPage(): Promise<void> {
  if (!pageInputNo.value || pageInputNo.value < 1) return;
  const target = clampPage(pageInputNo.value);
  pageInputNo.value = target;
  changingPage.value = true;
  try {
    if (!(await goToPageInner(target))) {
      toast.error(`Could not load page ${target}.`);
      return;
    }
    goToPageModal.value?.hide();
  } finally {
    changingPage.value = false;
  }
}

/** Step to a neighbouring page, staying where we are if it cannot be loaded. */
async function stepPage(by: -1 | 1): Promise<void> {
  const target = currentEditPage.value + by;
  if (target < 1 || target > currentMaxPage.value || !(await leaveCard())) return;
  changingPage.value = true;
  try {
    const loadedAlready = scriptStore.getScriptPage(target).length > 0;
    if (!loadedAlready && !(await scriptStore.loadScriptPage(target))) {
      toast.error(`Could not load page ${target}.`);
      return;
    }
    currentEditPage.value = target;
    const ahead = target + by;
    if (ahead >= 1) await scriptStore.loadScriptPage(ahead);
  } finally {
    changingPage.value = false;
  }
}

const decrPage = () => stepPage(-1);
const incrPage = () => stepPage(1);

// ── Find ────────────────────────────────────────────────────────────────────

async function onJump(match: FindMatch): Promise<void> {
  const page = match.location.page;
  if (page == null) {
    toast.error('That cue is not on a page that can be shown.');
    return;
  }
  if (!(await leaveCard())) return;
  // A hidden type would hide the cue we are jumping to.
  if (filterTypeId.value != null && filterTypeId.value !== match.cue_type.id)
    filterTypeId.value = null;
  changingPage.value = true;
  try {
    if (!(await goToPageInner(page))) {
      toast.error(`Could not load page ${page}.`);
      return;
    }
  } finally {
    changingPage.value = false;
  }
  jumpLineId.value = match.location.line_id;
  await nextTick();
  document
    .querySelector(`[data-line-id="${match.location.line_id}"]`)
    ?.scrollIntoView?.({ block: 'center' });
  toast.success(`Jumped to ${match.cue_type.prefix} ${match.cue.ident} on page ${page}`);
  if (jumpTimer != null) clearTimeout(jumpTimer);
  jumpTimer = setTimeout(() => {
    jumpTimer = null;
    jumpLineId.value = null;
  }, 2000);
}

let jumpTimer: ReturnType<typeof setTimeout> | null = null;
onBeforeUnmount(() => {
  if (jumpTimer != null) clearTimeout(jumpTimer);
});
</script>

<style scoped>
.cue-banner {
  margin-top: 10px;
  padding: 10px 14px;
  border: 1px solid var(--bs-warning);
  border-radius: 0.25rem;
  color: var(--bs-warning);
  font-size: 0.875rem;
  font-weight: 700;
}

.cue-load-error {
  max-width: 560px;
  margin: 32px auto;
  padding: 20px;
  border: 2px solid var(--bs-danger);
  border-radius: 0.25rem;
  text-align: center;
}

.cue-colhead {
  margin-top: 12px;
  text-align: center;
  font-size: 1rem;
}
</style>
