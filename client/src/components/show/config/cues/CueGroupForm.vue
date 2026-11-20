<template>
  <div>
    <BFormGroup label="Cue Type">
      <BFormSelect
        v-model="localCueTypeId"
        :options="groupCueTypeOptions"
        :disabled="props.readonly"
      />
    </BFormGroup>

    <BFormGroup
      label="Label Override"
      description="Optional — leave blank for automatic label based on first/last cue."
    >
      <BFormInput v-model="localLabelOverride" placeholder="e.g. Music Intro" />
    </BFormGroup>

    <div v-if="localCueTypeId != null" class="mb-3 d-flex align-items-center gap-2">
      <small class="text-muted">Preview:</small>
      <span
        class="badge"
        :style="{
          backgroundColor: previewColour,
          color: contrastColor(previewColour),
          padding: '0.3rem 0.5rem',
          fontSize: '0.9rem',
        }"
      >
        {{ previewLabel }}
      </span>
    </div>

    <BFormGroup label="Cues">
      <div v-if="localCues.length === 0" class="text-muted small mb-2">
        No cues yet. Add a range or single cue below.
      </div>
      <div class="cue-list-scroll">
        <div
          v-for="(cue, index) in localCues"
          :key="index"
          class="d-flex align-items-center gap-2 mb-1 cue-row"
          :class="{ 'drag-over': dragOverIndex === index && dragIndex !== index }"
          @dragover.prevent="dragOverIndex = index"
          @dragleave="dragOverIndex = null"
          @drop.prevent="onDrop(index)"
        >
          <span
            draggable="true"
            class="drag-handle"
            @dragstart="onDragStart(index, $event)"
            @dragend="onDragEnd"
          >
            <IMdiDragVertical />
          </span>
          <BFormInput v-model="cue.ident" placeholder="Identifier" />
          <BButton
            size="sm"
            variant="outline-secondary"
            :disabled="index === 0"
            @click="moveUp(index)"
          >
            <IMdiChevronUp />
          </BButton>
          <BButton
            size="sm"
            variant="outline-secondary"
            :disabled="index === localCues.length - 1"
            @click="moveDown(index)"
          >
            <IMdiChevronDown />
          </BButton>
          <BButton size="sm" variant="outline-danger" @click="removeCue(index)">
            <IMdiClose />
          </BButton>
        </div>
      </div>
    </BFormGroup>

    <BFormGroup label="Add Range" description="e.g. 1 > 100 adds cues 1 through 100">
      <BInputGroup>
        <BFormInput
          v-model="rangeInput"
          placeholder="1 > 100"
          :state="rangeState"
          @keyup.enter="addRange"
        />
        <BButton variant="outline-primary" :disabled="!canAddRange" @click="addRange">
          Add Range
        </BButton>
      </BInputGroup>
      <BFormInvalidFeedback :state="rangeState">
        Use format: start &gt; end (e.g. 1 &gt; 100), max 10000 cues per range.
      </BFormInvalidFeedback>
    </BFormGroup>

    <BButton class="mb-2" size="sm" variant="outline-secondary" @click="addSingleCue">
      <IMdiPlusBox /> Add Single Cue
    </BButton>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useCueDisplay } from '@/composables/useCueDisplay';
import type { Cue, CueGroup } from '@/types/api/cues';

const props = defineProps<{
  cueTypeOptions: { value: number | null; text: string }[];
  readonly?: boolean;
}>();

const emit = defineEmits<{ 'update:valid': [val: boolean] }>();

const { cueGroupLabel, cueGroupBackgroundColour, contrastColor } = useCueDisplay();

const localCueTypeId = ref<number | null>(null);
const localLabelOverride = ref('');
const localCues = ref<{ id?: number; ident: string }[]>([]);
const rangeInput = ref('');
const dragIndex = ref<number | null>(null);
const dragOverIndex = ref<number | null>(null);

const groupCueTypeOptions = computed(() => props.cueTypeOptions.filter((o) => o.value !== null));

const previewGroup = computed<CueGroup | null>(() => {
  if (localCueTypeId.value == null) return null;
  return {
    id: 0,
    cue_type_id: localCueTypeId.value,
    label_override: localLabelOverride.value || null,
  };
});

