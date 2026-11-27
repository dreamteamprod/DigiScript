<template>
  <section
    class="cue-card"
    :aria-label="mode === 'add' ? 'Add a group of cues to this line' : `Edit group ${groupName}`"
    @keydown.esc.stop.prevent="emit('cancel')"
  >
    <div class="cue-card-head">
      <b>{{ mode === 'add' ? 'Add a group of cues to this line' : 'Edit cue group' }}</b>
      <span v-if="mode === 'edit'" class="cue-card-caption">{{ members.length }} cues</span>
      <span class="flex-fill" />
      <div v-if="mode === 'add'" class="btn-group" role="group" aria-label="What to add">
        <button
          type="button"
          class="btn btn-sm btn-outline-light"
          aria-pressed="false"
          :disabled="submitting"
          @click="emit('switch-single')"
        >
          Single Cue
        </button>
        <button type="button" class="btn btn-sm btn-primary" aria-pressed="true">
          Group of Cues
        </button>
      </div>
    </div>

    <div class="cue-card-section">
      <span class="cue-card-label">
        {{
          mode === 'add'
            ? 'Cue type (every cue in a group shares it)'
            : 'Cue type (fixed once a group exists)'
        }}
      </span>
      <CueTypePicker
        v-if="mode === 'add'"
        ref="picker"
        v-model="selectedTypeId"
        :cue-types="showStore.cueTypes"
        :writable-ids="writableTypeIds"
        :disabled="submitting"
      />
      <span v-else class="fixed-type">
        <span class="swatch" :style="{ background: previewColour }" aria-hidden="true" />
        <b>{{ typePrefix }}</b> {{ typeDescription }}
      </span>
    </div>

    <div class="cue-card-fields align-items-end">
      <div class="range-field">
        <label :for="`${uid}-from`" class="cue-card-label">From number</label>
        <input
          :id="`${uid}-from`"
          ref="fromInput"
          v-model="rangeFrom"
          class="form-control"
          :class="{ 'is-invalid': rangeInvalid }"
          inputmode="numeric"
          autocomplete="off"
          :disabled="submitting"
          @input="fromTouched = true"
          @keydown.enter.prevent="addRange"
        />
      </div>
      <div class="range-field">
        <label :for="`${uid}-to`" class="cue-card-label">To number</label>
        <input
          :id="`${uid}-to`"
          v-model="rangeTo"
          class="form-control"
          :class="{ 'is-invalid': rangeInvalid }"
          inputmode="numeric"
          autocomplete="off"
          :disabled="submitting"
          @keydown.enter.prevent="addRange"
        />
      </div>
      <button
        type="button"
        class="btn btn-primary"
        :disabled="!rangeValid || submitting"
        @click="addRange"
      >
        Add Range
      </button>
      <button type="button" class="btn btn-outline-light" :disabled="submitting" @click="addOne">
        Add One Cue
      </button>
    </div>
    <div v-if="rangeInvalid" class="cue-warn mt-2" role="status">
      Use whole numbers, with From no higher than To, and no more than 10,000 cues.
    </div>

    <div class="cue-card-section">
      <span class="cue-card-label">
        {{
          members.length === 0
            ? 'No cues yet. Add a range, or add one cue at a time.'
            : `${members.length} ${members.length === 1 ? 'cue' : 'cues'} in this group, in order. Drag, or use the arrows, to reorder.`
        }}
      </span>
      <div v-if="members.length" class="member-list">
        <span
          v-for="(member, index) in members"
          :key="member.key"
          class="member-tile"
          :class="{ 'member-over': dragOverIndex === index && dragIndex !== index }"
          :data-member-key="member.key"
          @dragover.prevent="dragOverIndex = index"
          @dragleave="dragOverIndex = null"
          @drop.prevent="onDrop(index)"
        >
          <span
            class="member-handle"
            draggable="true"
            aria-hidden="true"
            @dragstart="onDragStart(index, $event)"
            @dragend="onDragEnd"
          >
            ⋮
          </span>
          <button
            type="button"
            data-move="earlier"
            :aria-label="`Move cue ${memberName(member)} earlier`"
            :disabled="index === 0 || submitting"
            @click="move(index, -1)"
          >
            ‹
          </button>
          <input
            v-model="member.ident"
            class="member-input"
            :aria-label="`Cue ${index + 1} of ${members.length}`"
            maxlength="50"
            autocomplete="off"
            :disabled="submitting"
          />
          <button
            type="button"
            data-move="later"
            :aria-label="`Move cue ${memberName(member)} later`"
            :disabled="index === members.length - 1 || submitting"
            @click="move(index, 1)"
          >
            ›
          </button>
          <button
            type="button"
            class="member-remove"
            :aria-label="`Remove cue ${memberName(member)}`"
            :disabled="submitting"
            @click="remove(index)"
          >
            ×
          </button>
        </span>
      </div>
    </div>

    <div class="cue-card-fields align-items-end">
      <div class="name-field">
        <label :for="`${uid}-name`" class="cue-card-label">Group name (optional)</label>
        <input
          :id="`${uid}-name`"
          v-model="labelOverride"
          class="form-control"
          maxlength="100"
          autocomplete="off"
          :disabled="submitting"
        />
      </div>
      <div v-if="selectedTypeId != null">
        <span class="cue-card-label">Shows in the script as</span>
        <span class="cue-chip cue-chip-group" :style="chipStyle">{{ previewLabel }}</span>
      </div>
    </div>

    <div v-if="error" class="cue-error mt-2" role="alert">{{ error }}</div>

    <div class="cue-card-actions">
      <button
        v-if="mode === 'edit'"
        type="button"
        class="btn btn-danger"
        :disabled="isLive || submitting"
        @click="onDelete"
      >
        Delete Group
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
        type="button"
        class="btn btn-success"
        :disabled="!valid || submitting || (mode === 'edit' && (isLive || !dirty))"
        @click="submit"
      >
        {{ primaryLabel }}
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, useId, watch } from 'vue';
import CueTypePicker from '@/components/show/config/cues/CueTypePicker.vue';
import { useConfirm } from '@/composables/useConfirm';
import { useCueDisplay } from '@/composables/useCueDisplay';
import { useCuePermissions } from '@/composables/useCuePermissions';
import { useLineSuggestion } from '@/composables/useCueSuggestion';
import { expandWholeRange } from '@/js/cueRange';
import { useScriptStore } from '@/stores/script';
import { useShowStore } from '@/stores/show';
import type { Cue, CueGroup } from '@/types/api/cues';
import type { ScriptLine } from '@/types/api/script';

