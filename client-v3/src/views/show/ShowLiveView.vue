<template>
  <BContainer
    fluid
    class="mx-0"
    :style="{ 'padding-right': showStore.stageManagerMode ? '0px' : '15px' }"
  >
    <BRow
      class="session-header"
      style="padding-top: 0.1rem; padding-bottom: 0.1rem"
      :style="{ 'padding-right': showStore.stageManagerMode ? '15px' : '0px' }"
    >
      <BCol cols="4" style="text-align: left">
        <b v-if="isScriptFollowing">{{ systemStore.currentShow?.name }} - Following</b>
        <b v-else-if="isScriptLeader">{{ systemStore.currentShow?.name }} - Leading</b>
        <b v-else>{{ systemStore.currentShow?.name }} - Manual</b>
      </BCol>
      <BCol cols="4" style="text-align: center">
        <b>Page {{ currentPage }}</b>
      </BCol>
      <BCol cols="4" style="text-align: right">
        <b>Elapsed Time: {{ msToTimerString(elapsedTime) }}</b>
      </BCol>
    </BRow>
    <BOverlay :show="showStore.currentInterval != null" rounded="sm" variant="secondary">
      <template #overlay>
        <div class="text-center interval-overlay">
          <BContainer fluid class="mx-0">
            <BRow>
              <BCol class="d-flex align-items-center justify-content-center">
                <h3>{{ intervalOverlayHeading }} - Interval in Progress ⏱</h3>
              </BCol>
            </BRow>
            <BRow v-if="intervalTimerActive">
              <BCol class="d-flex align-items-center justify-content-center">
                <h1 style="margin-top: 0.5rem">
                  <span :style="intervalTimerStyle">{{ intervalTimerValues[0] }}</span
                  >:<span :style="intervalTimerStyle">{{ intervalTimerValues[1] }}</span
                  >:<span :style="intervalTimerStyle">{{ intervalTimerValues[2] }}</span>
                </h1>
              </BCol>
            </BRow>
            <BRow style="margin-top: 0.5rem">
              <BCol class="d-flex align-items-center justify-content-center">
                <BButton v-if="isScriptLeader" variant="primary" @click.stop="stopInterval">
                  Stop Interval
                </BButton>
              </BCol>
            </BRow>
          </BContainer>
        </div>
      </template>
      <Splitpanes class="default-theme">
        <Pane>
          <ScriptViewPane
            :is-script-following="isScriptFollowing"
            :is-script-leader="isScriptLeader"
            :session-follow-data="showStore.sessionFollowData"
            :initial-line-ref="showStore.currentSession?.latest_line_ref ?? null"
            :interval-active="showStore.currentInterval != null"
            :script-mode="systemStore.currentShow?.script_mode ?? 1"
            :stage-manager-mode="showStore.stageManagerMode"
            @page-change="currentPage = $event"
          />
        </Pane>
        <Pane v-if="showStore.stageManagerMode" :size="20">
          <StageManagerPane :session-follow-data="showStore.sessionFollowData" />
        </Pane>
      </Splitpanes>
    </BOverlay>
  </BContainer>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { Splitpanes, Pane } from 'splitpanes';
import 'splitpanes/dist/splitpanes.css';

import { formatTimerParts, msToTimerParts, msToTimerString } from '@/js/utils';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import { useWebSocketStore } from '@/stores/websocket';
import { useWebSocket } from '@/composables/useWebSocket';
import { toast } from '@/js/toast';
import ScriptViewPane from '@/components/show/live/ScriptViewPane.vue';
import StageManagerPane from '@/components/show/live/StageManagerPane.vue';

const showStore = useShowStore();
const systemStore = useSystemStore();
const wsStore = useWebSocketStore();
const { sendObj } = useWebSocket();

// Session header state
const loadedSessionData = ref(false);
const currentPage = ref(1);

// Elapsed time
const elapsedTime = ref(0);
let elapsedTimer: ReturnType<typeof setInterval> | null = null;
let startTime: Date | null = null;

