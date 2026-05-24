<template>
  <BContainer class="mx-0" fluid>
    <BRow>
      <BCol>
        <BTabs content-class="mt-3">
          <BTab title="Acts" active>
            <ConfigActs />
          </BTab>
          <BTab title="Scenes">
            <ConfigScenes />
          </BTab>
        </BTabs>
      </BCol>
    </BRow>
  </BContainer>
</template>

<script setup lang="ts">
import ConfigActs from '@/components/show/config/acts_and_scenes/ConfigActs.vue';
import ConfigScenes from '@/components/show/config/acts_and_scenes/ConfigScenes.vue';
</script>
