<template>
  <section
    v-if="mode === 'view'"
    class="cue-note"
    role="note"
    :aria-label="`${viewLabel} is view only`"
  >
    <b>{{ viewLabel }} · {{ viewTypeDescription }}</b>
    <div class="cue-note-caption">
      View only. You do not have permission to change {{ viewPrefix }} cues.
    </div>
  </section>

  <section
    v-else
    class="cue-card"
    :aria-label="mode === 'add' ? 'Add a cue to this line' : `Edit ${editLabel}`"
    @keydown.esc.stop.prevent="emit('cancel')"
  >
    <div class="cue-card-head">
      <b>{{ mode === 'add' ? 'Add a cue to this line' : `Edit ${editLabel}` }}</b>
      <span class="flex-fill" />
      <fieldset v-if="mode === 'add'" class="btn-group" aria-label="What to add">
        <button type="button" class="btn btn-sm btn-primary" aria-pressed="true">Single Cue</button>
        <button
          type="button"
          class="btn btn-sm btn-outline-light"
          aria-pressed="false"
          :disabled="submitting"
          @click="emit('switch-group')"
        >
          Group of Cues
        </button>
      </fieldset>
    </div>

    <div class="cue-card-section">
      <span :id="`${uid}-type`" class="cue-card-label">Cue type</span>
      <CueTypePicker
        ref="picker"
        v-model="selectedTypeId"
        :cue-types="showStore.cueTypes"
        :writable-ids="writableTypeIds"
        :disabled="submitting"
        :aria-label="'Cue type'"
      />
    </div>

    <div class="cue-card-fields">
      <div class="cue-number">
        <label :for="`${uid}-number`" class="cue-card-label">Cue number</label>
        <input
          :id="`${uid}-number`"
          ref="numberInput"
          v-model="ident"
          class="form-control cue-number-input"
          :class="{ 'cue-number-warn': duplicate }"
          maxlength="50"
          autocomplete="off"
          :disabled="submitting"
          @input="touched = true"
          @keydown.enter.prevent="onEnter"
        />
      </div>
      <div v-if="mode === 'add' && selectedTypeId != null" class="cue-nearest">
        <span class="cue-card-label">Nearest {{ typePrefix }} cues</span>
        <div v-if="nearest.previous || nearest.next" class="cue-nearest-row">
          <template v-if="nearest.previous">
            <span class="cue-chip" :style="chipStyle(nearest.previous.cue)">
              {{ cueLabel(nearest.previous.cue) }}
            </span>
            <span class="cue-card-caption">{{ nearest.previous.where }}</span>
          </template>
          <span class="cue-card-caption">→ this line →</span>
          <template v-if="nearest.next">
            <span class="cue-chip" :style="chipStyle(nearest.next.cue)">
              {{ cueLabel(nearest.next.cue) }}
            </span>
            <span class="cue-card-caption">{{ nearest.next.where }}</span>
          </template>
        </div>
        <div v-else class="cue-card-caption">No {{ typePrefix }} cues yet.</div>
        <div
          v-if="suggestionNote"
          class="cue-card-caption mt-1"
          :class="{ 'cue-warn': !suggestion.value }"
        >
          {{ suggestionNote }}
        </div>
      </div>
      <div v-else-if="mode === 'add'" class="cue-card-caption align-self-end pb-2">
        Choose a cue type to get a suggested number.
      </div>
    </div>

    <output v-if="changedElsewhere" class="cue-warn d-block mt-2">
      This cue was changed by someone else. Saving will replace their change.
      <button type="button" class="btn btn-sm btn-outline-light ms-2" @click="useTheirVersion">
        Use Their Version
      </button>
    </output>
    <output v-if="duplicate" class="cue-warn d-block mt-2">
      {{ duplicateText }}
    </output>
    <div v-if="error" class="cue-error mt-2" role="alert">{{ error }}</div>

    <div class="cue-card-actions">
      <span v-if="mode === 'add'" class="cue-card-caption">
        <kbd>Enter</kbd> add &nbsp;·&nbsp; <kbd>Esc</kbd> cancel
      </span>
      <button
        v-if="mode === 'edit'"
        type="button"
        class="btn btn-danger"
        :disabled="isLive || submitting"
        @click="onDelete"
      >
        Delete Cue
      </button>
      <span class="flex-fill" />
      <button
        type="button"
        class="btn btn-secondary"
        :disabled="submitting"
        @click="emit('cancel')"
      >
        Cancel
      </button>
      <button
        v-if="mode === 'add'"
        type="button"
        class="btn btn-outline-success"
        :disabled="!canSubmit || submitting"
        @click="submitAdd(true)"
      >
        Add and Stay Open
      </button>
      <button
        type="button"
        class="btn btn-success"
        :disabled="!canSubmit || submitting || (mode === 'edit' && (isLive || !changed))"
        @click="mode === 'add' ? submitAdd(false) : submitEdit()"
      >
        {{ primaryLabel }}
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, useId, watch } from 'vue';
import log from 'loglevel';
import CueTypePicker from '@/components/show/config/cues/CueTypePicker.vue';
import { useConfirm } from '@/composables/useConfirm';
import { useCueDisplay } from '@/composables/useCueDisplay';
import { useCuePermissions } from '@/composables/useCuePermissions';
import { useLineSuggestion } from '@/composables/useCueSuggestion';
import { useScriptStore } from '@/stores/script';
import { useShowStore } from '@/stores/show';
import type { Cue } from '@/types/api/cues';
import type { ScriptLine } from '@/types/api/script';