interface Member {
  /** Stable identity for the list, so focus and drag follow a moved member. */
  key: number;
  /** The server's id for an existing member. */
  id?: number;
  ident: string;
}

const props = defineProps<{
  mode: 'add' | 'edit';
  line: ScriptLine;
  lineLabel: string;
  group?: CueGroup | null;
  groupCues?: Cue[];
  typeId: number | null;
}>();

const emit = defineEmits<{
  'update:typeId': [id: number | null];
  cancel: [];
  done: [];
  added: [typeId: number];
  'switch-single': [];
  /** Whether the card holds changes that would be lost if it closed. */
  dirty: [value: boolean];
}>();

const uid = useId();
const scriptStore = useScriptStore();
const showStore = useShowStore();
const { confirm } = useConfirm();
const { cueGroupLabel, cueGroupBackgroundColour, contrastColor } = useCueDisplay();
const { isLiveSession: isLive, writableTypeIds } = useCuePermissions();

const picker = ref<InstanceType<typeof CueTypePicker> | null>(null);
const fromInput = ref<HTMLInputElement | null>(null);

let nextKey = 1;
const toMembers = (cues: readonly Cue[] | undefined): Member[] =>
  (cues ?? []).map((c) => ({ key: nextKey++, id: c.id, ident: c.ident ?? '' }));

const initialMembers = toMembers(props.groupCues);
const initialLabel = props.group?.label_override ?? '';
const members = ref<Member[]>(initialMembers.map((m) => ({ ...m })));
const labelOverride = ref(initialLabel);
const rangeFrom = ref('');
const fromTouched = ref(false);
const rangeTo = ref('');
const submitting = ref(false);
const error = ref<string | null>(null);
const dragIndex = ref<number | null>(null);
const dragOverIndex = ref<number | null>(null);

const selectedTypeId = computed<number | null>({
  get: () => (props.mode === 'add' ? props.typeId : (props.group?.cue_type_id ?? null)),
  set: (value) => {
    if (props.mode === 'add') emit('update:typeId', value);
  },
});

