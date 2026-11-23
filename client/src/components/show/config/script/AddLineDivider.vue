<template>
  <div class="add-line-divider">
    <span class="add-line-rule" aria-hidden="true" />
    <BDropdown
      size="sm"
      variant="success"
      toggle-class="add-line-toggle"
      :aria-label="`Add a line after line ${lineNumber}`"
    >
      <template #button-content>+ Add Line Here</template>
      <BDropdownHeader>What do you want to add?</BDropdownHeader>
      <BDropdownItem @click="$emit('add', LINE_TYPES.DIALOGUE)">
        <strong>Dialogue</strong>
        <span class="add-line-item-desc">
          Someone speaking. Add more speakers if they talk together.
        </span>
      </BDropdownItem>
      <BDropdownItem @click="$emit('add', LINE_TYPES.STAGE_DIRECTION)">
        <strong>Direction</strong>
        <span class="add-line-item-desc">An action or stage direction.</span>
      </BDropdownItem>
      <BDropdownItem @click="$emit('add', LINE_TYPES.CUE_LINE)">
        <strong>Cue</strong>
        <span class="add-line-item-desc"
          >A marker where a cue sits. It has no text of its own.</span
        >
      </BDropdownItem>
      <BDropdownItem @click="$emit('add', LINE_TYPES.SPACING)">
        <strong>Gap</strong>
        <span class="add-line-item-desc">Blank space, to leave room in the live script.</span>
      </BDropdownItem>
    </BDropdown>
    <span class="add-line-rule" aria-hidden="true" />
  </div>
</template>

<script setup lang="ts">
/**
 * Design E's "+ Add Line Here" divider between every pair of lines, replacing the
 * per-row "Edit ▾" dropdown's four Insert items. "Start New Scene Here" / "Start New
 * Act Here" (the other two items the design's menu shows) are not implemented yet —
 * see SCRIPT_EDITOR_REDESIGN_E.md — so this menu only offers the four line types.
 */
import { LINE_TYPES } from '@/constants/lineTypes';

defineProps<{
  /** The line number immediately above this divider, for the a11y label only. */
  lineNumber: number;
}>();

defineEmits<{
  add: [lineType: number];
}>();
</script>

<style scoped>
.add-line-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 28px;
  padding: 0 12px;
}
.add-line-rule {
  flex: 1;
  height: 2px;
  background: transparent;
  transition: background-color 0.15s ease;
}
.add-line-divider:hover .add-line-rule,
.add-line-divider:focus-within .add-line-rule {
  background: var(--bs-success);
}
.add-line-divider :deep(.add-line-toggle) {
  opacity: 0;
  transition: opacity 0.15s ease;
}
.add-line-divider:hover :deep(.add-line-toggle),
.add-line-divider:focus-within :deep(.add-line-toggle) {
  opacity: 1;
}
@media (hover: none) {
  .add-line-divider :deep(.add-line-toggle) {
    opacity: 1;
  }
}
.add-line-item-desc {
  display: block;
  font-size: 0.8125rem;
  color: var(--bs-secondary-color);
}
</style>
