<template>
  <b-container class="mx-0" fluid :style="{ 'padding-right': stageManagerMode ? '0px' : '15px' }">
    <b-row
      class="session-header"
      style="padding-top: 0.1rem; padding-bottom: 0.1rem"
      :style="{ 'padding-right': stageManagerMode ? '15px' : '0px' }"
    >
      <b-col cols="4" style="text-align: left">
        <b v-if="isScriptFollowing"> {{ CURRENT_SHOW.name }} - Following </b>
        <b v-else-if="isScriptLeader"> {{ CURRENT_SHOW.name }} - Leading </b>
        <b v-else> {{ CURRENT_SHOW.name }} - Manual </b>
      </b-col>
      <b-col cols="4">
        <b> Page {{ currentPage }} </b>
      </b-col>
      <b-col cols="4" style="text-align: right">
        <b> Elapsed Time: {{ msToTimerString(elapsedTime) }} </b>
      </b-col>
    </b-row>
    <b-overlay
      :show="CURRENT_SHOW_INTERVAL != null"
      rounded="sm"
      variant="secondary"
      @shown="onOverlayShown"
      @hidden="onOverlayHidden"
    >
      <template #overlay>
        <div ref="interval-overlay" class="text-center">
          <b-container class="mx-0" fluid>
            <b-row>
              <b-col class="d-flex align-items-center justify-content-center">
                <h3>
                  {{ intervalOverlayHeading }} - Interval in Progress
                  <b-icon icon="stopwatch" animation="cylon" />
                </h3>
              </b-col>
            </b-row>
            <b-row v-if="intervalTimer != null">
              <b-col class="d-flex align-items-center justify-content-center">
                <h1 style="margin-top: 0.5rem">
                  <!-- eslint-disable-next-line max-len -->
                  <span :style="intervalTimerStyle">{{ intervalTimerValues[0] }}</span
                  >:<span :style="intervalTimerStyle">{{ intervalTimerValues[1] }}</span
                  >:<span :style="intervalTimerStyle">{{ intervalTimerValues[2] }}</span>
                </h1>
              </b-col>
            </b-row>
            <b-row style="margin-top: 0.5rem">
              <b-col class="d-flex align-items-center justify-content-center">
                <b-button v-if="isScriptLeader" variant="primary" @click.stop="stopInterval">
                  Stop Interval
                </b-button>
              </b-col>
            </b-row>
          </b-container>
        </div>
      </template>
      <split-panes class="default-theme">
        <split-pane>
          <script-view-pane
            ref="scriptPane"
            :is-script-following="isScriptFollowing"
            :is-script-leader="isScriptLeader"
            :session-follow-data="SESSION_FOLLOW_DATA"
            :initial-line-ref="CURRENT_SHOW_SESSION?.latest_line_ref"
            :interval-active="CURRENT_SHOW_INTERVAL != null"
            :script-mode="CURRENT_SHOW?.script_mode || 1"
            :stage-manager-mode="stageManagerMode"
            @page-change="currentPage = $event"
          />
        </split-pane>
        <split-pane v-if="stageManagerMode" :size="20">
          <stage-manager-pane :session-follow-data="SESSION_FOLLOW_DATA" />
        </split-pane>
      </split-panes>
    </b-overlay>
  </b-container>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';

import { formatTimerParts, msToTimerParts, msToTimerString } from '@/js/utils';
import ScriptViewPane from '@/vue_components/show/live/ScriptViewPane.vue';
import StageManagerPane from '@/vue_components/show/live/StageManagerPane.vue';

