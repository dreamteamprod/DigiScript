<template>
  <BModal
    ref="modal"
    :title="`Revision ${revision ? revision.revision : ''}`"
    size="lg"
    @hidden="$emit('hidden')"
  >
    <div v-if="revision">
      <BRow>
        <BCol cols="12">
          <BAlert v-if="isCurrentRevision" variant="success" :model-value="true">
            This is the current active revision
          </BAlert>
        </BCol>
      </BRow>
      <BRow>
        <BCol cols="12" md="6">
          <dl>
            <dt>Revision Number</dt>
            <dd>{{ revision.revision }}</dd>
            <dt>Description</dt>
            <dd>{{ revision.description || 'No description' }}</dd>
            <dt>Created At</dt>
            <dd>{{ formatDate(revision.created_at) }}</dd>
            <dt>Last Edited</dt>
            <dd>{{ formatDate(revision.edited_at) }}</dd>
          </dl>
        </BCol>
        <BCol cols="12" md="6">
          <dl>
            <dt>Previous Revision</dt>
            <dd v-if="previousRevision">
              Revision {{ previousRevision.revision }}<br />
              <small class="text-muted">{{ previousRevision.description }}</small>
            </dd>
            <dd v-else><em class="text-muted">None (root revision)</em></dd>
            <dt>Child Revisions</dt>
            <dd v-if="childRevisions.length > 0">
              <ul class="list-unstyled">
                <li v-for="child in childRevisions" :key="child.id">
                  Revision {{ child.revision }}: {{ child.description }}
                </li>
              </ul>
            </dd>
            <dd v-else><em class="text-muted">None</em></dd>
          </dl>
        </BCol>
      </BRow>
    </div>
    <template #footer>
      <div class="w-100 d-flex justify-content-between">
        <div>
          <BButton
            v-if="!isCurrentRevision && canEdit"
            variant="warning"
            :disabled="!!submitting"
            @click="$emit('load-revision', revision)"
          >
            <BSpinner v-if="submitting === 'load'" small />
            Load This Revision
          </BButton>
        </div>
        <div class="d-flex gap-2">
          <BButton
            v-if="canEdit"
            variant="success"
            :disabled="!!submitting"
            @click="$emit('create-from', revision)"
          >
            <BSpinner v-if="submitting === 'create'" small />
            Create Branch From Here
          </BButton>
          <BButton variant="secondary" @click="$emit('close')">Close</BButton>
        </div>
      </div>
    </template>
  </BModal>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import type { ScriptRevision } from '@/types/api/script';

const props = defineProps<{
  revision: ScriptRevision | null;
  revisions: ScriptRevision[];
  currentRevisionId: number | null;
  canEdit: boolean;
  submitting: boolean | string;
}>();

defineEmits<{
  'load-revision': [revision: ScriptRevision];
  'create-from': [revision: ScriptRevision];
  close: [];
  hidden: [];
}>();

const modal = ref<InstanceType<typeof BModal>>();

const isCurrentRevision = computed(
  () => props.revision != null && props.revision.id === props.currentRevisionId
);

const previousRevision = computed(() => {
  if (!props.revision?.previous_revision_id) return null;
  return props.revisions.find((r) => r.id === props.revision!.previous_revision_id) ?? null;
});

const childRevisions = computed(() => {
  if (!props.revision) return [];
  return props.revisions.filter((r) => r.previous_revision_id === props.revision!.id);
});

function formatDate(dateString: string | null): string {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleString();
}

function show(): void {
  modal.value?.show();
}

function hide(): void {
  modal.value?.hide();
}

defineExpose({ show, hide });
</script>

<style scoped>
dl {
  margin-bottom: 0;
}
dt {
  font-weight: 600;
  margin-top: 0.5rem;
  color: #dee2e6;
}
dd {
  margin-bottom: 0.5rem;
  color: #adb5bd;
}
</style>
