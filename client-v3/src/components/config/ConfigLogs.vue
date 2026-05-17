<template>
  <div>
    <!-- Controls bar -->
    <div class="mb-3 d-flex flex-wrap gap-3 align-items-center">
      <BFormGroup label="Source:" label-cols="auto" class="mb-0">
        <BFormRadioGroup
          v-model="source"
          :options="sourceOptions"
          buttons
          button-variant="outline-secondary"
          size="sm"
        />
      </BFormGroup>

      <BFormGroup label="Level:" label-cols="auto" class="mb-0">
        <BFormSelect v-model="levelFilter" :options="levelOptions" size="sm" style="width: 120px" />
      </BFormGroup>

      <BFormGroup label="Search:" label-cols="auto" class="mb-0">
        <BFormInput
          v-model="searchInput"
          placeholder="Filter messages…"
          size="sm"
          style="width: 200px"
          type="text"
        />
      </BFormGroup>

      <BFormGroup v-if="source === 'client'" label="User:" label-cols="auto" class="mb-0">
        <BFormInput
          v-model="usernameInput"
          placeholder="Filter by username…"
          size="sm"
          style="width: 160px"
          type="text"
        />
      </BFormGroup>

      <BFormGroup label="Max lines:" label-cols="auto" class="mb-0">
        <BFormInput
          v-model.number="limit"
          min="10"
          max="1000"
          size="sm"
          style="width: 80px"
          type="number"
        />
      </BFormGroup>

      <BFormGroup label="Live:" label-cols="auto" class="mb-0">
        <BFormCheckbox v-model="liveRefresh" switch />
      </BFormGroup>

      <BButton :disabled="loading || liveRefresh" size="sm" variant="secondary" @click="fetchLogs">
        <BSpinner v-if="loading" small />
        <span v-else>Refresh</span>
      </BButton>
    </div>

    <!-- Status line -->
    <div class="mb-1 text-muted" style="font-size: 0.8rem">
      <span v-if="error" class="text-danger">{{ error }}</span>
      <span v-else-if="liveRefresh" class="text-success">&#9679; Live</span>
      <span v-else>Showing {{ entries.length }} of {{ totalEntries }} entries</span>
    </div>

    <!-- Console -->
    <div
      ref="consoleRef"
      class="log-console"
      style="
        background: #1e1e1e;
        color: #d4d4d4;
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        font-size: 0.78rem;
        line-height: 1.45;
        padding: 8px 12px;
        height: 520px;
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

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { makeURL } from '@/js/utils';

interface LogEntry {
  ts: string;
  level: string;
  filename: string;
  lineno: number;
  message: string;
}

const consoleRef = ref<HTMLElement | null>(null);

const entries = ref<LogEntry[]>([]);
const totalEntries = ref(0);
const source = ref('server');
const levelFilter = ref('');
const searchInput = ref('');
const usernameInput = ref('');
const limit = ref(500);
const liveRefresh = ref(false);
const loading = ref(false);
const error = ref<string | null>(null);
const autoScroll = ref(true);

let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;
let usernameDebounceTimer: ReturnType<typeof setTimeout> | null = null;
let streamReader: ReadableStreamDefaultReader<Uint8Array> | null = null;
let streamAborted = false;

const sourceOptions = [
  { text: 'Server', value: 'server' },
  { text: 'Client', value: 'client' },
];

const levelOptions = [
  { text: 'All Levels', value: '' },
  { text: 'TRACE+', value: 'TRACE' },
  { text: 'DEBUG+', value: 'DEBUG' },
  { text: 'INFO+', value: 'INFO' },
  { text: 'WARN+', value: 'WARN' },
  { text: 'ERROR+', value: 'ERROR' },
];

watch(source, () => {
  usernameInput.value = '';
  if (liveRefresh.value) restartStream();
  else fetchLogs();
});

watch(levelFilter, () => {
  if (liveRefresh.value) restartStream();
  else fetchLogs();
});

watch(searchInput, () => {
  clearTimeout(searchDebounceTimer ?? undefined);
  searchDebounceTimer = setTimeout(() => {
    if (liveRefresh.value) restartStream();
    else fetchLogs();
  }, 400);
});