export default {
  name: 'ShowLiveView',
  components: {
    ScriptViewPane,
    StageManagerPane,
  },
  data() {
    return {
      // Session timing
      elapsedTime: 0,
      elapsedTimer: null,
      startTime: null,
      loadedSessionData: false,

      // Page display (updated via event from ScriptViewPane)
      currentPage: 1,

      // Interval display state
      intervalTimer: null,
      intervalStartDate: null,
      isIntervalLong: false,
      intervalTimerValues: [0, 0, 0],
      intervalRemainingTime: 0,
    };
  },
  computed: {
    isScriptFollowing() {
      if (this.loadedSessionData) {
        return this.CURRENT_SHOW_SESSION.client_internal_id != null && !this.isScriptLeader;
      }
      return false;
    },
    isScriptLeader() {
      if (this.loadedSessionData) {
        return this.CURRENT_SHOW_SESSION.client_internal_id === this.INTERNAL_UUID;
      }
      return false;
    },
    intervalOverlayHeading() {
      if (this.CURRENT_SHOW_INTERVAL == null || this.ACT_LIST.length === 0) {
        return '';
      }
      return this.ACT_LIST.find((act) => act.id === this.CURRENT_SHOW_INTERVAL.act_id).name;
    },
    intervalTimerColour() {
      if (this.isIntervalLong) {
        return '#cc0000';
      }
      const intervalProgress =
        Math.abs(this.intervalRemainingTime) / (this.CURRENT_SHOW_INTERVAL.initial_length * 1000);
      if (intervalProgress > 0.25) {
        return '#00cc00';
      }
      return '#d76113';
    },
    intervalTimerStyle() {
      return {
        margin: '.5rem',
        'border-radius': '3px',
        color: '#ffffff',
        'background-color': this.intervalTimerColour,
        padding: '.25rem',
      };
    },
    ...mapGetters([
      'CURRENT_SHOW_SESSION',
      'ACT_LIST',
      'CURRENT_SHOW',
      'INTERNAL_UUID',
      'SESSION_FOLLOW_DATA',
      'CURRENT_SHOW_INTERVAL',
    ]),
    ...mapGetters({
      stageManagerMode: 'STAGE_MANAGER_MODE',
    }),
  },
  watch: {
    CURRENT_SHOW_INTERVAL() {
      this.setupIntervalTimer();
    },
  },
  async mounted() {
    await Promise.all([this.GET_SHOW_SESSION_DATA(), this.GET_ACT_LIST()]);
    this.loadedSessionData = true;

    if (this.CURRENT_SHOW_INTERVAL != null) {
      this.setupIntervalTimer();
    }

    // Setup elapsed time tracking
    this.updateElapsedTime();
    this.startTime = this.createDateAsUTC(
      new Date(this.CURRENT_SHOW_SESSION.start_date_time.replace(' ', 'T'))
    );
    this.elapsedTimer = setInterval(this.updateElapsedTime, 1000);
  },
  destroyed() {
    clearInterval(this.elapsedTimer);
  },
  methods: {
    msToTimerString,
    createDateAsUTC(date) {
      return new Date(
        Date.UTC(
          date.getFullYear(),
          date.getMonth(),
          date.getDate(),
          date.getHours(),
          date.getMinutes(),
          date.getSeconds()
        )
      );
    },
    updateElapsedTime() {
      if (this.startTime != null) {
        this.elapsedTime = Date.now() - this.startTime;
      }
    },
    stopInterval() {
      this.$socket.sendObj({
        OP: 'END_INTERVAL',
        DATA: {},
      });
      this.$toast.success('Interval stopped!');
    },
    onOverlayShown() {
      this.$refs['interval-overlay'].focus();
    },
    onOverlayHidden() {
      this.$refs.scriptPane?.focusScript();
    },
    setupIntervalTimer() {
      clearInterval(this.intervalTimer);
      this.intervalTimer = null;
      this.intervalTimerValues = [0, 0, 0];
      this.isIntervalLong = false;
      this.intervalRemainingTime = 0;
      if (this.CURRENT_SHOW_INTERVAL != null) {
        this.intervalStartDate = this.createDateAsUTC(
          new Date(this.CURRENT_SHOW_INTERVAL.start_datetime.replace(' ', 'T'))
        );
        this.updateIntervalTimer();
        this.intervalTimer = setInterval(this.updateIntervalTimer, 500);
      }
    },
    updateIntervalTimer() {
      if (this.intervalStartDate != null) {
        const intervalElapsedTime = Date.now() - this.intervalStartDate;
        this.intervalRemainingTime =
          this.CURRENT_SHOW_INTERVAL.initial_length * 1000 - intervalElapsedTime;
        if (this.intervalRemainingTime < 0) {
          this.isIntervalLong = true;
        }
        this.intervalTimerValues = formatTimerParts(
          ...msToTimerParts(Math.abs(this.intervalRemainingTime))
        );
      }
    },
    ...mapActions(['GET_SHOW_SESSION_DATA', 'GET_ACT_LIST']),
  },
};
</script>

<style scoped>
.session-header {
  border-bottom: 0.1rem solid #3498db;
}
</style>
