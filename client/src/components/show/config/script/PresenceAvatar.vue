<template>
  <span
    class="presence-avatar"
    :class="{ 'presence-avatar-sm': size === 'sm' }"
    :style="{ background: color }"
    :title="title"
  >
    {{ initials }}
    <span v-if="badge" class="presence-avatar-badge" :class="`presence-avatar-badge-${badge}`">
      <IMdiPencil v-if="badge === 'editing'" aria-hidden="true" />
      <IMdiContentCut v-else aria-hidden="true" />
    </span>
  </span>
</template>

<script setup lang="ts">
/**
 * One room member's avatar: initials on a colour-coded circle, with an optional
 * small status badge (a pencil for "editing", scissors for "cutting") in the
 * corner. `color` and `initials` are left for the caller to compute (via
 * `@/js/presenceUtils`) rather than taking a raw username, since the room
 * popover needs the same colour/initials pair for a plain `<span>` avatar list
 * too (see `CollabScriptEditor.vue`'s `presenceEntries`).
 */
withDefaults(
  defineProps<{
    initials: string;
    color: string;
    title: string;
    badge?: 'editing' | 'cutting' | null;
    size?: 'sm' | 'md';
  }>(),
  { badge: null, size: 'md' }
);
</script>

<style scoped>
.presence-avatar {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  color: #111;
  font-size: 12px;
  font-weight: 800;
  line-height: 1;
  box-shadow: 0 0 0 2px var(--body-background, #fff);
}

.presence-avatar-sm {
  width: 24px;
  height: 24px;
  font-size: 10px;
}

.presence-avatar-badge {
  position: absolute;
  right: -4px;
  bottom: -4px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 15px;
  height: 15px;
  border-radius: 50%;
  box-shadow: 0 0 0 1.5px var(--body-background, #fff);
  color: #111;
  font-size: 9px;
}

.presence-avatar-sm .presence-avatar-badge {
  width: 13px;
  height: 13px;
}

.presence-avatar-badge-editing {
  background: var(--bs-warning);
}

.presence-avatar-badge-cutting {
  background: var(--bs-info);
}
</style>
