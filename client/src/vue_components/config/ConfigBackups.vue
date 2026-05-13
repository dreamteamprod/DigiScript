<template>
  <div v-if="!loading">
    <div v-if="backups.length > 0">
      <p class="text-muted mb-3">
        {{ count }} {{ count === 1 ? 'backup' : 'backups' }} &middot;
        {{ formatBytes(totalSizeBytes) }} total
      </p>
      <b-table :items="backups" :fields="fields" sort-by="created_at" :sort-desc="true">
        <template #cell(size_bytes)="data">
          {{ formatBytes(data.item.size_bytes) }}
        </template>
        <template #cell(created_at)="data">
          {{ formatDate(data.item.created_at) }}
        </template>
        <template #cell(actions)="data">
          <b-button
            variant="danger"
            size="sm"
            :disabled="isDeleting"
            @click="deleteBackup(data.item)"
          >
            Delete
          </b-button>
        </template>
      </b-table>
    </div>
    <b-alert v-else variant="info" show>
      No backup files found. Backups are created automatically before database migrations.
    </b-alert>
  </div>
  <div v-else class="text-center center-spinner">
    <b-spinner style="width: 10rem; height: 10rem" variant="info" />
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import log from 'loglevel';
import { makeURL } from '@/js/utils';
import type { BackupFile, BackupsResponse } from '@/types/api/backup';

export default defineComponent({
  name: 'ConfigBackups',
  data() {
    return {
      backups: [] as BackupFile[],
      count: 0,
      totalSizeBytes: 0,
      loading: true,
      isDeleting: false,
      fields: [
        { key: 'filename', label: 'Filename' },
        { key: 'size_bytes', label: 'Size', sortable: true },
        { key: 'created_at', label: 'Date Created', sortable: true },
        { key: 'actions', label: '' },
      ],
    };
  },
  async mounted() {
    await this.fetchBackups();
    this.loading = false;
  },
  methods: {
    async fetchBackups(): Promise<void> {
      try {
        const response = await fetch(makeURL('/api/v1/admin/db-backups'));
        if (response.ok) {
          const data: BackupsResponse = await response.json();
          this.backups = data.backups;
          this.count = data.count;
          this.totalSizeBytes = data.total_size_bytes;
        } else {
          log.error('Unable to fetch backup files');
        }
      } catch (error) {
        log.error('Error fetching backup files:', error);
      }
    },
    async deleteBackup(backup: BackupFile): Promise<void> {
      const confirmed = await (this as any).$bvModal.msgBoxConfirm(
        `Are you sure you want to permanently delete "${backup.filename}"? This cannot be undone.`,
        { title: 'Delete Backup', okVariant: 'danger', okTitle: 'Delete' }
      );
      if (!confirmed) return;

      this.isDeleting = true;
      try {
        const response = await fetch(
          makeURL(`/api/v1/admin/db-backups?timestamp=${backup.created_at}`),
          { method: 'DELETE' }
        );
        if (response.ok) {
          this.$toast.success('Backup deleted');
          await this.fetchBackups();
        } else {
          const body = await response.json();
          this.$toast.error(`Failed to delete backup: ${body.message}`);
        }
      } catch (error) {
        this.$toast.error('Failed to delete backup');
        log.error('Error deleting backup:', error);
      } finally {
        this.isDeleting = false;
      }
    },
    formatBytes(bytes: number): string {
      if (bytes === 0) return '0 B';
      const units = ['B', 'KB', 'MB', 'GB'];
      const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
      return `${(bytes / 1024 ** i).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
    },
    formatDate(unixTimestamp: number): string {
      const d = new Date(unixTimestamp * 1000);
      const day = String(d.getDate()).padStart(2, '0');
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const year = d.getFullYear();
      const hours = String(d.getHours()).padStart(2, '0');
      const minutes = String(d.getMinutes()).padStart(2, '0');
      const seconds = String(d.getSeconds()).padStart(2, '0');
      return `${day}/${month}/${year} ${hours}:${minutes}:${seconds}`;
    },
  },
});
</script>
