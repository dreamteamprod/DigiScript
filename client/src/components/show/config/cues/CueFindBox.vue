<template>
  <div ref="root" class="cue-find" @keydown.esc="dismiss">
    <label :for="`${uid}-input`" class="visually-hidden">Find a cue</label>
    <input
      :id="`${uid}-input`"
      v-model="text"
      class="form-control cue-find-input"
      type="search"
      role="combobox"
      placeholder="Find a cue, e.g. LX 12"
      autocomplete="off"
      aria-haspopup="listbox"
      :aria-expanded="panelOpen"
      :aria-controls="`${uid}-panel`"
      :aria-activedescendant="activeOption != null ? `${uid}-opt-${activeOption}` : undefined"
      @keydown.enter.prevent="onEnter"
      @keydown.down.prevent="moveActive(1)"
      @keydown.up.prevent="moveActive(-1)"
      @input="onInput"
    />
    <button type="button" class="btn btn-outline-light" :disabled="searching" @click="run()">
      Find
    </button>

    <div
      v-if="panelOpen"
      :id="`${uid}-panel`"
      class="find-panel"
      :aria-live="state === 'results' ? undefined : 'polite'"
    >
      <div v-if="state === 'searching'" class="find-message">Searching…</div>

      <div v-else-if="state === 'error'" class="find-message">
        <div class="find-error" role="alert">Search failed. Please try again.</div>
        <button type="button" class="btn btn-outline-light mt-2" @click="run()">Try Again</button>
      </div>

      <div v-else-if="state === 'needs-type'" class="find-message">
        <div>Which cue type is {{ pendingNumber }}?</div>
        <div class="find-types">
          <button
            v-for="type in showStore.cueTypes"
            :key="type.id"
            type="button"
            class="find-type-chip"
            @click="searchWithType(type.id)"
          >
            <span class="swatch" :style="{ background: typeColour(type.id) }" aria-hidden="true" />
            <b>{{ type.prefix }}</b>
          </button>
        </div>
      </div>

      <div v-else-if="state === 'needs-number'" class="find-message">
        Add the number you are looking for, for example {{ examplePrefix }} 12.
      </div>

      <div v-else-if="state === 'none'" class="find-message">
        No cues found matching “{{ lastQuery }}”.
      </div>

      <template v-else-if="state === 'results'">
        <div class="find-heading" :class="{ 'find-heading-warn': heading.warn }">
          {{ heading.text }}
        </div>
        <div role="listbox" :aria-label="heading.text">
          <button
            v-for="(match, index) in results"
            :id="`${uid}-opt-${index}`"
            :key="`${match.cue.id}`"
            type="button"
            role="option"
            class="find-row"
            :class="{ 'find-row-active': index === activeOption }"
            :aria-selected="index === activeOption"
            tabindex="-1"
            @click="pick(match)"
            @mousemove="activeOption = index"
          >
            <span class="cue-chip" :style="chipStyle(match)">
              {{ match.cue_type.prefix }} {{ match.cue.ident }}
            </span>
            <span>
              <b class="find-where">{{ whereText(match) }}</b>
              <span class="find-preview">{{ previewText(match) }}</span>
            </span>
          </button>
        </div>
        <div class="find-hint">
          <kbd>↑</kbd> <kbd>↓</kbd> choose &nbsp;·&nbsp; <kbd>Enter</kbd> go to that line
          &nbsp;·&nbsp; <kbd>Esc</kbd> close
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useId } from 'vue';
import log from 'loglevel';
import { useCueDisplay } from '@/composables/useCueDisplay';
import {
  mergeFindResponses,
  parseFindQuery,
  type FindMatch,
  type FindResponse,
} from '@/js/cueFind';
import { useScriptStore } from '@/stores/script';
import { useShowStore } from '@/stores/show';
import type { CueType } from '@/types/api/cues';

const emit = defineEmits<{
  /** A cue was chosen (or was the only match): open its page and mark its line. */
  jump: [match: FindMatch];
}>();

const uid = useId();
const scriptStore = useScriptStore();
const showStore = useShowStore();
const { typeColour, contrastColor } = useCueDisplay();

type State = 'idle' | 'searching' | 'results' | 'none' | 'error' | 'needs-type' | 'needs-number';

const root = ref<HTMLElement | null>(null);
const text = ref('');
const state = ref<State>('idle');
const results = ref<FindMatch[]>([]);
const heading = ref({ text: '', warn: false });
const activeOption = ref<number | null>(null);
const pendingNumber = ref('');
const lastQuery = ref('');
const forcedTypes = ref<CueType[] | null>(null);
/** The text the current results were found for, so results for older text are not trusted. */
const resultsText = ref('');