const props = defineProps<{
  mode: 'add' | 'edit' | 'view';
  line: ScriptLine;
  /** The start of the line's text, used to say which line a cue is on. */
  lineLabel: string;
  /** The cue being edited or viewed. */
  cue?: Cue | null;
  /** The type chosen in the add card, shared with the group card. */
  typeId: number | null;
  /** For a view-only group: the group's label, shown in place of the sample cue's. */
  groupLabel?: string | null;
}>();

const emit = defineEmits<{
  'update:typeId': [id: number | null];
  cancel: [];
  /** The card finished and should close. */
  done: [];
  /** A cue was added; `stay` is true for "Add and Stay Open". */
  added: [typeId: number, stay: boolean];
  'switch-group': [];
  /** This card has its own change request in flight (so a reload it causes is not "someone else"). */
  busy: [value: boolean];
}>();

const uid = useId();
const scriptStore = useScriptStore();
const showStore = useShowStore();
const { confirm } = useConfirm();
const { cueLabel, cueBackgroundColour, contrastColor } = useCueDisplay();
const { isLiveSession: isLive, writableTypeIds } = useCuePermissions();

const picker = ref<InstanceType<typeof CueTypePicker> | null>(null);
const numberInput = ref<HTMLInputElement | null>(null);

const submitting = ref(false);
const error = ref<string | null>(null);
const touched = ref(false);
const ident = ref(props.mode === 'add' ? '' : (props.cue?.ident ?? ''));

// In add mode the chosen type is shared with the group card (v-model); in edit mode
// it is local to this card.
const editTypeId = ref<number | null>(props.cue?.cue_type_id ?? null);
const selectedTypeId = computed<number | null>({
  get: () => (props.mode === 'add' ? props.typeId : editTypeId.value),
  set: (value) => {
    if (props.mode === 'add') emit('update:typeId', value);
    else editTypeId.value = value;
  },
});

const typePrefix = computed(() => showStore.cueTypeById(selectedTypeId.value)?.prefix ?? '');
const trimmedIdent = computed(() => ident.value.trim());
const canSubmit = computed(() => selectedTypeId.value != null && trimmedIdent.value !== '');
const changed = computed(
  () =>
    props.cue != null &&
    (trimmedIdent.value !== (props.cue.ident ?? '') ||
      selectedTypeId.value !== props.cue.cue_type_id)
);

const editLabel = computed(() => (props.cue ? cueLabel(props.cue) : ''));
const primaryLabel = computed(() => {
  if (props.mode === 'edit') return submitting.value ? 'Saving…' : 'Save Cue';
  if (submitting.value) return 'Adding…';
  return canSubmit.value ? `Add ${typePrefix.value} ${trimmedIdent.value}` : 'Add Cue';
});

// ── Suggested number and nearest cues ───────────────────────────────────────

const { nearest, suggestion } = useLineSuggestion(() => props.line, selectedTypeId);

const suggestionNote = computed(() => {
  if (props.mode !== 'add' || selectedTypeId.value == null) return '';
  const { value, reason, previous, next } = suggestion.value;
  const prefix = typePrefix.value;
  if (value) {
    if (previous && next)
      return `${value} is suggested because it sits between them. Type over it to use another number.`;
    if (previous) return `${value} is suggested as the next number after ${prefix} ${previous}.`;
    if (next) return `${value} is suggested as the number before ${prefix} ${next}.`;
    return `${value} is the first free number.`;
  }
  if (previous && next) {
    return reason === 'out-of-order'
      ? `${prefix} ${previous} comes before ${prefix} ${next} in the script, so no number is suggested. Type the number you want.`
      : `No free number between ${prefix} ${previous} and ${prefix} ${next}. Type the number you want.`;
  }
  return '';
});

