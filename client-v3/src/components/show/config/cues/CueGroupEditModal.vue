<template>
  <BModal ref="modal" title="Edit Cue Group" size="lg" scrollable @hidden="onHidden">
    <CueGroupForm
      ref="groupForm"
      :cue-type-options="cueTypeOptions"
      class="mt-1"
      @update:valid="formValid = $event"
    />
    <template #footer>
      <BButton
        v-if="groupId != null"
        variant="danger"
        :disabled="saving || deleting"
        @click="onDelete"
      >
        Delete Group
      </BButton>
      <div v-else />
      <div class="d-flex gap-2 ms-auto">
        <BButton variant="secondary" :disabled="saving || deleting" @click="modal?.hide()">
          Cancel
        </BButton>
        <BButton variant="primary" :disabled="!formValid || saving || deleting" @click="onSave">
          {{ saving ? 'Saving…' : 'Save Group' }}
        </BButton>
      </div>
    </template>
  </BModal>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import { useScriptStore } from '@/stores/script';
import { useConfirm } from '@/composables/useConfirm';
import type { Cue, CueGroup } from '@/types/api/cues';
import CueGroupForm from './CueGroupForm.vue';

const props = defineProps<{
  cueTypeOptions: { value: number | null; text: string }[];
}>();

const scriptStore = useScriptStore();
const { confirm } = useConfirm();

const modal = ref<InstanceType<typeof BModal> | null>(null);
const groupForm = ref<InstanceType<typeof CueGroupForm> | null>(null);

const groupId = ref<number | null>(null);
const lineId = ref<number>(0);
const formValid = ref(false);
const saving = ref(false);
const deleting = ref(false);

function onHidden(): void {
  saving.value = false;
  deleting.value = false;
}

async function onSave(): Promise<void> {
  if (!formValid.value || saving.value || groupId.value == null || !groupForm.value) return;
  saving.value = true;
  try {
    const data = groupForm.value.getFormData();
    const cuesPayload = data.cues.map((c, i) => ({ id: c.id, ident: c.ident, sortOrder: i }));
    await scriptStore.editCueGroup({
      groupId: groupId.value,
      labelOverride: data.labelOverride || undefined,
      lineId: lineId.value,
      cues: cuesPayload,
    });
    modal.value?.hide();
  } finally {
    saving.value = false;
  }
}

async function onDelete(): Promise<void> {
  if (deleting.value || groupId.value == null) return;
  const confirmed = await confirm('Delete this cue group and all its cues?', {
    title: 'Delete Cue Group',
    okVariant: 'danger',
    okTitle: 'Delete',
  });
  if (!confirmed) return;
  deleting.value = true;
  try {
    await scriptStore.deleteCueGroup({ groupId: groupId.value, lineId: lineId.value });
    modal.value?.hide();
  } finally {
    deleting.value = false;
  }
}

function openEdit(group: CueGroup, cues: Cue[], targetLineId: number): void {
  groupId.value = group.id;
  lineId.value = targetLineId;
  formValid.value = true;
  groupForm.value?.reset({
    cueTypeId: group.cue_type_id,
    labelOverride: group.label_override ?? '',
    cues: cues.map((c) => ({ id: c.id, ident: c.ident ?? '' })),
  });
  modal.value?.show();
}

defineExpose({ openEdit });
</script>
