<template>
  <b-container class="mx-0" fluid>
    <b-row style="margin-bottom: 0.5rem">
      <b-col class="text-left pl-0">
        <b-button
          v-if="IS_SHOW_EXECUTOR"
          variant="success"
          :disabled="CURRENT_SHOW_SESSION !== null || startingSession"
          @click.stop="startSession"
        >
          Start Session
        </b-button>
      </b-col>
    </b-row>
    <b-row>
      <b-col>
        <b-table id="acts-table" :items="SHOW_SESSIONS_LIST" :fields="sessionFields" show-empty>
          <template #cell(run_time)="data">
            <p v-if="data.item.end_date_time">
              {{ runTimeCalc(data.item.start_date_time, data.item.end_date_time) }}
            </p>
          </template>

          <template #cell(script_revision_id)="data">
            <p>
              {{ scriptRevisionLabel(data.item.script_revision_id) }}
            </p>
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
                    color: contrastColor({ bgColor: tag.colour }),
                  }"
                >
                  {{ tag.tag }}
                </span>
              </div>
              <session-tag-dropdown
                v-if="IS_SHOW_EDITOR"
                :session-id="data.item.id"
                :current-tag-ids="data.item.tags.map((t) => t.id)"
              />
            </div>
          </template>
        </b-table>
      </b-col>
    </b-row>
  </b-container>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapGetters } from 'vuex';
import log from 'loglevel';
import { contrastColor } from 'contrast-color';

import { makeURL, msToTimerString } from '@/js/utils';
import SessionTagDropdown from './SessionTagDropdown.vue';

export default defineComponent({
  name: 'SessionList',
  components: {
    SessionTagDropdown,
  },
  data() {
    return {
      sessionFields: [
        { key: 'start_date_time', label: 'Start Time' },
        { key: 'end_date_time', label: 'End Time' },
        { key: 'run_time', label: 'Run Time' },
        { key: 'script_revision_id', label: 'Script Revision' },
        { key: 'tags', label: 'Tags' },
      ],
      startingSession: false,
    };
  },
  computed: {
    ...mapGetters([
      'SHOW_SESSIONS_LIST',
      'CURRENT_SHOW_SESSION',
      'INTERNAL_UUID',
      'IS_SHOW_EXECUTOR',
      'IS_SHOW_EDITOR',
      'SCRIPT_REVISIONS',
    ]),
  },
  methods: {
    contrastColor,
    async startSession(): Promise<void> {
      if ((this as any).INTERNAL_UUID == null) {
        (this as any).$toast.error('Unable to start new show session');
        return;
      }
      this.startingSession = true;
      const response = await fetch(`${makeURL('/api/v1/show/sessions/start')}`, {
        method: 'POST',
        body: JSON.stringify({
          session_id: (this as any).INTERNAL_UUID,
        }),
      });
      if (response.ok) {
        (this as any).$toast.success('Started new show session');
      } else {
        log.error('Unable to start new show session');
        (this as any).$toast.error('Unable to start new show session');
      }
      this.startingSession = false;
    },
    runTimeCalc(start: string, end: string): string {
      const startDate = Date.parse(start);
      const endDate = Date.parse(end);
      const diff = endDate - startDate;
      return msToTimerString(diff);
    },
    scriptRevisionLabel(revisionId: number): string {
      const revision = (this as any).SCRIPT_REVISIONS.find((rev: any) => rev.id === revisionId);
      if (revision) {
        return `${revision.revision}: ${revision.description}`;
      }
      return 'N/A';
    },
  },
});
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
