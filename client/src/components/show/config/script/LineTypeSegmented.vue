<template>
  <BButtonGroup role="group" aria-label="Line type">
    <BButton
      v-for="option in options"
      :key="option.value"
      size="sm"
      :variant="modelValue === option.value ? 'primary' : 'outline-secondary'"
      :disabled="disabled"
      :aria-pressed="modelValue === option.value"
      @click="$emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </BButton>
  </BButtonGroup>
</template>

<script setup lang="ts">
/**
 * Design E's "Dialogue / Direction / Cue / Gap" segmented control. Only meaningful
 * for a line that hasn't been saved yet (`disabled` true otherwise) — switching an
 * already-saved line's type would need to migrate its cue associations, cuts and
 * (in collab) the shared draft's part schema, none of which is designed or
 * implemented. See ScriptLineEditor.vue/CollabScriptLineEditor.vue for how a type
 * change is actually carried out (delete + re-add the line locally, never a
 * `line_type` mutation on an existing line).
 */
import { LINE_TYPES } from '@/constants/lineTypes';
import { LINE_TYPE_LABELS } from '@/js/lineTypeLabels';

defineProps<{
  modelValue: number;
  disabled?: boolean;
}>();

defineEmits<{
  'update:modelValue': [value: number];
}>();

const options = [
  { value: LINE_TYPES.DIALOGUE, label: LINE_TYPE_LABELS[LINE_TYPES.DIALOGUE] },
  { value: LINE_TYPES.STAGE_DIRECTION, label: LINE_TYPE_LABELS[LINE_TYPES.STAGE_DIRECTION] },
  { value: LINE_TYPES.CUE_LINE, label: LINE_TYPE_LABELS[LINE_TYPES.CUE_LINE] },
  { value: LINE_TYPES.SPACING, label: LINE_TYPE_LABELS[LINE_TYPES.SPACING] },
];
</script>
