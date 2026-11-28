<template>
  <div class="cue-toolbar" :style="{ top: `${navbarHeight}px` }">
    <div class="cue-toolbar-row">
      <div>
        <button type="button" class="btn btn-success" @click="emit('go-to-page')">
          Go to Page
        </button>
      </div>
      <div class="cue-toolbar-pages">
        <button
          type="button"
          class="btn btn-success"
          :disabled="currentPage === 1 || busy"
          @click="emit('prev')"
        >
          Prev Page
        </button>
        <span class="cue-toolbar-current">Current Page: {{ currentPage }}</span>
        <button
          type="button"
          class="btn btn-success"
          :disabled="currentPage >= maxPage || busy"
          @click="emit('next')"
        >
          Next Page
        </button>
      </div>
      <CueFindBox ref="findBox" @jump="(match) => emit('jump', match)" />
    </div>

    <div class="cue-toolbar-filter">
      <span class="cue-toolbar-caption">Show cues</span>
      <fieldset class="filter-group" aria-label="Show cue types">
        <button
          type="button"
          class="filter-btn"
          :class="{ 'filter-on': filterTypeId == null }"
          :aria-pressed="filterTypeId == null"
          @click="emit('update:filterTypeId', null)"
        >
          All
        </button>
        <button
          v-for="type in cueTypes"
          :key="type.id"
          type="button"
          class="filter-btn"
          :class="{ 'filter-on': filterTypeId === type.id }"
          :aria-pressed="filterTypeId === type.id"
          @click="emit('update:filterTypeId', type.id)"
        >
          <span class="swatch" :style="{ background: typeColour(type.id) }" aria-hidden="true" />
          {{ type.prefix }}
        </button>
      </fieldset>
      <span class="flex-fill" />
      <span class="cue-toolbar-caption">Cue changes save straight away</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import CueFindBox from '@/components/show/config/cues/CueFindBox.vue';
import { useCueDisplay } from '@/composables/useCueDisplay';
import type { FindMatch } from '@/js/cueFind';
import type { CueType } from '@/types/api/cues';

defineProps<{
  currentPage: number;
  maxPage: number;
  /** A page is loading. */
  busy: boolean;
  cueTypes: CueType[];
  filterTypeId: number | null;
}>();

const emit = defineEmits<{
  'go-to-page': [];
  prev: [];
  next: [];
  'update:filterTypeId': [id: number | null];
  jump: [match: FindMatch];
}>();

const { typeColour } = useCueDisplay();
const findBox = ref<InstanceType<typeof CueFindBox> | null>(null);

// Sit just under the app's navbar, like the script editor's header does.
const navbarHeight = ref(56);
onMounted(() => {
  const navbar = document.querySelector('.navbar');
  navbarHeight.value = navbar ? (navbar as HTMLElement).offsetHeight : 56;
});

defineExpose({ focusFind: () => findBox.value?.focus() });
</script>

<style scoped>
.cue-toolbar {
  text-align: left;
  position: sticky;
  z-index: 100;
  padding: 10px 0;
  background: var(--body-background, var(--bs-body-bg));
  /* A box-shadow, not a border: a border on a sticky element paints over popovers
     (the find results) in Chromium. */
  box-shadow: 0 1px 0 0 var(--bs-gray-700);
}

.cue-toolbar-row {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 12px;
}

.cue-toolbar-pages {
  display: flex;
  align-items: center;
  gap: 16px;
}

.cue-toolbar-current {
  min-width: 130px;
  text-align: center;
}

.cue-toolbar-filter {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding-top: 10px;
}

.cue-toolbar-caption {
  color: var(--bs-gray-500);
  font-size: 0.8125rem;
}

.filter-group {
  display: inline-flex;
  flex-wrap: wrap;
}

.filter-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 34px;
  padding: 0 14px;
  margin-left: -1px;
  border: 1px solid var(--bs-gray-600);
  background: transparent;
  color: #fff;
  font-size: 0.875rem;
}

.filter-btn:first-child {
  margin-left: 0;
  border-radius: 0.25rem 0 0 0.25rem;
}

.filter-btn:last-child {
  border-radius: 0 0.25rem 0.25rem 0;
}

.filter-btn.filter-on {
  background: var(--bs-primary);
  border-color: var(--bs-primary);
}

.filter-btn:focus-visible {
  outline: 2px solid #fff;
  outline-offset: 2px;
  position: relative;
}

.swatch {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 3px;
}

.flex-fill {
  flex: 1;
}

@media (max-width: 900px) {
  .cue-toolbar-row {
    grid-template-columns: 1fr;
    justify-items: start;
  }
}
</style>
