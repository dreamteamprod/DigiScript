<template>
  <div v-if="!loading">
    <BTable :items="tableData" :fields="tableColumns" show-empty>
      <template #cell(revision_id)="data">
        <span>
          {{ data.item.revision }}
          <IMdiCheckboxMarked
            v-if="data.item.revision_id === showStore.currentRevision"
            style="color: #06bc8c; margin-left: 0.25rem"
          />
        </span>
      </template>
      <template #cell(btn)="data">
        <BSpinner v-if="data.item.revision_id === pendingRevisionId" small />
        <BButtonGroup v-else-if="systemStore.isScriptEditor">
          <BButton
            v-if="data.item.data_path != null"
            variant="danger"
            size="sm"
            :disabled="deletingCompiledScript || generatingCompiledScript"
            @click="deleteCompiledScript(data.item)"
          >
            Delete
          </BButton>
          <BButton
            v-else
            variant="success"
            size="sm"
            :disabled="deletingCompiledScript || generatingCompiledScript"
            @click="generateCompiledScript(data.item)"
          >
            Generate
          </BButton>
        </BButtonGroup>
      </template>
    </BTable>
  </div>
  <div v-else class="text-center py-5">
    <BSpinner label="Loading" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import log from 'loglevel';
import { useScriptStore } from '@/stores/script';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import { useConfirm } from '@/composables/useConfirm';
import { toast } from '@/js/toast';

const scriptStore = useScriptStore();
const showStore = useShowStore();
const systemStore = useSystemStore();
const { confirm } = useConfirm();

const loading = ref(true);
const deletingCompiledScript = ref(false);
const generatingCompiledScript = ref(false);
const pendingRevisionId = ref<number | null>(null);

const tableColumns = [
  { key: 'revision_id', label: 'Script Revision' },
  { key: 'created_at', label: 'Created At' },
  { key: 'updated_at', label: 'Updated At' },
  { key: 'data_path', label: 'Data Path' },
  { key: 'btn', label: '' },
];

const tableData = computed(() =>
  showStore.scriptRevisions.map((revision) => {
    const compiled = scriptStore.compiledScripts.find((cs) => cs.revision_id === revision.id);
    return {
      revision_id: revision.id,
      revision: revision.revision,
      created_at: compiled?.created_at ?? null,
      updated_at: compiled?.updated_at ?? null,
      data_path: compiled?.data_path ?? null,
    };
  })
);

async function deleteCompiledScript(item: {
  revision_id: number;
  revision: number | null;
}): Promise<void> {
  const ok = await confirm(
    `Are you sure you want to delete the compiled script for revision ${item.revision}?`,
    { okVariant: 'danger', okTitle: 'Delete' }
  );
  if (!ok) return;
  deletingCompiledScript.value = true;
  pendingRevisionId.value = item.revision_id;
  try {
    await scriptStore.deleteCompiledScript(item.revision_id);
  } catch (e) {
    log.error('Error deleting compiled script:', e);
    toast.error('Unable to delete compiled script!');
  } finally {
    deletingCompiledScript.value = false;
    pendingRevisionId.value = null;
  }
}

async function generateCompiledScript(item: { revision_id: number }): Promise<void> {
  generatingCompiledScript.value = true;
  pendingRevisionId.value = item.revision_id;
  try {
    await scriptStore.generateCompiledScript(item.revision_id);
  } catch (e) {
    log.error('Error generating compiled script:', e);
    toast.error('Unable to compile script revision!');
  } finally {
    generatingCompiledScript.value = false;
    pendingRevisionId.value = null;
  }
}

onMounted(async () => {
  await scriptStore.getCompiledScripts();
  loading.value = false;
});
</script>