const cueType = computed(() => showStore.cueTypeById(selectedTypeId.value));
const typePrefix = computed(() => cueType.value?.prefix ?? '');
const typeDescription = computed(() => cueType.value?.description ?? '');

// ── Preview ─────────────────────────────────────────────────────────────────

const previewGroup = computed<CueGroup | null>(() =>
  selectedTypeId.value == null
    ? null
    : {
        id: 0,
        cue_type_id: selectedTypeId.value,
        label_override: labelOverride.value.trim() || null,
      }
);
const previewCues = computed<Cue[]>(() =>
  members.value.map((m, i) => ({
    id: 0,
    cue_type_id: selectedTypeId.value,
    ident: m.ident,
    group_id: 0,
    sort_order: i,
    line_position: null,
  }))
);
const previewLabel = computed(() =>
  previewGroup.value ? cueGroupLabel(previewGroup.value, previewCues.value) : ''
);
const previewColour = computed(() =>
  previewGroup.value ? cueGroupBackgroundColour(previewGroup.value) : '#000000'
);
const chipStyle = computed(() => ({
  backgroundColor: previewColour.value,
  color: contrastColor(previewColour.value),
}));
const groupName = computed(() => props.group?.label_override || previewLabel.value);

// ── Range ───────────────────────────────────────────────────────────────────

// From starts at the suggested number when that is a whole number.
const { suggestion } = useLineSuggestion(() => props.line, selectedTypeId);
watch(
  () => [props.mode, suggestion.value.value] as const,
  ([mode, value]) => {
    if (mode === 'add' && !fromTouched.value) {
      rangeFrom.value = value != null && /^\d+$/.test(value) ? value : '';
    }
  },
  { immediate: true }
);

const rangeExpanded = computed(() => expandWholeRange(rangeFrom.value, rangeTo.value));
const rangeValid = computed(() => rangeExpanded.value != null);
// Only complain once both ends have something in them.
const rangeInvalid = computed(
  () => rangeFrom.value.trim() !== '' && rangeTo.value.trim() !== '' && !rangeValid.value
);

function addRange(): void {
  const idents = rangeExpanded.value;
  if (!idents || submitting.value) return;
  members.value.push(...idents.map((ident) => ({ key: nextKey++, ident })));
  rangeFrom.value = '';
  rangeTo.value = '';
}

async function addOne(): Promise<void> {
  const key = nextKey++;
  members.value.push({ key, ident: '' });
  await nextTick();
  document.querySelector<HTMLInputElement>(`[data-member-key="${key}"] .member-input`)?.focus();
}

const memberName = (member: Member) => member.ident.trim() || 'blank';

function remove(index: number): void {
  members.value.splice(index, 1);
}

/** Swap with a neighbour, keeping focus on the control that was used. */
async function move(index: number, by: -1 | 1): Promise<void> {
  const target = index + by;
  if (target < 0 || target >= members.value.length) return;
  const [item] = members.value.splice(index, 1);
  members.value.splice(target, 0, item);
  await nextTick();
  const tile = document.querySelector(`[data-member-key="${item.key}"]`);
  const wanted = tile?.querySelector<HTMLButtonElement>(
    `[data-move="${by < 0 ? 'earlier' : 'later'}"]`
  );
  // At the end of the list that button is disabled, so use the other one.
  const control =
    wanted && !wanted.disabled
      ? wanted
      : tile?.querySelector<HTMLButtonElement>(`[data-move="${by < 0 ? 'later' : 'earlier'}"]`);
  control?.focus();
}

function onDragStart(index: number, event: DragEvent): void {
  dragIndex.value = index;
  const { dataTransfer } = event;
  if (dataTransfer) {
    dataTransfer.effectAllowed = 'move';
    dataTransfer.setData('text/plain', '');
  }
}

function onDrop(target: number): void {
  const from = dragIndex.value;
  dragIndex.value = null;
  dragOverIndex.value = null;
  if (from == null || from === target) return;
  const [item] = members.value.splice(from, 1);
  members.value.splice(target, 0, item);
}

function onDragEnd(): void {
  dragIndex.value = null;
  dragOverIndex.value = null;
}

// ── State ───────────────────────────────────────────────────────────────────

const valid = computed(
  () =>
    selectedTypeId.value != null &&
    members.value.length > 0 &&
    members.value.every((m) => m.ident.trim() !== '')
);

