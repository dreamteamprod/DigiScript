<template>
  <BCol v-if="names.length > 0" cols="12" class="remote-editors">
    <BBadge
      v-for="name in names"
      :key="name"
      variant="warning"
      pill
      class="me-1"
      :title="`${name} is editing this line`"
    >
      {{ name }} ✎
    </BBadge>
  </BCol>
</template>

<script setup lang="ts">
/**
 * Phase 4 Step C: the "someone else has this line open" badge row, shared by
 * `ScriptLineViewer` (the read-only view) and `CollabScriptLineEditor` (so a
 * concurrent co-editor also sees it) — `cols="12"` so it wraps onto its own line
 * within the parent's existing `<BRow>` rather than needing a second row element.
 */
defineProps<{
  names: string[];
}>();
</script>

<style scoped>
.remote-editors {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  margin: 0.25rem 0;
}
</style>
