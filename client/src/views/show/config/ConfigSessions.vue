<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col>
        <h5>Sessions List</h5>
        <b-table id="acts-table" :items="this.SHOW_SESSIONS_LIST" :fields="sessionFields"
                 show-empty>
        </b-table>
      </b-col>
    </b-row>
    <b-row>
      <b-col>
        <b-button-group>
          <b-button variant="success" :disabled="CURRENT_SHOW_SESSION !== null">
            Start Session
          </b-button>
          <b-button variant="danger" :disabled="CURRENT_SHOW_SESSION === null">
            Stop Session
          </b-button>
        </b-button-group>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';

export default {
  name: 'ConfigSessions',
  data() {
    return {
      sessionFields: [
        { key: 'start_date_time', label: 'Start Date' },
        { key: 'end_date_time', label: 'End Date' },
        { key: 'run_time', label: 'Runtime' },
      ],
    };
  },
  async mounted() {
    await this.GET_SHOW_SESSION_DATA();
  },
  methods: {
    ...mapActions(['GET_SHOW_SESSION_DATA']),
  },
  computed: {
    ...mapGetters(['SHOW_SESSIONS_LIST', 'CURRENT_SHOW_SESSION']),
  },
};
</script>
