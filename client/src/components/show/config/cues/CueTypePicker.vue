<template>
  <div
    ref="root"
    class="cue-type-picker"
    role="radiogroup"
    :aria-label="ariaLabel"
    @keydown="onKeydown"
  >
    <button
      v-for="(type, index) in orderedTypes"
      :key="type.id"
      type="button"
      class="type-chip"
      :class="{ 'type-chip-on': type.id === modelValue }"
      role="radio"
      :aria-checked="type.id === modelValue"
      :aria-disabled="!isWritable(type.id)"
      :disabled="!isWritable(type.id) || disabled"
      :tabindex="tabIndexFor(type.id, index)"
      :data-cue-type-id="type.id"
      @click="select(type.id)"
    >
      <span class="swatch" :style="{ background: colourFor(type.id) }" aria-hidden="true" />
      <b>{{ type.prefix }}</b>
      <span>{{ isWritable(type.id) ? (type.description ?? '') : 'View only' }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useCueDisplay } from '@/composables/useCueDisplay';
import type { CueType } from '@/types/api/cues';

const props = withDefaults(
  defineProps<{
    cueTypes: CueType[];
    modelValue: number | null;
    /** Ids of the types this person may write; the rest are shown as view only. */
    writableIds: Set<number>;
    disabled?: boolean;
    ariaLabel?: string;
  }>(),
  { disabled: false, ariaLabel: 'Cue type' }
);

const emit = defineEmits<{ 'update:modelValue': [id: number] }>();

const { typeColour } = useCueDisplay();
const root = ref<HTMLElement | null>(null);

const isWritable = (id: number) => props.writableIds.has(id);
const colourFor = (id: number) => typeColour(id);

/** Writable types first, otherwise in their given order. */
const orderedTypes = computed(() => [
  ...props.cueTypes.filter((t) => isWritable(t.id)),
  ...props.cueTypes.filter((t) => !isWritable(t.id)),
]);

/** Roving tabindex: the chosen type is the tab stop, else the first writable one. */
function tabIndexFor(id: number, index: number): 0 | -1 {
  if (props.modelValue != null && props.cueTypes.some((t) => t.id === props.modelValue)) {
    return id === props.modelValue ? 0 : -1;
  }
  const firstWritable = orderedTypes.value.findIndex((t) => isWritable(t.id));
  return index === firstWritable ? 0 : -1;
}

function select(id: number): void {
  if (isWritable(id) && !props.disabled) emit('update:modelValue', id);
}

function onKeydown(event: KeyboardEvent): void {
  const forward = event.key === 'ArrowRight' || event.key === 'ArrowDown';
  const backward = event.key === 'ArrowLeft' || event.key === 'ArrowUp';
  if (!forward && !backward) return;
  const enabled = orderedTypes.value.filter((t) => isWritable(t.id));
  if (enabled.length === 0) return;
  event.preventDefault();
  const focusedId = Number((document.activeElement as HTMLElement | null)?.dataset.cueTypeId);
  const current = enabled.findIndex((t) => t.id === focusedId);
  const next = enabled[(current + (forward ? 1 : -1) + enabled.length) % enabled.length];
  select(next.id);
  root.value?.querySelector<HTMLElement>(`[data-cue-type-id="${next.id}"]`)?.focus();
}

defineExpose({
  /** Focus the chosen type, or the first writable one. */
  focus(): void {
    const target = props.modelValue ?? orderedTypes.value.find((t) => isWritable(t.id))?.id;
    if (target != null) {
      root.value?.querySelector<HTMLElement>(`[data-cue-type-id="${target}"]`)?.focus();
    }
  },
});
</script>

<style scoped>
.cue-type-picker {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.type-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 40px;
  padding: 0 0.75rem;
  border: 2px solid var(--bs-gray-600);
  border-radius: 0.25rem;
  background: transparent;
  color: #fff;
  font-size: 0.875rem;
}

.type-chip-on {
  border-color: #fff;
  background: var(--bs-primary);
}

.type-chip:disabled {
  border-style: dotted;
  color: var(--bs-gray-500);
}

.type-chip:focus-visible {
  outline: 2px solid #fff;
  outline-offset: 2px;
}

.swatch {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 3px;
  flex: none;
}
</style>
