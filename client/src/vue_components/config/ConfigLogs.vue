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

<script>
import $ from 'jquery';
import { debounce } from 'lodash';
import { makeURL } from '@/js/utils';

export default {
  name: 'ConfigLogs',
  data() {
    return {
      entries: [],
      totalEntries: 0,
      source: 'server',
      levelFilter: '',
      searchInput: '',
      usernameInput: '',
      limit: 500,
      liveRefresh: false,
      loading: false,
      error: null,
      autoScroll: true,
      debounceContentSize: debounce(this.computeContentSize, 100),

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
    source() {
      this.usernameInput = '';
      if (this.liveRefresh) {
        this.restartStream();
      } else {
        this.fetchLogs();
      }
    },
    levelFilter() {
      if (this.liveRefresh) {
        this.restartStream();
      } else {
        this.fetchLogs();
      }
    },
    searchInput() {
      clearTimeout(this.searchDebounceTimer);
      this.searchDebounceTimer = setTimeout(() => {
        if (this.liveRefresh) {
          this.restartStream();
        } else {
          this.fetchLogs();
        }
      }, 400);
    },
    usernameInput() {
      clearTimeout(this.usernameDebounceTimer);
      this.usernameDebounceTimer = setTimeout(() => {
        if (this.liveRefresh) {
          this.restartStream();
        } else {
          this.fetchLogs();
        }
      }, 400);
    },
    liveRefresh(val) {
      if (val) {
        this.startStream();
      } else {
        this.stopStream();
      }
    },
  },
  created() {
    this.searchDebounceTimer = null;
    this.usernameDebounceTimer = null;
    // Non-reactive stream state kept off Vue's reactivity system.
    this.streamReader = null;
    this.streamAborted = false;
  },
  async mounted() {
    await this.fetchLogs();
    this.computeContentSize();
    window.addEventListener('resize', this.debounceContentSize);
  },
  beforeDestroy() {
    this.stopStream();
    clearTimeout(this.searchDebounceTimer);
    clearTimeout(this.usernameDebounceTimer);
    window.removeEventListener('resize', this.debounceContentSize);
  },
  methods: {
    computeContentSize() {
      const scriptContainer = $('#log-console');
      const startPos = scriptContainer.offset().top;
      const boxHeight = document.documentElement.clientHeight - startPos;
      scriptContainer.height(boxHeight - 50);
    },
    // ------------------------------------------------------------------ //
    // One-shot snapshot fetch (used when live stream is off)
    // ------------------------------------------------------------------ //
    async fetchLogs() {
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
      } catch (err) {
        this.error = err.message || 'Failed to fetch logs';
      } finally {
        this.loading = false;
      }
    },
    // ------------------------------------------------------------------ //
    // SSE live stream (used when liveRefresh is true)
    // ------------------------------------------------------------------ //
    buildStreamUrl() {
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
    async startStream() {
      this.stopStream();
      this.streamAborted = false;
      this.error = null;

      let response;
      try {
        response = await fetch(this.buildStreamUrl());
      } catch (err) {
        this.error = err.message || 'Failed to connect to log stream';
        return;
      }

      if (!response.ok) {
        this.error = `Log stream returned ${response.status}`;
        return;
      }

      // Clear existing entries — the stream sends backfill from scratch.
      this.entries = [];
      this.totalEntries = 0;

      const reader = response.body.getReader();
      this.streamReader = reader;
      const decoder = new TextDecoder();

      // SSE events are separated by "\n\n".  Because TCP packets don't align
      // with event boundaries, we accumulate chunks in a string buffer and
      // split on the separator, keeping any incomplete trailing chunk.
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          const events = buffer.split('\n\n');
          buffer = events.pop(); // last element may be an incomplete event

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
                // Ignore malformed JSON — should never happen in practice.
              }
            }
            // Comment lines (": keepalive") are intentionally ignored.
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
    stopStream() {
      if (this.streamReader) {
        this.streamAborted = true;
        this.streamReader.cancel();
        this.streamReader = null;
      }
    },
    restartStream() {
      this.stopStream();
      this.startStream();
    },

    // ------------------------------------------------------------------ //
    // Formatting helpers
    // ------------------------------------------------------------------ //
    formatEntry(entry) {
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
    levelClass(level) {
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
    levelLetter(level) {
      const map = {
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
    onScroll() {
      const el = this.$refs.console;
      if (!el) return;
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
      this.autoScroll = atBottom;
    },
    scrollToBottom() {
      const el = this.$refs.console;
      if (el) el.scrollTop = el.scrollHeight;
    },
  },
};
</script>
