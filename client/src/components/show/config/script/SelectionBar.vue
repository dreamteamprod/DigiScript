<template>
  <div class="selection-bar" role="toolbar" aria-label="Selected lines">
    <strong>{{ count }} line{{ count === 1 ? '' : 's' }} selected</strong>
    <span class="selection-bar-range text-muted">{{ rangeLabel }}</span>
    <span class="selection-bar-divider" aria-hidden="true" />
    <BButton size="sm" variant="primary" @click="$emit('set-character')">
      Set Character or Group
    </BButton>
    <BButton size="sm" variant="primary" @click="$emit('move-to-scene')">Move to Scene</BButton>
    <BButton size="sm" variant="outline-danger" @click="$emit('delete')">
      Delete {{ count }} Line{{ count === 1 ? '' : 's' }}
    </BButton>
    <span class="flex-grow-1" />
    <BButton size="sm" variant="outline-secondary" @click="$emit('clear')">
      Clear Selection
    </BButton>
  </div>
</template>

<script setup lang="ts">
/** Design E's selection bar, replacing the old "Bulk Edit" mode toggle + Start/End
 * row buttons. Shown whenever at least one line is ticked; the parent owns the
 * selection range itself (reusing its existing bulk-edit start/end state) and just
 * passes the derived count/label down. */
defineProps<{
  count: number;
  rangeLabel: string;
}>();

defineEmits<{
  'set-character': [];
  'move-to-scene': [];
  delete: [];
  clear: [];
}>();
</script>

<style scoped>
.selection-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  margin: 8px 0;
  background: var(--bs-tertiary-bg);
  border: 1px solid var(--bs-success);
  border-radius: var(--bs-border-radius);
  flex-wrap: wrap;
}
.selection-bar-divider {
  width: 1px;
  height: 22px;
  background: var(--bs-border-color);
  margin: 0 2px;
}
</style>