/** Pause after the last keystroke before searching as you type. */
const DEBOUNCE_MS = 300;
let debounceTimer: ReturnType<typeof setTimeout> | null = null;
/** Incremented for every search and every edit, so an answer to an older one is ignored. */
let requestId = 0;

const searching = computed(() => state.value === 'searching');
const panelOpen = computed(() => state.value !== 'idle');
const examplePrefix = computed(() => showStore.cueTypes[0]?.prefix ?? 'LX');

function closePanel(): void {
  state.value = 'idle';
  activeOption.value = null;
}

/** Esc: close the list and drop any search that is waiting or on its way. */
function dismiss(): void {
  cancelPending();
  closePanel();
}

function cancelPending(): void {
  if (debounceTimer != null) {
    clearTimeout(debounceTimer);
    debounceTimer = null;
  }
  requestId += 1;
}

/**
 * Search as you type, after a short pause. These searches only fill the list: a single exact
 * match does not jump (typing "LX 13" passes through "LX 1"), so nothing moves until Enter,
 * Find or a click. A bare number or prefix is not searched until asked for.
 */
function onInput(): void {
  forcedTypes.value = null;
  cancelPending();
  const query = parseFindQuery(text.value, showStore.cueTypes);
  if (query.kind !== 'search') {
    closePanel();
    return;
  }
  debounceTimer = setTimeout(() => {
    debounceTimer = null;
    void run(undefined, true);
  }, DEBOUNCE_MS);
}

function onEnter(): void {
  // Results shown for text that has since changed must not be opened by mistake.
  const fresh = resultsText.value === text.value.trim();
  if (state.value === 'results' && activeOption.value != null && fresh) {
    pick(results.value[activeOption.value]);
    return;
  }
  cancelPending();
  void run();
}

function moveActive(by: 1 | -1): void {
  if (state.value !== 'results' || results.value.length === 0) return;
  const count = results.value.length;
  activeOption.value =
    activeOption.value == null
      ? by === 1
        ? 0
        : count - 1
      : (activeOption.value + by + count) % count;
}

function searchWithType(typeId: number): void {
  const type = showStore.cueTypes.find((t) => t.id === typeId);
  if (!type) return;
  forcedTypes.value = [type];
  void run(pendingNumber.value);
}

async function run(numberOverride?: string, typing = false): Promise<void> {
  const query = numberOverride != null ? null : parseFindQuery(text.value, showStore.cueTypes);
  let types: CueType[];
  let number: string;
  if (numberOverride != null && forcedTypes.value) {
    types = forcedTypes.value;
    number = numberOverride;
  } else if (query?.kind === 'search') {
    types = query.types;
    number = query.number;
  } else if (query?.kind === 'needs-type') {
    pendingNumber.value = query.number;
    state.value = 'needs-type';
    return;
  } else if (query?.kind === 'needs-number') {
    state.value = 'needs-number';
    return;
  } else {
    return;
  }

  lastQuery.value = forcedTypes.value
    ? `${forcedTypes.value[0].prefix} ${number}`
    : text.value.trim();
  requestId += 1;
  const myRequest = requestId;
  const searchedText = text.value.trim();
  // While typing, the previous results stay up until the new ones replace them.
  if (!typing) state.value = 'searching';
  let response: FindResponse;
  try {
    const responses = await Promise.all(
      types.map(
        (t) => scriptStore.searchCues({ identifier: number, cueTypeId: t.id }) as Promise<unknown>
      )
    );
    response = mergeFindResponses(responses as FindResponse[]);
  } catch (err) {
    log.error('Cue search failed', err);
    if (myRequest === requestId) state.value = 'error';
    return;
  }
  // Something newer (more typing, or another search) has taken over.
  if (myRequest !== requestId) return;

  if (response.exact_matches.length === 1 && !typing) {
    closePanel();
    emit('jump', response.exact_matches[0]);
    return;
  }
  const shown = response.exact_matches.length > 0 ? response.exact_matches : response.suggestions;
  if (shown.length === 0) {
    state.value = 'none';
    return;
  }
  resultsText.value = searchedText;
  if (response.exact_matches.length > 0) {
    const count = response.exact_matches.length;
    heading.value = {
      text:
        count === 1
          ? `1 cue is numbered ${lastQuery.value}`
          : `${count} cues are numbered ${lastQuery.value}`,
      warn: false,
    };
  } else {
    heading.value = { text: `No ${lastQuery.value} yet. Did you mean:`, warn: true };
  }
  results.value = shown;
  activeOption.value = 0;
  state.value = 'results';
  await loadPreviews(shown);
}

