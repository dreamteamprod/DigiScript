<template>
  <BRow id="current-cue-footer" class="current-cue-footer">
    <BCol class="d-flex flex-wrap align-items-center gap-2">
      <b>Current Cues:</b>
      <BButtonGroup v-if="currentCues.length > 0" class="flex-wrap">
        <BButton
          v-for="cue in currentCues"
          :key="cue.id"
          class="cue-button"
          :style="{
            backgroundColor: cueBackgroundColour(cue),
            color: contrastColor(cueBackgroundColour(cue)),
          }"
        >
          {{ cueLabel(cue) }}
        </BButton>
      </BButtonGroup>
      <span v-else class="text-muted">No cues called yet</span>
    </BCol>
  </BRow>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useCueDisplay } from '@/composables/useCueDisplay';
import { useScriptStore } from '@/stores/script';
import { useShowStore } from '@/stores/show';
import type { Cue } from '@/types/api/cues';

const props = defineProps<{
  currentPage: number;
  currentLineOnPage: number;
}>();

const scriptStore = useScriptStore();
const showStore = useShowStore();
const { cueLabel, cueBackgroundColour, contrastColor } = useCueDisplay();

const currentCues = computed<Cue[]>(() => {
  const lastPerType = scriptStore.lastCuePerTypeAt(props.currentPage, props.currentLineOnPage);
  return showStore.cueTypes
    .map((cueType) => lastPerType[cueType.id])
    .filter((cue): cue is Cue => cue != null);
});
</script>

<style scoped>
.current-cue-footer {
  border-top: 0.1rem solid #3498db;
  padding-top: 0.3rem;
  padding-bottom: 0.3rem;
  margin: 0;
}

.cue-button {
  padding: 0.2rem;
}
</style>
