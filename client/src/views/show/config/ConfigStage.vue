<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col>
        <b-tabs content-class="mt-3">
          <b-tab title="Crew" active>
            <crew-list />
          </b-tab>
          <b-tab title="Scenery">
            <scenery-list />
          </b-tab>
          <b-tab title="Props">
            <props-list />
          </b-tab>
          <b-tab title="Stage Manager">
            <stage-manager />
          </b-tab>
          <b-tab title="Timeline">
            <b-tabs content-class="mt-2">
              <b-tab title="Props & Scenery" active>
                <stage-timeline />
              </b-tab>
              <b-tab title="Crew" lazy>
                <crew-timeline />
              </b-tab>
            </b-tabs>
          </b-tab>
        </b-tabs>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import CrewList from '@/vue_components/show/config/stage/CrewList.vue';
import SceneryList from '@/vue_components/show/config/stage/SceneryList.vue';
import PropsList from '@/vue_components/show/config/stage/PropsList.vue';
import StageManager from '@/vue_components/show/config/stage/StageManager.vue';
import StageTimeline from '@/vue_components/show/config/stage/StageTimeline.vue';
import CrewTimeline from '@/vue_components/show/config/stage/CrewTimeline.vue';

export default {
  name: 'ConfigCrew',
  components: {
    StageManager,
    PropsList,
    SceneryList,
    CrewList,
    StageTimeline,
    CrewTimeline,
  },
};
</script>
