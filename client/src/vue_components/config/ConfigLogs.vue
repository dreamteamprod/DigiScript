<template>
  <div>
    <!-- Controls bar -->
    <b-form class="mb-3 text-left" inline>
      <b-form-group class="mr-3 mb-2" label="Source:" label-cols="auto">
        <b-form-radio-group
          v-model="source"
          :options="sourceOptions"
          buttons
          button-variant="outline-secondary"
          size="sm"
        />
      </b-form-group>

      <b-form-group class="mr-3 mb-2" label="Level:" label-cols="auto">
        <b-form-select
          v-model="levelFilter"
          :options="levelOptions"
          size="sm"
          style="width: 120px"
        />
      </b-form-group>

      <b-form-group class="mr-3 mb-2" label="Search:" label-cols="auto">
        <b-form-input
          v-model="searchInput"
          placeholder="Filter messages…"
          size="sm"
          style="width: 200px"
          type="text"
        />
      </b-form-group>

      <b-form-group v-if="source === 'client'" class="mr-3 mb-2" label="User:" label-cols="auto">
        <b-form-input
          v-model="usernameInput"
          placeholder="Filter by username…"
          size="sm"
          style="width: 160px"
          type="text"
        />
      </b-form-group>

      <b-form-group class="mr-3 mb-2" label="Max lines:" label-cols="auto">
        <b-form-input
          v-model.number="limit"
          min="10"
          max="1000"
          size="sm"
          style="width: 80px"
          type="number"
        />
      </b-form-group>

      <b-form-group class="mr-3 mb-2" label="Live:" label-cols="auto">
        <b-form-checkbox v-model="liveRefresh" switch />
      </b-form-group>

      <b-button
        :disabled="loading || liveRefresh"
        class="mb-2"
        size="sm"
        variant="secondary"
        @click="fetchLogs"
      >
        <b-spinner v-if="loading" small />
        <span v-else>Refresh</span>
      </b-button>
    </b-form>

    <!-- Status line -->
    <div class="mb-1 text-muted" style="font-size: 0.8rem">
      <span v-if="error" class="text-danger">{{ error }}</span>
      <span v-else-if="liveRefresh" class="text-success">&#9679; Live</span>
      <span v-else>Showing {{ entries.length }} of {{ totalEntries }} entries</span>
    </div>

    <!-- Console -->
    <div
      id="log-console"
      ref="console"
      class="log-console"
      style="
        background: #1e1e1e;
        color: #d4d4d4;
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        font-size: 0.78rem;
        line-height: 1.45;
        padding: 8px 12px;
        min-height: 520px;
        overflow-y: auto;
        border-radius: 4px;
        white-space: pre-wrap;
        word-break: break-all;
        text-align: left;
      "
      @scroll="onScroll"
    >
      <div v-if="entries.length === 0" class="text-muted" style="padding-top: 4px">
        No log entries to display.
      </div>
      <div v-for="(entry, idx) in entries" :key="idx">
        <span :class="levelClass(entry.level)">{{ formatEntry(entry) }}</span>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import $ from 'jquery';
import { debounce } from 'lodash';
import { makeURL } from '@/js/utils';

interface LogEntry {
  ts: string;
  level: string;
  filename: string;
  lineno: number;
  message: string;
}

