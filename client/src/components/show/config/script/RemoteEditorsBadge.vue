<template>
  <BCol
    v-if="names.length > 0"
    cols="12"
    class="remote-editors"
    :class="`remote-editors-${variant}`"
  >
    <span class="remote-editors-avatars">
      <PresenceAvatar
        v-for="name in names"
        :key="name"
        size="sm"
        :initials="presenceInitials(name)"
        :color="presenceColor(name)"
        :badge="'editing'"
        :title="`${name} is editing this line`"
      />
    </span>
    <span class="remote-editors-label">{{ label }}</span>
  </BCol>
</template>

<script setup lang="ts">
/**
 * Phase 4 Step C: the "someone else has this line open" indicator, shared by
 * `ScriptLineViewer` (the read-only view) and `CollabScriptLineEditor` (so a
 * concurrent co-editor also sees it) — `cols="12"` so it wraps onto its own line
 * within the parent's existing `<BRow>` rather than needing a second row element.
 *
 * `variant` only changes the label wording/alignment: `'row'` (the default, used
 * from `ScriptLineViewer`) reads as a plain name tag above the line; `'editor'`
 * (used from `CollabScriptLineEditor`, where *you* also have the line open) reads
 * as "X is also editing this line" and sits to the right, matching the design.
 */
import { computed } from 'vue';
import { presenceInitials, presenceColor } from '@/js/presenceUtils';
import PresenceAvatar from './PresenceAvatar.vue';

const props = withDefaults(
  defineProps<{
    names: string[];
    variant?: 'row' | 'editor';
  }>(),
  { variant: 'row' }
);

// Collapses to "a" / "a, b" / "a +N" — matches the design's close-up reference for
// three or more editors on the same line, where listing every name would crowd out
// the line text itself.
const collapsedNames = computed<string>(() => {
  const [first, second, ...rest] = props.names;
  if (props.names.length <= 1) return first ?? '';
  if (props.names.length === 2) return `${first}, ${second}`;
  return `${first} +${rest.length + 1}`;
});

const label = computed<string>(() => {
  if (props.variant === 'row') return collapsedNames.value;
  const verb = props.names.length > 1 ? 'are' : 'is';
  return `${collapsedNames.value} ${verb} also editing this line`;
});
</script>

<style scoped>
.remote-editors {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0.25rem 0;
  font-size: 0.8125rem;
  font-weight: 700;
}

.remote-editors-row {
  justify-content: flex-start;
}

.remote-editors-editor {
  justify-content: flex-end;
  color: var(--bs-secondary-color);
}

.remote-editors-avatars {
  display: flex;
}

.remote-editors-avatars > * + * {
  margin-left: -8px;
}
</style>
