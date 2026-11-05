<template>
  <BModal
    ref="modal"
    title="Saving Script"
    size="md"
    :no-header-close="inProgress"
    :no-footer="inProgress"
    :ok-disabled="inProgress"
    :no-close-on-backdrop="inProgress"
    :no-close-on-esc="inProgress"
    ok-only
  >
    <div>
      <b v-if="inProgress">Saving page {{ currentPage }} of {{ totalPages }}</b>
      <template v-else>
        <b v-if="error">{{ error }}</b>
        <b v-else>Finished saving script.</b>
      </template>
    </div>
    <BProgress
      :value="currentPage"
      :max="totalPages || 0"
      :variant="progressVariant"
      show-value
      :animated="inProgress"
    />
  </BModal>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { BModal } from 'bootstrap-vue-next';

/**
 * The save-progress modal shown by both the classic and collaborative script editors —
 * same markup, different source for the progress numbers (a REST per-page loop for the
 * classic editor, the server's own SAVE_PROGRESS broadcast for the collaborative one).
 */
const props = defineProps<{
  inProgress: boolean;
  currentPage: number;
  totalPages: number;
  /** The specific failure reason, or null while in progress / after a clean finish. */
  error: string | null;
}>();

const modal = ref<InstanceType<typeof BModal>>();

const progressVariant = computed(() => {
  if (props.inProgress) return 'primary';
  return props.error ? 'danger' : 'success';
});

defineExpose({
  show: () => modal.value?.show(),
  hide: () => modal.value?.hide(),
});
</script>