// Fill in the suggestion until the person types their own number.
watch(
  () => [props.mode, selectedTypeId.value, suggestion.value.value] as const,
  ([mode, , value]) => {
    if (mode === 'add' && !touched.value) ident.value = value ?? '';
  },
  { immediate: true }
);

// ── Duplicates ──────────────────────────────────────────────────────────────

const duplicate = computed<{ page: number | null } | null>(() => {
  const typeId = selectedTypeId.value;
  const wanted = trimmedIdent.value;
  if (typeId == null || !wanted) return null;
  for (const [lineId, cues] of Object.entries(scriptStore.cues)) {
    for (const cue of cues) {
      if (cue.cue_type_id === typeId && cue.ident === wanted && cue.id !== props.cue?.id) {
        return { page: scriptStore.linePositions[lineId]?.page ?? null };
      }
    }
  }
  return null;
});

const duplicateText = computed(() => {
  const label = `${typePrefix.value} ${trimmedIdent.value}`;
  const where = duplicate.value?.page != null ? ` on page ${duplicate.value.page}` : '';
  return `${label} is already used${where}. You can still save.`;
});

// ── The cue changed under us ────────────────────────────────────────────────

// Someone else edited this cue while the card was open. If nothing has been typed, show the new
// values so Save cannot send old ones. If something has, keep it, say so on the card and let the
// person choose: Save replaces the other change, or "Use Their Version" drops their own edits.
const changedElsewhere = ref(false);

function useTheirVersion(): void {
  ident.value = props.cue?.ident ?? '';
  editTypeId.value = props.cue?.cue_type_id ?? null;
  changedElsewhere.value = false;
}

watch(
  () => [props.cue?.ident ?? '', props.cue?.cue_type_id ?? null] as const,
  ([newIdent, newType], [oldIdent, oldType]) => {
    if (props.mode !== 'edit' || submitting.value) return;
    // A reload hands over fresh objects; only an actual difference is someone else's edit.
    if (newIdent === oldIdent && newType === oldType) return;
    const edited = trimmedIdent.value !== oldIdent || editTypeId.value !== oldType;
    if (edited) changedElsewhere.value = true;
    else useTheirVersion();
  }
);

// ── View-only note ──────────────────────────────────────────────────────────

const viewLabel = computed(() => props.groupLabel ?? (props.cue ? cueLabel(props.cue) : ''));
const viewPrefix = computed(
  () => showStore.cueTypeById(props.cue?.cue_type_id ?? null)?.prefix ?? ''
);
const viewTypeDescription = computed(
  () => showStore.cueTypeById(props.cue?.cue_type_id ?? null)?.description ?? 'Cue'
);

// ── Display helpers ─────────────────────────────────────────────────────────

function chipStyle(cue: Cue): Record<string, string> {
  const background = cueBackgroundColour(cue);
  return { backgroundColor: background, color: contrastColor(background) };
}

// ── Actions ─────────────────────────────────────────────────────────────────

function onEnter(): void {
  if (!canSubmit.value || submitting.value) return;
  if (props.mode === 'add') void submitAdd(false);
  else if (!isLive.value && changed.value) void submitEdit();
}

function rememberType(typeId: number): void {
  try {
    localStorage.setItem('cueEditType', String(typeId));
  } catch {
    // Storage can be unavailable; remembering the type is only a convenience.
  }
}

async function submitAdd(stay: boolean): Promise<void> {
  const typeId = selectedTypeId.value;
  if (typeId == null || !trimmedIdent.value || submitting.value) return;
  const label = `${typePrefix.value} ${trimmedIdent.value}`;
  submitting.value = true;
  error.value = null;
  let ok = false;
  try {
    ok = await scriptStore.addNewCue({
      cueType: typeId,
      ident: trimmedIdent.value,
      lineId: props.line.id as number,
    });
  } catch (err) {
    // The store reports a failed request as `false`; a throw here is unexpected.
    log.error('Unable to change the cues', err);
  }
  if (!ok) {
    error.value = `${label} was not added. Your entry is still here, so you can try again.`;
    submitting.value = false;
    return;
  }
  submitting.value = false;
  rememberType(typeId);
  emit('added', typeId, stay);
  if (!stay) {
    emit('done');
    return;
  }
  // Stay open: start again from the next suggestion, selected ready to type over.
  touched.value = false;
  ident.value = suggestion.value.value ?? '';
  await nextTick();
  numberInput.value?.focus();
  numberInput.value?.select();
}

