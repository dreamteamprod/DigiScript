<template>
  <BContainer class="mx-0 px-0" fluid>
    <div v-if="!loaded" class="text-center py-5"><BSpinner /></div>

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
            :key="`page_${currentEditPage}_line_${index}`"
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
import { computed, nextTick, onBeforeMount, ref, watch } from 'vue';
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

onBeforeMount(async () => {
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
    scriptStore.loadCues(),
    scriptStore.getCuts(),
    scriptStore.getStageDirectionStyles(),
    scriptStore.getMaxPage().then(() => {
      currentMaxPage.value = scriptStore.maxPage;
    }),
  ]);

  const storedPage = readStoredPage();
  if (storedPage != null) {
    currentEditPage.value = Number.parseInt(storedPage, 10) || 1;
  }
  await goToPageInner(currentEditPage.value);
  loaded.value = true;
});

async function goToPageInner(pageNo: number): Promise<void> {
  if (pageNo > 1) {
    await scriptStore.loadScriptPage(pageNo - 1);
  }
  await scriptStore.loadScriptPage(pageNo);
  currentEditPage.value = pageNo;
  await scriptStore.loadScriptPage(pageNo + 1);
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

/** A card with unsaved group changes is the only thing worth asking about. */
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
  if (card.cueId != null) {
    const cue = scriptStore.cuesForLine(card.lineId).find((c) => c.id === card.cueId);
    return cue ? cueLabel(cue) : 'The cue';
  }
  if (card.groupId != null) {
    const entry = scriptStore
      .groupedCuesForLine(card.lineId)
      .groups.find((g) => g.group.id === card.groupId);
    return entry ? cueGroupLabel(entry.group, entry.cues) : 'The group';
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
  changingPage.value = true;
  await goToPageInner(pageInputNo.value);
  changingPage.value = false;
  goToPageModal.value?.hide();
}

async function decrPage(): Promise<void> {
  if (currentEditPage.value <= 1 || !(await leaveCard())) return;
  changingPage.value = true;
  const targetPage = currentEditPage.value - 1;
  await scriptStore.loadScriptPage(targetPage);
  currentEditPage.value--;
  await scriptStore.loadScriptPage(currentEditPage.value - 1);
  changingPage.value = false;
}

async function incrPage(): Promise<void> {
  if (currentEditPage.value >= currentMaxPage.value || !(await leaveCard())) return;
  changingPage.value = true;
  currentEditPage.value++;
  await scriptStore.loadScriptPage(currentEditPage.value + 1);
  changingPage.value = false;
}

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
  await goToPageInner(page);
  changingPage.value = false;
  jumpLineId.value = match.location.line_id;
  await nextTick();
  document
    .querySelector(`[data-line-id="${match.location.line_id}"]`)
    ?.scrollIntoView?.({ block: 'center' });
  toast.success(`Jumped to ${match.cue_type.prefix} ${match.cue.ident} on page ${page}`);
  setTimeout(() => {
    if (jumpLineId.value === match.location.line_id) jumpLineId.value = null;
  }, 2000);
}
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

.cue-colhead {
  margin-top: 12px;
  text-align: center;
  font-size: 1rem;
}
</style>