const dirty = computed(() => {
  if (props.mode === 'add') {
    return members.value.length > 0 || labelOverride.value.trim() !== '';
  }
  if (labelOverride.value.trim() !== initialLabel.trim()) return true;
  if (members.value.length !== initialMembers.length) return true;
  return members.value.some(
    (m, i) => m.id !== initialMembers[i].id || m.ident.trim() !== initialMembers[i].ident
  );
});
watch(dirty, (value) => emit('dirty', value), { immediate: true });

const primaryLabel = computed(() => {
  if (props.mode === 'edit') return submitting.value ? 'Saving…' : 'Save Group';
  if (submitting.value) return 'Adding…';
  return members.value.length > 0 ? `Add Group of ${members.value.length}` : 'Add Group';
});

// ── Actions ─────────────────────────────────────────────────────────────────

async function submit(): Promise<void> {
  const typeId = selectedTypeId.value;
  if (!valid.value || typeId == null || submitting.value) return;
  submitting.value = true;
  error.value = null;
  const label = previewLabel.value;
  const label_override = labelOverride.value.trim();
  try {
    const ok =
      props.mode === 'add'
        ? await scriptStore.addCueGroup({
            cueTypeId: typeId,
            labelOverride: label_override || undefined,
            lineId: props.line.id as number,
            cues: members.value.map((m, i) => ({ ident: m.ident.trim(), sortOrder: i })),
          })
        : await scriptStore.editCueGroup({
            groupId: props.group!.id,
            labelOverride: label_override,
            lineId: props.line.id as number,
            cues: members.value.map((m, i) => ({
              id: m.id,
              ident: m.ident.trim(),
              sortOrder: i,
            })),
          });
    if (!ok) throw new Error('rejected');
  } catch {
    error.value = `${label} was not ${props.mode === 'add' ? 'added' : 'saved'}. Your entries are still here, so you can try again.`;
    submitting.value = false;
    return;
  }
  submitting.value = false;
  if (props.mode === 'add') emit('added', typeId);
  emit('done');
}

async function onDelete(): Promise<void> {
  if (!props.group || isLive.value || submitting.value) return;
  const confirmed = await confirm(
    `Delete ${previewLabel.value} and its ${members.value.length} cues?\nOn the line “${props.lineLabel}”\nThey are removed from the current script revision. Other revisions keep them.`,
    { title: 'Delete Cue Group', okVariant: 'danger', okTitle: 'Delete Group' }
  );
  if (!confirmed) return;
  submitting.value = true;
  error.value = null;
  try {
    const ok = await scriptStore.deleteCueGroup({
      groupId: props.group.id,
      lineId: props.line.id as number,
    });
    if (!ok) throw new Error('rejected');
  } catch {
    error.value = `${previewLabel.value} was not deleted. Please try again.`;
    submitting.value = false;
    return;
  }
  submitting.value = false;
  emit('done');
}

onMounted(() => {
  if (props.mode === 'add' && selectedTypeId.value == null) picker.value?.focus();
  else fromInput.value?.focus();
});
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
  gap: 12px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.range-field {
  width: 110px;
}

.name-field {
  width: 260px;
}

.fixed-type {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 12px;
  border: 2px solid #fff;
  border-radius: 0.25rem;
  background: var(--bs-primary);
}

.swatch {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 3px;
}

.member-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-height: 220px;
  overflow-y: auto;
  padding: 2px;
}

.member-tile {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--bs-gray-600);
  border-radius: 0.25rem;
}

.member-tile.member-over {
  outline: 2px solid var(--bs-primary);
}

.member-tile button,
.member-handle {
  min-width: 32px;
  min-height: 34px;
  padding: 0;
  border: 0;
  background: transparent;
  color: #fff;
  font-size: 1rem;
}

.member-tile button:disabled {
  color: var(--bs-gray-700);
}

.member-tile button:focus-visible {
  outline: 2px solid #fff;
  outline-offset: -2px;
}

.member-handle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--bs-gray-500);
  cursor: grab;
}

.member-remove {
  border-left: 1px solid var(--bs-gray-700) !important;
}

.member-input {
  width: 56px;
  min-height: 30px;
  border: 0;
  border-radius: 2px;
  text-align: center;
  font-weight: 700;
  font-size: 0.875rem;
  color: var(--bs-gray-800);
  background: #fff;
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

.cue-chip-group {
  border: 2px dashed #fff;
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

.flex-fill {
  flex: 1;
}
</style>
