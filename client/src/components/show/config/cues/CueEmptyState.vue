<template>
  <div class="cue-empty">
    <div class="cue-empty-panel">
      <template v-if="canEditShow">
        <h3>Add your cue types first</h3>
        <p class="cue-empty-caption">
          A cue type is a kind of cue, such as lighting or sound. Once you have one, you can place
          cues in the script.
        </p>
        <div class="cue-empty-suggestions" role="group" aria-label="Common cue types">
          <button
            v-for="suggestion in SUGGESTED_CUE_TYPES"
            :key="suggestion.prefix"
            type="button"
            class="suggestion-chip"
            @click="emit('new-type', suggestion)"
          >
            <span class="swatch" :style="{ background: suggestion.colour }" aria-hidden="true" />
            <b>{{ suggestion.prefix }}</b> {{ suggestion.description }}
          </button>
        </div>
        <p class="cue-empty-caption">
          Pick a common one to start with. You can change its prefix, name and colour before it is
          saved.
        </p>
        <div class="cue-empty-actions">
          <button type="button" class="btn btn-success" @click="emit('new-type', null)">
            New Cue Type
          </button>
          <button type="button" class="btn btn-outline-info" @click="emit('import')">
            Import from Another Show
          </button>
        </div>
      </template>
      <template v-else>
        <h5>No cue types yet</h5>
        <p class="cue-empty-caption">
          Ask someone who can edit this show to add them. Then you can place cues in the script.
        </p>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { SUGGESTED_CUE_TYPES, type SuggestedCueType } from '@/constants/cueTypeSuggestions';

defineProps<{ canEditShow: boolean }>();

const emit = defineEmits<{
  /** Open the new cue type form, pre-filled with a suggestion when one was chosen. */
  'new-type': [suggestion: SuggestedCueType | null];
  import: [];
}>();
</script>

<style scoped>
.cue-empty {
  max-width: 760px;
  margin: 0 auto;
}

.cue-empty-panel {
  margin-top: 32px;
  padding: 32px;
  border: 1px solid var(--bs-gray-700);
  border-radius: 0.25rem;
  text-align: center;
}

.cue-empty-caption {
  color: var(--bs-gray-500);
}

.cue-empty-suggestions {
  display: flex;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
  margin: 20px 0 8px;
}

.suggestion-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 12px;
  border: 2px solid var(--bs-gray-600);
  border-radius: 0.25rem;
  background: transparent;
  color: #fff;
}

.suggestion-chip:focus-visible {
  outline: 2px solid #fff;
  outline-offset: 2px;
}

.swatch {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 3px;
}

.cue-empty-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 24px;
}
</style>
