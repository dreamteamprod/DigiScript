<template>
  <BContainer class="mx-0" fluid>
    <BRow v-if="systemStore.isShowExecutor" style="margin-bottom: 0.5rem">
      <BCol class="text-start ps-0">
        <BButton
          variant="success"
          :disabled="systemStore.currentShow?.current_session_id !== null || startingSession"
          @click.stop="startSession"
        >
          Start Session
        </BButton>
      </BCol>
    </BRow>
    <BRow>
      <BCol>
        <BTable :items="showStore.sessions" :fields="sessionFields" show-empty>
          <template #cell(run_time)="data">
            <span v-if="data.item.end_date_time">
              {{ runTime(data.item.start_date_time, data.item.end_date_time) }}
            </span>
          </template>
          <template #cell(script_revision_id)="data">
            {{ revisionLabel(data.item.script_revision_id) }}
          </template>
          <template #cell(tags)="data">
            <div class="tags-cell">
              <div class="tags-pills-container">
                <span
                  v-for="tag in data.item.tags"
                  :key="tag.id"
                  class="tag-pill"
                  :style="{
                    backgroundColor: tag.colour,
                    color: contrastColor(tag.colour ?? '#ffffff'),
                  }"
                >
                  {{ tag.tag }}
                </span>
              </div>
              <SessionTagDropdown
                v-if="systemStore.isShowEditor"
                :session-id="data.item.id"
                :current-tag-ids="data.item.tags.map((t) => t.id)"
              />
            </div>
          </template>
        </BTable>
      </BCol>
    </BRow>
  </BContainer>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import log from 'loglevel';
import { makeURL, msToTimerString, contrastColor } from '@/js/utils';
import { useSystemStore } from '@/stores/system';
import { useShowStore } from '@/stores/show';
import { useWebSocketStore } from '@/stores/websocket';
import { toast } from '@/js/toast';
import SessionTagDropdown from './SessionTagDropdown.vue';

const systemStore = useSystemStore();
const showStore = useShowStore();
const wsStore = useWebSocketStore();

const startingSession = ref(false);

const sessionFields = [
  { key: 'start_date_time', label: 'Start Time' },
  { key: 'end_date_time', label: 'End Time' },
  { key: 'run_time', label: 'Run Time' },
  { key: 'script_revision_id', label: 'Script Revision' },
  { key: 'tags', label: 'Tags' },
];

function runTime(start: string | null, end: string | null): string {
  if (!start || !end) return '';
  const diff = Date.parse(end) - Date.parse(start);
  return msToTimerString(diff);
}

function revisionLabel(revisionId: number | null): string {
  if (revisionId == null) return 'N/A';
  const revision = showStore.scriptRevisionById(revisionId);
  if (revision) return `${revision.revision}: ${revision.description}`;
  return String(revisionId);
}

async function startSession(): Promise<void> {
  if (!wsStore.internalUUID) {
    toast.error('Unable to start new show session');
    return;
  }
  startingSession.value = true;
  try {
    const response = await fetch(makeURL('/api/v1/show/sessions/start'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: wsStore.internalUUID }),
    });
    if (response.ok) {
      toast.success('Started new show session');
      await showStore.getShowSessionData();
    } else {
      log.error('Unable to start new show session');
      toast.error('Unable to start new show session');
    }
  } finally {
    startingSession.value = false;
  }
}
</script>

<style scoped>
.tags-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 30px;
  gap: 8px;
}

.tags-pills-container {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.tag-pill {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 12px;
  white-space: nowrap;
  border: 1px solid rgba(0, 0, 0, 0.1);
}
</style>