const previewCues = computed<Cue[]>(() =>
  localCues.value.map((c, i) => ({
    id: 0,
    cue_type_id: localCueTypeId.value!,
    ident: c.ident,
    group_id: 0,
    sort_order: i,
  }))
);

const previewLabel = computed(() => {
  const g = previewGroup.value;
  return g ? cueGroupLabel(g, previewCues.value) : '';
});

const previewColour = computed(() => {
  const g = previewGroup.value;
  return g ? cueGroupBackgroundColour(g) : '#000000';
});

const rangeState = computed<boolean | null>(() => {
  if (!rangeInput.value.trim()) return null;
  return parseRange(rangeInput.value) !== null;
});

const canAddRange = computed(
  () => !!rangeInput.value.trim() && parseRange(rangeInput.value) !== null
);

const canSave = computed(
  () =>
    localCueTypeId.value != null &&
    localCues.value.length > 0 &&
    localCues.value.every((c) => c.ident.trim() !== '')
);

function parseRange(input: string): number[] | null {
  const match = input.trim().match(/^(\d+)\s*>\s*(\d+)$/);
  if (!match) return null;
  const start = parseInt(match[1], 10);
  const end = parseInt(match[2], 10);
  if (start > end || end - start >= 10000) return null;
  return Array.from({ length: end - start + 1 }, (_, i) => start + i);
}

function addRange(): void {
  const nums = parseRange(rangeInput.value);
  if (!nums) return;
  for (const n of nums) localCues.value.push({ ident: String(n) });
  rangeInput.value = '';
}

function addSingleCue(): void {
  localCues.value.push({ ident: '' });
}

function removeCue(index: number): void {
  localCues.value.splice(index, 1);
}

function moveUp(index: number): void {
  if (index === 0) return;
  [localCues.value[index - 1], localCues.value[index]] = [
    localCues.value[index],
    localCues.value[index - 1],
  ];
}

function moveDown(index: number): void {
  if (index === localCues.value.length - 1) return;
  [localCues.value[index], localCues.value[index + 1]] = [
    localCues.value[index + 1],
    localCues.value[index],
  ];
}

function onDragStart(index: number, event: DragEvent): void {
  dragIndex.value = index;
  const { dataTransfer } = event;
  if (dataTransfer) {
    dataTransfer.effectAllowed = 'move';
    dataTransfer.setData('text/plain', '');
  }
}

function onDrop(targetIndex: number): void {
  if (dragIndex.value === null || dragIndex.value === targetIndex) {
    dragIndex.value = null;
    dragOverIndex.value = null;
    return;
  }
  const items = [...localCues.value];
  const [removed] = items.splice(dragIndex.value, 1);
  items.splice(targetIndex, 0, removed);
  localCues.value = items;
  dragIndex.value = null;
  dragOverIndex.value = null;
}

function onDragEnd(): void {
  dragIndex.value = null;
  dragOverIndex.value = null;
}

function reset(initial?: {
  cueTypeId?: number | null;
  labelOverride?: string;
  cues?: { id?: number; ident: string }[];
}): void {
  localCueTypeId.value = initial?.cueTypeId ?? null;
  localLabelOverride.value = initial?.labelOverride ?? '';
  localCues.value = initial?.cues ? [...initial.cues] : [];
  rangeInput.value = '';
  dragIndex.value = null;
  dragOverIndex.value = null;
}

function getFormData(): {
  cueTypeId: number | null;
  labelOverride: string;
  cues: { id?: number; ident: string }[];
} {
  return {
    cueTypeId: localCueTypeId.value,
    labelOverride: localLabelOverride.value,
    cues: [...localCues.value],
  };
}

watch(canSave, (val) => emit('update:valid', val));

defineExpose({ reset, getFormData });
</script>

<style scoped>
.cue-list-scroll {
  border: 1px solid var(--bs-border-color);
  border-radius: 0.25rem;
  padding: 0.25rem 0.5rem;
  margin-bottom: 0.5rem;
}

.cue-row {
  border-radius: 4px;
  transition: background-color 0.1s ease;
}

.cue-row.drag-over {
  background-color: rgba(var(--bs-primary-rgb), 0.12);
}

.drag-handle {
  cursor: grab;
  color: var(--bs-secondary-color);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding: 0.25rem;
}

.drag-handle:active {
  cursor: grabbing;
}
</style>
