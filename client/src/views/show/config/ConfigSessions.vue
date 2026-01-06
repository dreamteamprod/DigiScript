<template>
  <b-container
    class="mx-0"
    fluid
  >
    <b-row>
      <b-col v-if="loaded">
        <b-tabs content-class="mt-3">
          <b-tab
            title="Sessions"
            active
          >
            <session-list />
          </b-tab>
          <b-tab title="Tags">
            <session-tag-list />
          </b-tab>
        </b-tabs>
      </b-col>
      <b-col v-else>
        <div
          class="text-center center-spinner"
        >
          <b-spinner
            style="width: 10rem; height: 10rem;"
            variant="info"
          />
        </div>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { mapActions } from 'vuex';
import SessionList from '@/vue_components/show/config/sessions/SessionList.vue';
import SessionTagList from '@/vue_components/show/config/sessions/SessionTagList.vue';

export default {
  name: 'ConfigSessions',
  components: { SessionTagList, SessionList },
  data() {
    return {
      loaded: false,
    };
  },
  async mounted() {
    await this.GET_SHOW_SESSION_DATA();
    await this.GET_SESSION_TAGS();
    this.loaded = true;
  },
  methods: {
    ...mapActions(['GET_SHOW_SESSION_DATA', 'GET_SESSION_TAGS']),
  },
};
</script>