// Interval timer
let intervalTimerHandle: ReturnType<typeof setInterval> | null = null;
let intervalStartDate: Date | null = null;
const isIntervalLong = ref(false);
const intervalTimerValues = ref<(string | number)[]>([0, 0, 0]);
const intervalRemainingTime = ref(0);
const intervalTimerActive = ref(false);

// Computed

const isScriptLeader = computed(
  () =>
    loadedSessionData.value && showStore.currentSession?.client_internal_id === wsStore.internalUUID
);

const isScriptFollowing = computed(
  () =>
    loadedSessionData.value &&
    showStore.currentSession?.client_internal_id != null &&
    !isScriptLeader.value
);

const intervalOverlayHeading = computed(() => {
  if (!showStore.currentInterval || showStore.actList.length === 0) return '';
  return showStore.actList.find((a) => a.id === showStore.currentInterval!.act_id)?.name ?? '';
});

const intervalTimerColour = computed(() => {
  if (isIntervalLong.value) return '#cc0000';
  const initialLength = (showStore.currentInterval?.initial_length ?? 1) * 1000;
  const progress = Math.abs(intervalRemainingTime.value) / initialLength;
  return progress > 0.25 ? '#00cc00' : '#d76113';
});

const intervalTimerStyle = computed(() => ({
  margin: '.5rem',
  'border-radius': '3px',
  color: '#ffffff',
  'background-color': intervalTimerColour.value,
  padding: '.25rem',
}));

// Methods

function createDateAsUTC(date: Date): Date {
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
}

function updateElapsedTime(): void {
  if (startTime != null) elapsedTime.value = Date.now() - startTime.getTime();
}

function stopInterval(): void {
  sendObj({ OP: 'END_INTERVAL', DATA: {} });
  toast.success('Interval stopped!');
}

function updateIntervalTimer(): void {
  if (!intervalStartDate || !showStore.currentInterval) return;
  const elapsed = Date.now() - intervalStartDate.getTime();
  intervalRemainingTime.value = showStore.currentInterval.initial_length! * 1000 - elapsed;
  isIntervalLong.value = intervalRemainingTime.value < 0;
  intervalTimerValues.value = formatTimerParts(
    ...msToTimerParts(Math.abs(intervalRemainingTime.value))
  );
}

function setupIntervalTimer(): void {
  if (intervalTimerHandle !== null) {
    clearInterval(intervalTimerHandle);
    intervalTimerHandle = null;
  }
  intervalTimerValues.value = [0, 0, 0];
  isIntervalLong.value = false;
  intervalRemainingTime.value = 0;
  intervalTimerActive.value = false;

  if (showStore.currentInterval) {
    intervalStartDate = createDateAsUTC(
      new Date(showStore.currentInterval.start_datetime!.replace(' ', 'T'))
    );
    updateIntervalTimer();
    intervalTimerActive.value = true;
    intervalTimerHandle = setInterval(updateIntervalTimer, 500);
  }
}

watch(() => showStore.currentInterval, setupIntervalTimer);

onMounted(async () => {
  await Promise.all([showStore.getShowSessionData(), showStore.getActList()]);
  loadedSessionData.value = true;

  if (showStore.currentInterval != null) setupIntervalTimer();

  if (showStore.currentSession?.start_date_time) {
    startTime = createDateAsUTC(
      new Date(showStore.currentSession.start_date_time.replace(' ', 'T'))
    );
  }
  updateElapsedTime();
  elapsedTimer = setInterval(updateElapsedTime, 1000);
});

onUnmounted(() => {
  if (elapsedTimer !== null) clearInterval(elapsedTimer);
  if (intervalTimerHandle !== null) clearInterval(intervalTimerHandle);
});
</script>

<style scoped>
.session-header {
  border-bottom: 0.1rem solid #3498db;
}

.interval-overlay {
  padding: 2rem;
}
</style>