export default defineComponent({
  name: 'ConfigLogs',
  data() {
    return {
      entries: [] as LogEntry[],
      totalEntries: 0,
      source: 'server',
      levelFilter: '',
      searchInput: '',
      usernameInput: '',
      limit: 500,
      liveRefresh: false,
      loading: false,
      error: null as string | null,
      autoScroll: true,
      searchDebounceTimer: null as ReturnType<typeof setTimeout> | null,
      usernameDebounceTimer: null as ReturnType<typeof setTimeout> | null,
      streamReader: null as ReadableStreamDefaultReader<Uint8Array> | null,
      streamAborted: false,
      debounceContentSize: null as ((...args: unknown[]) => void) | null,

      sourceOptions: [
        { text: 'Server', value: 'server' },
        { text: 'Client', value: 'client' },
      ],
      levelOptions: [
        { text: 'All Levels', value: '' },
        { text: 'TRACE+', value: 'TRACE' },
        { text: 'DEBUG+', value: 'DEBUG' },
        { text: 'INFO+', value: 'INFO' },
        { text: 'WARN+', value: 'WARN' },
        { text: 'ERROR+', value: 'ERROR' },
      ],
    };
  },
  watch: {
    source(): void {
      this.usernameInput = '';
      if (this.liveRefresh) {
        this.restartStream();
      } else {
        this.fetchLogs();
      }
    },
    levelFilter(): void {
      if (this.liveRefresh) {
        this.restartStream();
      } else {
        this.fetchLogs();
      }
    },
    searchInput(): void {
      clearTimeout(this.searchDebounceTimer ?? undefined);
      this.searchDebounceTimer = setTimeout(() => {
        if (this.liveRefresh) {
          this.restartStream();
        } else {
          this.fetchLogs();
        }
      }, 400);
    },
    usernameInput(): void {
      clearTimeout(this.usernameDebounceTimer ?? undefined);
      this.usernameDebounceTimer = setTimeout(() => {
        if (this.liveRefresh) {
          this.restartStream();
        } else {
          this.fetchLogs();
        }
      }, 400);
    },
    liveRefresh(val: boolean): void {
      if (val) {
        this.startStream();
      } else {
        this.stopStream();
      }
    },
  },
  async mounted() {
    this.debounceContentSize = debounce(this.computeContentSize, 100);
    await this.fetchLogs();
    this.computeContentSize();
    window.addEventListener('resize', this.debounceContentSize);
  },
  beforeDestroy() {
    this.stopStream();
    clearTimeout(this.searchDebounceTimer ?? undefined);
    clearTimeout(this.usernameDebounceTimer ?? undefined);
    window.removeEventListener('resize', this.debounceContentSize);
  },
  methods: {
    computeContentSize(): void {
      const scriptContainer = $('#log-console');
      const startPos = scriptContainer.offset()!.top;
      const boxHeight = document.documentElement.clientHeight - startPos;
      scriptContainer.height(boxHeight - 50);
    },
    async fetchLogs(): Promise<void> {
      this.loading = true;
      this.error = null;
      try {
        const params = new URLSearchParams({
          source: this.source,
          level: this.levelFilter,
          search: this.searchInput,
          limit: String(this.limit),
          offset: '0',
        });
        if (this.source === 'client' && this.usernameInput) {
          params.set('username', this.usernameInput);
        }
        const response = await fetch(`${makeURL('/api/v1/logs/view')}?${params}`);
        if (!response.ok) {
          this.error = `Server returned ${response.status}`;
          return;
        }
        const data = await response.json();
        const wasAtBottom = this.autoScroll;
        this.entries = data.entries;
        this.totalEntries = data.total;
        if (wasAtBottom) {
          this.$nextTick(() => this.scrollToBottom());
        }
      } catch (err: any) {
        this.error = err.message || 'Failed to fetch logs';
      } finally {
        this.loading = false;
      }
    },
    buildStreamUrl(): string {
      const params = new URLSearchParams({
        source: this.source,
        level: this.levelFilter,
        search: this.searchInput,
      });
      if (this.source === 'client' && this.usernameInput) {
        params.set('username', this.usernameInput);
      }
      return `${makeURL('/api/v1/logs/stream')}?${params}`;
    },
    async startStream(): Promise<void> {
      this.stopStream();
      this.streamAborted = false;
      this.error = null;

      let response: Response;
      try {
        response = await fetch(this.buildStreamUrl());
      } catch (err: any) {
        this.error = err.message || 'Failed to connect to log stream';
        return;
      }

      if (!response.ok) {
        this.error = `Log stream returned ${response.status}`;
        return;
      }

      this.entries = [];
      this.totalEntries = 0;

      const reader = response.body!.getReader();
      this.streamReader = reader;
      const decoder = new TextDecoder();
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const events = buffer.split('\n\n');
          buffer = events.pop()!;

          for (const event of events) {
            if (event.startsWith('data: ')) {
              try {
                const entry = JSON.parse(event.slice(6));
                const wasAtBottom = this.autoScroll;
                this.entries.push(entry);
                this.totalEntries++;
                if (this.entries.length > this.limit) {
                  this.entries.shift();
                }
                if (wasAtBottom) {
                  this.$nextTick(() => this.scrollToBottom());
                }
              } catch {
                // ignore malformed SSE JSON
              }
            }
          }
        }
      } catch {
        if (!this.streamAborted) {
          this.error = 'Log stream disconnected';
          this.liveRefresh = false;
        }
      } finally {
        this.streamReader = null;
      }
    },
    stopStream(): void {
      if (this.streamReader) {
        this.streamAborted = true;
        this.streamReader.cancel();
        this.streamReader = null;
      }
    },
    restartStream(): void {
      this.stopStream();
      this.startStream();
    },
    formatEntry(entry: LogEntry): string {
      const dt = new Date(entry.ts);
      const yy = String(dt.getUTCFullYear()).slice(2);
      const mo = String(dt.getUTCMonth() + 1).padStart(2, '0');
      const dd = String(dt.getUTCDate()).padStart(2, '0');
      const hh = String(dt.getUTCHours()).padStart(2, '0');
      const mm = String(dt.getUTCMinutes()).padStart(2, '0');
      const ss = String(dt.getUTCSeconds()).padStart(2, '0');
      const ms = String(dt.getUTCMilliseconds()).padStart(3, '0');
      const letter = this.levelLetter(entry.level);
      return `[${letter} ${yy}-${mo}-${dd} ${hh}:${mm}:${ss}.${ms} ${entry.filename}:${entry.lineno}] ${entry.message}`;
    },
    levelClass(level: string): string {
      switch (level) {
        case 'TRACE':
          return 'text-secondary';
        case 'DEBUG':
          return 'text-info';
        case 'INFO':
          return 'text-success';
        case 'WARNING':
        case 'WARN':
          return 'text-warning';
        case 'ERROR':
          return 'text-danger';
        case 'CRITICAL':
          return 'text-danger font-weight-bold';
        default:
          return 'text-light';
      }
    },
    levelLetter(level: string): string {
      const map: Record<string, string> = {
        TRACE: 'T',
        DEBUG: 'D',
        INFO: 'I',
        WARNING: 'W',
        WARN: 'W',
        ERROR: 'E',
        CRITICAL: 'C',
      };
      return map[level] || level[0];
    },
    onScroll(): void {
      const el = this.$refs.console as HTMLElement | undefined;
      if (!el) return;
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
      this.autoScroll = atBottom;
    },
    scrollToBottom(): void {
      const el = this.$refs.console as HTMLElement | undefined;
      if (el) el.scrollTop = el.scrollHeight;
    },
  },
});
</script>
