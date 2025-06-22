<template>
  <b-container
    class="mx-0"
    fluid
  >
    <b-row>
      <b-col>
        <b-tabs content-class="mt-3">
          <b-tab
            title="Crew"
            active
          >
            <crew-list />
          </b-tab>
          <b-tab title="Scenery">
            <scenery-list />
          </b-tab>
          <b-tab title="Props">
            <props-list />
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

export default {
  name: 'ConfigCrew',
  components: { PropsList, SceneryList, CrewList },
};
</script>
