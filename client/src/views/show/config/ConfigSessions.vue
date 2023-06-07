<template>
  <b-container
    class="mx-0"
    fluid
  >
    <b-row>
      <b-col>
        <h5>Sessions List</h5>
        <b-table
          id="acts-table"
          :items="SHOW_SESSIONS_LIST"
          :fields="sessionFields"
          show-empty
        >
          <template #cell(run_time)="data">
            <p v-if="data.item.end_date_time">
              {{ runTimeCalc(data.item.start_date_time, data.item.end_date_time) }}
            </p>
          </template>
        </b-table>
      </b-col>
    </b-row>
    <b-row>
      <b-col>
        <b-button-group>
          <b-button
            variant="success"
            :disabled="CURRENT_SHOW_SESSION !== null || startingSession"
            @click.stop="startSession"
          >
            Start Session
          </b-button>
          <b-button
            variant="danger"
            :disabled="CURRENT_SHOW_SESSION === null || stoppingSession"
            @click.stop="stopSession"
          >
            Stop Session
          </b-button>
        </b-button-group>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';
import log from 'loglevel';

import { makeURL, msToTimer } from '@/js/utils';

export default {
  name: 'ConfigSessions',
  data() {
    return {
      sessionFields: [
        { key: 'start_date_time', label: 'Start Date' },
        { key: 'end_date_time', label: 'End Date' },
        { key: 'run_time', label: 'Runtime' },
      ],
      startingSession: false,
      stoppingSession: false,
    };
  },
  async mounted() {
    await this.GET_SHOW_SESSION_DATA();
  },
  methods: {
    async startSession() {
      if (this.INTERNAL_UUID == null) {
        this.$toast.error('Unable to start new show session');
        return;
      }
      this.startingSession = true;
      const response = await fetch(`${makeURL('/api/v1/show/sessions/start')}`, {
        method: 'POST',
        body: JSON.stringify({
          session_id: this.INTERNAL_UUID,
        }),
      });
      if (response.ok) {
        this.$toast.success('Started new show session');
      } else {
        log.error('Unable to start new show session');
        this.$toast.error('Unable to start new show session');
      }
      this.startingSession = false;
    },
    async stopSession() {
      this.stoppingSession = true;
      const response = await fetch(`${makeURL('/api/v1/show/sessions/stop')}`, {
        method: 'POST',
      });
      if (response.ok) {
        this.$toast.success('Stopped show session');
      } else {
        log.error('Unable to stop show session');
        this.$toast.error('Unable to stop show session');
      }
      this.stoppingSession = false;
    },
    runTimeCalc(start, end) {
      const startDate = Date.parse(start);
      const endDate = Date.parse(end);
      const diff = endDate - startDate;
      return msToTimer(diff);
    },
    ...mapActions(['GET_SHOW_SESSION_DATA']),
  },
  computed: {
    ...mapGetters(['SHOW_SESSIONS_LIST', 'CURRENT_SHOW_SESSION', 'INTERNAL_UUID']),
  },
};
</script>
