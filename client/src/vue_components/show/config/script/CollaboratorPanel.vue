<template>
  <div v-if="collaborators.length > 0" class="collaborator-panel">
    <span class="collaborator-label">{{ collaborators.length }} in room</span>
    <span
      v-for="(collab, idx) in collaborators"
      :key="idx"
      class="collaborator-chip"
      :title="chipTitle(collab)"
    >
      <span class="collaborator-dot" :style="{ backgroundColor: userColor(collab.user_id) }" />
      {{ collab.username }}
      <b-badge :variant="collab.role === 'editor' ? 'success' : 'info'" pill>
        {{ collab.role }}
      </b-badge>
    </span>
  </div>
</template>

<script>
import { collabColor } from '@/utils/collabColors';

export default {
  name: 'CollaboratorPanel',
  props: {
    collaborators: {
      type: Array,
      required: true,
    },
    awarenessStates: {
      type: Object,
      default: () => ({}),
    },
  },
  methods: {
    userColor(userId) {
      return collabColor(userId);
    },
    chipTitle(collab) {
      const awareness = this.awarenessStates[collab.user_id];
      if (awareness && awareness.page != null) {
        if (awareness.lineIndex != null) {
          return `${collab.username} — editing page ${awareness.page}, line ${awareness.lineIndex + 1}`;
        }
        return `${collab.username} — viewing page ${awareness.page}`;
      }
      return collab.username;
    },
  },
};
</script>

<style scoped>
.collaborator-panel {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.collaborator-label {
  font-size: 0.8rem;
  opacity: 0.7;
  white-space: nowrap;
}

.collaborator-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.15rem 0.5rem;
  border-radius: 1rem;
  font-size: 0.8rem;
  background: rgba(255, 255, 255, 0.1);
  white-space: nowrap;
}

.collaborator-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
</style>
