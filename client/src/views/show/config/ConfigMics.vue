<template>
  <b-container
    class="mx-0"
    fluid
  >
    <b-row>
      <b-col>
        <b-tabs content-class="mt-3">
          <b-tab
            title="Mics"
            active
          >
            <mic-list />
          </b-tab>
          <b-tab
            title="Allocations"
          >
            <p>Allocations</p>
          </b-tab>
        </b-tabs>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { mapActions } from 'vuex';
import MicList from '@/vue_components/show/config/mics/MicList.vue';

export default {
  name: 'ConfigMics',
  components: { MicList },
  async mounted() {
    await this.GET_SCENE_LIST();
    await this.GET_ACT_LIST();
    await this.GET_MICROPHONE_LIST();
  },
  methods: {
    ...mapActions(['GET_SCENE_LIST', 'GET_ACT_LIST', 'GET_MICROPHONE_LIST']),
  },
};
</script>