async function submitEdit(): Promise<void> {
  if (!props.cue || selectedTypeId.value == null || !trimmedIdent.value || submitting.value) return;
  submitting.value = true;
  emit('busy', true);
  error.value = null;
  let ok = false;
  try {
    ok = await scriptStore.editCue({
      cueId: props.cue.id,
      cueType: selectedTypeId.value,
      ident: trimmedIdent.value,
      lineId: props.line.id as number,
    });
  } catch (err) {
    // The store reports a failed request as `false`; a throw here is unexpected.
    log.error('Unable to change the cues', err);
  }
  if (!ok) {
    error.value = `${editLabel.value} was not saved. Your entry is still here, so you can try again.`;
    submitting.value = false;
    emit('busy', false);
    return;
  }
  submitting.value = false;
  // Close first, then clear busy: the cue this card was editing may already have changed.
  emit('done');
  emit('busy', false);
}

async function onDelete(): Promise<void> {
  if (!props.cue || isLive.value || submitting.value) return;
  const confirmed = await confirm(
    `Delete ${editLabel.value}?\nOn the line “${props.lineLabel}”\nIt is removed from the current script revision. Other revisions keep it.`,
    { title: 'Delete Cue', okVariant: 'danger', okTitle: 'Delete Cue' }
  );
  if (!confirmed) return;
  submitting.value = true;
  emit('busy', true);
  error.value = null;
  let ok = false;
  try {
    ok = await scriptStore.deleteCue({
      cueId: props.cue.id,
      lineId: props.line.id as number,
    });
  } catch (err) {
    // The store reports a failed request as `false`; a throw here is unexpected.
    log.error('Unable to change the cues', err);
  }
  if (!ok) {
    error.value = `${editLabel.value} was not deleted. Please try again.`;
    submitting.value = false;
    emit('busy', false);
    return;
  }
  submitting.value = false;
  emit('done');
  emit('busy', false);
}

onMounted(() => {
  if (props.mode === 'view') return;
  // The number field, or the type buttons when no type is chosen yet.
  if (selectedTypeId.value == null) picker.value?.focus();
  else {
    numberInput.value?.focus();
    numberInput.value?.select();
  }
});

// A type chosen later in add mode moves the person on to the number.
watch(
  () => props.typeId,
  async (value, previous) => {
    if (props.mode === 'add' && previous == null && value != null) {
      await nextTick();
      numberInput.value?.focus();
      numberInput.value?.select();
    }
  }
);
</script>

<style scoped>
.cue-card {
  margin: 6px 0;
  padding: 14px 16px;
  background: var(--bs-gray-800);
  border: 1px solid var(--bs-success);
  border-radius: 0.25rem;
  box-shadow: 0 0 0 0.2rem rgba(0, 188, 140, 0.25);
  text-align: left;
}

.cue-card-head {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.cue-card-section {
  margin-top: 12px;
}

.cue-card-label {
  display: block;
  margin-bottom: 4px;
  color: var(--bs-gray-500);
  font-size: 0.8125rem;
}

.cue-card-caption {
  color: var(--bs-gray-500);
  font-size: 0.8125rem;
}

.cue-card-fields {
  display: flex;
  gap: 20px;
  align-items: flex-start;
  margin-top: 12px;
  flex-wrap: wrap;
}

.cue-number {
  width: 150px;
}

.cue-number-input {
  min-height: 38px;
  font-size: 1.125rem;
  font-weight: 700;
  border-color: var(--bs-success);
}

.cue-number-warn {
  border-color: var(--bs-warning);
}

.cue-nearest {
  flex: 1;
  min-width: 260px;
}

.cue-nearest-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
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

kbd {
  padding: 1px 6px;
  border: 1px solid var(--bs-gray-600);
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.05);
  color: var(--bs-gray-200);
  font-family: inherit;
  font-size: 0.75rem;
}

.cue-warn {
  color: var(--bs-warning);
  font-size: 0.8125rem;
  font-weight: 700;
}

.cue-error {
  padding: 10px 14px;
  border: 2px solid var(--bs-danger);
  border-radius: 0.25rem;
  color: #fff;
  font-size: 0.875rem;
  font-weight: 700;
}

.cue-card-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  flex-wrap: wrap;
}

.cue-note {
  display: inline-block;
  margin: 4px 0 0 8px;
  padding: 10px 14px;
  background: var(--bs-gray-800);
  border: 1px solid var(--bs-gray-600);
  border-radius: 0.25rem;
  font-size: 0.875rem;
  text-align: left;
}

.cue-note-caption {
  margin-top: 2px;
  color: var(--bs-gray-500);
  font-size: 0.8125rem;
}

.flex-fill {
  flex: 1;
}
</style>
