<template>
  <BContainer class="mx-0" fluid>
    <BRow>
      <BCol>
        <BTabs content-class="mt-3">
          <BTab title="Crew" active><CrewList /></BTab>
          <BTab title="Scenery"><SceneryList /></BTab>
          <BTab title="Props"><PropsList /></BTab>
          <BTab title="Stage Manager"><StageManager /></BTab>
          <BTab title="Timeline">
            <BTabs content-class="mt-2">
              <BTab title="Props &amp; Scenery" active><StageTimeline /></BTab>
              <BTab title="Crew" lazy><CrewTimeline /></BTab>
            </BTabs>
          </BTab>
        </BTabs>
      </BCol>
    </BRow>
  </BContainer>
</template>

<script setup lang="ts">
import CrewList from '@/components/show/config/stage/CrewList.vue';
import SceneryList from '@/components/show/config/stage/SceneryList.vue';
import PropsList from '@/components/show/config/stage/PropsList.vue';
import StageManager from '@/components/show/config/stage/StageManager.vue';
import StageTimeline from '@/components/show/config/stage/StageTimeline.vue';
import CrewTimeline from '@/components/show/config/stage/CrewTimeline.vue';
</script>
