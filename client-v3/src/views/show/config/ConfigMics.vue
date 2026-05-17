<template>
  <BContainer class="mx-0" fluid>
    <BRow>
      <BCol>
        <BTabs content-class="mt-3" lazy>
          <BTab title="Mics" active>
            <MicList />
          </BTab>
          <BTab title="Allocations">
            <MicAllocations />
          </BTab>
          <BTab title="Timeline">
            <MicTimeline :loading="!loaded" />
          </BTab>
          <BTab title="Density">
            <SceneDensityHeatmap :loading="!loaded" />
          </BTab>
          <BTab title="Availability">
            <ResourceAvailability :loading="!loaded" />
          </BTab>
        </BTabs>
      </BCol>
    </BRow>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useShowStore } from '@/stores/show';
import MicList from '@/components/show/config/mics/MicList.vue';
import MicAllocations from '@/components/show/config/mics/MicAllocations.vue';
import MicTimeline from '@/components/show/config/mics/MicTimeline.vue';
import SceneDensityHeatmap from '@/components/show/config/mics/SceneDensityHeatmap.vue';
import ResourceAvailability from '@/components/show/config/mics/ResourceAvailability.vue';

const showStore = useShowStore();
const loaded = ref(false);

onMounted(async () => {
  await Promise.all([
    showStore.getSceneList(),
    showStore.getActList(),
    showStore.getCharacterList(),
    showStore.getCastList(),
    showStore.getMicrophoneList(),
    showStore.getMicAllocations(),
  ]);
  loaded.value = true;
});
</script>