/** Pages are loaded so each result can show the start of its line. */
async function loadPreviews(matches: readonly FindMatch[]): Promise<void> {
  const pages = new Set(matches.map((m) => m.location.page).filter((p): p is number => p != null));
  await Promise.all(
    [...pages]
      .filter((p) => scriptStore.getScriptPage(p).length === 0)
      .map((p) => scriptStore.loadScriptPage(p))
  );
}

function pick(match: FindMatch): void {
  closePanel();
  emit('jump', match);
}

// ── Display ─────────────────────────────────────────────────────────────────

function chipStyle(match: FindMatch): Record<string, string> {
  const background = typeColour(match.cue_type.id);
  return { backgroundColor: background, color: contrastColor(background) };
}

function whereText(match: FindMatch): string {
  const act = showStore.actList.find((a) => a.id === match.location.act_id)?.name;
  const scene = showStore.sceneList.find((s) => s.id === match.location.scene_id)?.name;
  const place = [act, scene].filter(Boolean).join(' ');
  const page = match.location.page != null ? `Page ${match.location.page}` : 'Page unknown';
  return place ? `${page} · ${place}` : page;
}

function previewText(match: FindMatch): string {
  const page = match.location.page;
  if (page == null) return '';
  const line = scriptStore.getScriptPage(page).find((l) => l.id === match.location.line_id);
  const body =
    line?.line_parts
      .map((p) => p.line_text ?? '')
      .join(' ')
      .trim() ?? '';
  return body.length > 60 ? `${body.slice(0, 60).trimEnd()}…` : body;
}

// Close when focus or a click moves outside the box.
function onDocumentPointer(event: Event): void {
  // Also drops a search that is waiting or on its way, so it cannot reopen the list.
  if (root.value && !root.value.contains(event.target as Node)) dismiss();
}
onMounted(() => document.addEventListener('pointerdown', onDocumentPointer));
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocumentPointer);
  cancelPending();
});

defineExpose({
  /** Put the cursor in the box. */
  focus(): void {
    root.value?.querySelector<HTMLInputElement>('input')?.focus();
  },
});
</script>

<style scoped>
.cue-find {
  position: relative;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.cue-find-input {
  width: 230px;
}

.find-panel {
  position: absolute;
  z-index: 200;
  top: 44px;
  right: 0;
  width: 460px;
  max-width: 90vw;
  background: var(--bs-gray-800);
  border: 1px solid var(--bs-gray-700);
  border-radius: 0.25rem;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
  text-align: left;
}

.find-message {
  padding: 12px;
}

.find-error {
  padding: 10px 14px;
  border: 2px solid var(--bs-danger);
  border-radius: 0.25rem;
  color: #fff;
  font-weight: 700;
  font-size: 0.875rem;
}

.find-heading {
  padding: 10px 12px;
  font-weight: 700;
}

.find-heading-warn {
  color: var(--bs-warning);
}

.find-row {
  display: grid;
  grid-template-columns: 80px 1fr;
  gap: 12px;
  align-items: center;
  width: 100%;
  min-height: 44px;
  padding: 9px 12px;
  background: transparent;
  border: 0;
  border-top: 1px solid var(--bs-gray-700);
  color: #fff;
  text-align: left;
}

.find-row-active,
.find-row:focus-visible {
  background: rgba(255, 255, 255, 0.1);
}

.find-where {
  display: block;
  font-size: 0.875rem;
}

.find-preview {
  display: block;
  color: var(--bs-gray-500);
  font-size: 0.8125rem;
}

.find-hint {
  padding: 8px 12px;
  border-top: 1px solid var(--bs-gray-700);
  color: var(--bs-gray-500);
  font-size: 0.8125rem;
}

kbd {
  padding: 1px 6px;
  border: 1px solid var(--bs-gray-600);
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.05);
  color: var(--bs-gray-200);
  font-family: inherit;
  font-size: 0.75rem;
}

.find-types {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.find-type-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 36px;
  padding: 0 12px;
  border: 2px solid var(--bs-gray-600);
  border-radius: 0.25rem;
  background: transparent;
  color: #fff;
}

.swatch {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 3px;
}

.cue-chip {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 10px;
  border-radius: 0.25rem;
  font-weight: 700;
  font-size: 0.875rem;
  white-space: nowrap;
}
</style>