watch(usernameInput, () => {
  clearTimeout(usernameDebounceTimer ?? undefined);
  usernameDebounceTimer = setTimeout(() => {
    if (liveRefresh.value) restartStream();
    else fetchLogs();
  }, 400);
});

watch(liveRefresh, (val) => {
  if (val) startStream();
  else stopStream();
});

async function fetchLogs(): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    const params = new URLSearchParams({
      source: source.value,
      level: levelFilter.value,
      search: searchInput.value,
      limit: String(limit.value),
      offset: '0',
    });
    if (source.value === 'client' && usernameInput.value)
      params.set('username', usernameInput.value);

    const response = await fetch(`${makeURL('/api/v1/logs/view')}?${params}`);
    if (!response.ok) {
      error.value = `Server returned ${response.status}`;
      return;
    }

    const data = await response.json();
    const wasAtBottom = autoScroll.value;
    entries.value = data.entries;
    totalEntries.value = data.total;
    if (wasAtBottom) nextTick(scrollToBottom);
  } catch (err: any) {
    error.value = err.message || 'Failed to fetch logs';
  } finally {
    loading.value = false;
  }
}

function buildStreamUrl(): string {
  const params = new URLSearchParams({
    source: source.value,
    level: levelFilter.value,
    search: searchInput.value,
  });
  if (source.value === 'client' && usernameInput.value) params.set('username', usernameInput.value);
  return `${makeURL('/api/v1/logs/stream')}?${params}`;
}

async function startStream(): Promise<void> {
  stopStream();
  streamAborted = false;
  error.value = null;

  let response: Response;
  try {
    response = await fetch(buildStreamUrl());
  } catch (err: any) {
    error.value = err.message || 'Failed to connect to log stream';
    return;
  }

  if (!response.ok) {
    error.value = `Log stream returned ${response.status}`;
    return;
  }

  entries.value = [];
  totalEntries.value = 0;

  const reader = response.body!.getReader();
  streamReader = reader;
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
            const wasAtBottom = autoScroll.value;
            entries.value.push(entry);
            totalEntries.value++;
            if (entries.value.length > limit.value) entries.value.shift();
            if (wasAtBottom) nextTick(scrollToBottom);
          } catch {
            // ignore malformed SSE JSON
          }
        }
      }
    }
  } catch {
    if (!streamAborted) {
      error.value = 'Log stream disconnected';
      liveRefresh.value = false;
    }
  } finally {
    streamReader = null;
  }
}

function stopStream(): void {
  if (streamReader) {
    streamAborted = true;
    streamReader.cancel();
    streamReader = null;
  }
}

function restartStream(): void {
  stopStream();
  startStream();
}

function formatEntry(entry: LogEntry): string {
  const dt = new Date(entry.ts);
  const yy = String(dt.getUTCFullYear()).slice(2);
  const mo = String(dt.getUTCMonth() + 1).padStart(2, '0');
  const dd = String(dt.getUTCDate()).padStart(2, '0');
  const hh = String(dt.getUTCHours()).padStart(2, '0');
  const mm = String(dt.getUTCMinutes()).padStart(2, '0');
  const ss = String(dt.getUTCSeconds()).padStart(2, '0');
  const ms = String(dt.getUTCMilliseconds()).padStart(3, '0');
  const letter = levelLetter(entry.level);
  return `[${letter} ${yy}-${mo}-${dd} ${hh}:${mm}:${ss}.${ms} ${entry.filename}:${entry.lineno}] ${entry.message}`;
}

function levelClass(level: string): string {
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
      return 'text-danger fw-bold';
    default:
      return 'text-light';
  }
}

function levelLetter(level: string): string {
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
}

function onScroll(): void {
  const el = consoleRef.value;
  if (!el) return;
  autoScroll.value = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
}

function scrollToBottom(): void {
  const el = consoleRef.value;
  if (el) el.scrollTop = el.scrollHeight;
}

onMounted(() => fetchLogs());

onBeforeUnmount(() => {
  stopStream();
  clearTimeout(searchDebounceTimer ?? undefined);
  clearTimeout(usernameDebounceTimer ?? undefined);
});
</script>
