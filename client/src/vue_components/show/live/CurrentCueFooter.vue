<template>
  <b-row id="current-cue-footer" class="current-cue-footer">
    <b-col class="d-flex flex-wrap align-items-center" style="gap: 0.5rem">
      <b>Current Cues:</b>
      <b-button-group v-if="currentCues.length > 0" class="flex-wrap">
        <b-button
          v-for="cue in currentCues"
          :key="cue.id"
          class="cue-button"
          :style="{
            backgroundColor: cueBackgroundColour(cue),
            color: contrastColor({ bgColor: cueBackgroundColour(cue) }),
          }"
        >
          {{ cueLabel(cue) }}
        </b-button>
      </b-button-group>
      <span v-else class="text-muted">No cues called yet</span>
    </b-col>
  </b-row>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapGetters } from 'vuex';
import cueDisplayMixin from '@/mixins/cueDisplayMixin';
import type { Cue } from '@/types/api/cues';

export default defineComponent({
  name: 'CurrentCueFooter',
  mixins: [cueDisplayMixin],
  props: {
    currentPage: {
      required: true,
      type: Number,
    },
    currentLineOnPage: {
      required: true,
      type: Number,
    },
    cueTypes: {
      required: true,
      type: Array,
    },
  },
  computed: {
    ...mapGetters(['LAST_CUE_PER_TYPE_AT']),
    currentCues(): Cue[] {
      const lastPerType = (this as any).LAST_CUE_PER_TYPE_AT(
        this.currentPage,
        this.currentLineOnPage
      );
      return (this.cueTypes as any[])
        .map((cueType) => lastPerType[cueType.id])
        .filter((cue): cue is Cue => cue != null);
    },
  },
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
