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
        <div class="add-line-item">
          <span class="add-line-swatch" aria-hidden="true">
            <b class="add-line-swatch-name">Name</b>Text
          </span>
          <span class="add-line-item-text">
            <strong>Dialogue</strong>
            <span class="add-line-item-desc">
              Someone speaking. Add more speakers if they talk together.
            </span>
          </span>
        </div>
      </BDropdownItem>
      <BDropdownItem @click="$emit('add', LINE_TYPES.STAGE_DIRECTION)">
        <div class="add-line-item">
          <span class="add-line-swatch" aria-hidden="true">
            <span class="add-line-swatch-direction-chip">Action</span>
          </span>
          <span class="add-line-item-text">
            <strong>Direction</strong>
            <span class="add-line-item-desc">An action or stage direction.</span>
          </span>
        </div>
      </BDropdownItem>
      <BDropdownItem @click="$emit('add', LINE_TYPES.CUE_LINE)">
        <div class="add-line-item">
          <span class="add-line-swatch" aria-hidden="true">
            <span class="add-line-swatch-cue-rule" />
          </span>
          <span class="add-line-item-text">
            <strong>Cue</strong>
            <span class="add-line-item-desc"
              >A marker where a cue sits. It has no text of its own.</span
            >
          </span>
        </div>
      </BDropdownItem>
      <BDropdownItem @click="$emit('add', LINE_TYPES.SPACING)">
        <div class="add-line-item">
          <span class="add-line-swatch add-line-swatch-gap" aria-hidden="true" />
          <span class="add-line-item-text">
            <strong>Gap</strong>
            <span class="add-line-item-desc">Blank space, to leave room in the live script.</span>
          </span>
        </div>
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
/* Resting height is deliberately thin — at a permanent 28px per line pair this
   ate a lot of vertical space across a whole page of lines for an action most
   lines never use. Expands back to the full interactive height on hover/focus
   (and stays expanded on touch, where hover never fires — see the opacity
   exception below for the same reasoning). */
.add-line-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 8px;
  padding: 0 12px;
  transition: height 0.15s ease;
}
.add-line-divider:hover,
.add-line-divider:focus-within {
  height: 28px;
}
@media (hover: none) {
  .add-line-divider {
    height: 28px;
  }
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
@media (prefers-reduced-motion: reduce) {
  .add-line-divider,
  .add-line-rule,
  .add-line-divider :deep(.add-line-toggle) {
    transition: none;
  }
}
.add-line-item {
  display: flex;
  align-items: center;
  gap: 10px;
}
/* A stylised preview of what each line type looks like once added, mirroring the
   design's icon column (a dashed rule for Cue, a diagonal stripe for Gap, etc.)
   rather than the plain bold-title-only item this replaced. */
.add-line-swatch {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 28px;
  overflow: hidden;
  border: 1px solid var(--bs-gray-700);
  border-radius: var(--bs-border-radius-sm);
  background: var(--bs-dark);
  font-size: 11px;
}
.add-line-swatch-name {
  margin-right: 3px;
  font-size: 9px;
}
.add-line-swatch-direction-chip {
  padding: 2px 6px;
  border-radius: 3px;
  background: darkslateblue;
  color: #fff;
  font-size: 10px;
  font-style: italic;
}
.add-line-swatch-cue-rule {
  width: 32px;
  border-top: 2px dashed var(--bs-gray-500);
}
.add-line-swatch-gap {
  background: repeating-linear-gradient(
    135deg,
    transparent 0 6px,
    rgba(255, 255, 255, 0.15) 6px 7px
  );
}
.add-line-item-text {
  display: flex;
  flex-direction: column;
}
.add-line-item-desc {
  display: block;
  font-size: 0.8125rem;
  color: var(--bs-secondary-color);
}
</style>
