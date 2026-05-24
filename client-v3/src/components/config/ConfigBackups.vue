<template>
  <div v-if="!loading">
    <div v-if="backups.length > 0">
      <p class="text-muted mb-3">
        {{ count }} {{ count === 1 ? 'backup' : 'backups' }} &middot;
        {{ formatBytes(totalSizeBytes) }} total
      </p>
      <BTable :items="backups" :fields="fields" sort-by="created_at" :sort-desc="true">
        <template #cell(size_bytes)="data">
          {{ formatBytes(data.item.size_bytes) }}
        </template>
        <template #cell(created_at)="data">
          {{ formatDate(data.item.created_at) }}
        </template>
        <template #cell(actions)="data">
          <BButton
            variant="danger"
            size="sm"
            :disabled="isDeleting"
            @click="deleteBackup(data.item)"
          >
            Delete
          </BButton>
        </template>
      </BTable>
    </div>
    <BAlert v-else variant="info" :model-value="true">
      No backup files found. Backups are created automatically before database migrations.
    </BAlert>
  </div>
  <div v-else class="text-center">
    <BSpinner style="width: 10rem; height: 10rem" variant="info" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import log from 'loglevel';
import { makeURL } from '@/js/utils';
import { toast } from '@/js/toast';
import { useConfirm } from '@/composables/useConfirm';
import type { BackupFile, BackupsResponse } from '@/types/api/backup';

const { confirm } = useConfirm();

const loading = ref(true);
const isDeleting = ref(false);
const backups = ref<BackupFile[]>([]);
const count = ref(0);
const totalSizeBytes = ref(0);

const fields = [
  { key: 'filename', label: 'Filename' },
  { key: 'size_bytes', label: 'Size', sortable: true },
  { key: 'created_at', label: 'Date Created', sortable: true },
  { key: 'actions', label: '' },
];

async function fetchBackups(): Promise<void> {
  try {
    const response = await fetch(makeURL('/api/v1/admin/db-backups'));
    if (response.ok) {
      const data: BackupsResponse = await response.json();
      backups.value = data.backups;
      count.value = data.count;
      totalSizeBytes.value = data.total_size_bytes;
    } else {
      log.error('Unable to fetch backup files');
    }
  } catch (err) {
    log.error('Error fetching backup files:', err);
  }
}

async function deleteBackup(backup: BackupFile): Promise<void> {
  const confirmed = await confirm(
    `Are you sure you want to permanently delete "${backup.filename}"? This cannot be undone.`,
    { title: 'Delete Backup', okVariant: 'danger', okTitle: 'Delete' }
  );
  if (!confirmed) return;

  isDeleting.value = true;
  try {
    const response = await fetch(
      makeURL(`/api/v1/admin/db-backups?timestamp=${backup.created_at}`),
      { method: 'DELETE' }
    );
    if (response.ok) {
      toast.success('Backup deleted');
      await fetchBackups();
    } else {
      const body = await response.json();
      toast.error(`Failed to delete backup: ${body.message}`);
    }
  } catch (err) {
    log.error('Error deleting backup:', err);
    toast.error('Failed to delete backup');
  } finally {
    isDeleting.value = false;
  }
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** i).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function formatDate(unixTimestamp: number): string {
  const d = new Date(unixTimestamp * 1000);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

onMounted(async () => {
  await fetchBackups();
  loading.value = false;
});
</script>
