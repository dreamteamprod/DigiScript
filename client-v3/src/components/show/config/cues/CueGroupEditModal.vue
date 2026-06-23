<template>
  <BModal
    ref="modal"
    :title="isEdit ? 'Edit Cue Group' : 'Add Cue Group'"
    size="lg"
    hide-footer
    @hidden="onHidden"
  >
    <BFormGroup label="Cue Type">
      <BFormSelect v-model="localCueTypeId" :options="groupCueTypeOptions" />
    </BFormGroup>

    <BFormGroup
      label="Label Override"
      description="Optional — leave blank for automatic label based on first/last cue."
    >
      <BFormInput v-model="localLabelOverride" placeholder="e.g. Music Intro" />
    </BFormGroup>

    <div v-if="localCueTypeId != null" class="mb-3 d-flex align-items-center gap-2">
      <small class="text-muted">Preview:</small>
      <span
        class="badge"
        :style="{
          backgroundColor: previewColour,
          color: contrastColor(previewColour),
          padding: '0.3rem 0.5rem',
          fontSize: '0.9rem',
        }"
      >
        {{ previewLabel }}
      </span>
    </div>

    <BFormGroup label="Cues">
      <div v-if="localCues.length === 0" class="text-muted small mb-2">
        No cues yet. Add a range or single cue below.
      </div>
      <div
        v-for="(cue, index) in localCues"
        :key="index"
        class="d-flex align-items-center gap-2 mb-1"
      >
        <BFormInput v-model="cue.ident" placeholder="Identifier" />
        <BButton
          size="sm"
          variant="outline-secondary"
          :disabled="index === 0"
          @click="moveUp(index)"
        >
          <IMdiChevronUp />
        </BButton>
        <BButton
          size="sm"
          variant="outline-secondary"
          :disabled="index === localCues.length - 1"
          @click="moveDown(index)"
        >
          <IMdiChevronDown />
        </BButton>
        <BButton size="sm" variant="outline-danger" @click="removeCue(index)">
          <IMdiClose />
        </BButton>
      </div>
    </BFormGroup>

    <BFormGroup label="Add Range" description="e.g. 1 > 100 adds cues 1 through 100">
      <BInputGroup>
        <BFormInput
          v-model="rangeInput"
          placeholder="1 > 100"
          :state="rangeState"
          @keyup.enter="addRange"
        />
        <BButton variant="outline-primary" :disabled="!canAddRange" @click="addRange">
          Add Range
        </BButton>
      </BInputGroup>
      <BFormInvalidFeedback :state="rangeState">
        Use format: start &gt; end (e.g. 1 &gt; 100), max 10000 cues.
      </BFormInvalidFeedback>
    </BFormGroup>

    <BButton class="mb-3" size="sm" variant="outline-secondary" @click="addSingleCue">
      <IMdiPlusBox /> Add Single Cue
    </BButton>

    <hr />

    <div class="d-flex justify-content-between">
      <BButton v-if="isEdit" variant="danger" :disabled="saving || deleting" @click="onDelete">
        Delete Group
      </BButton>
      <div v-else />
      <div class="d-flex gap-2">
        <BButton variant="secondary" :disabled="saving || deleting" @click="modal?.hide()">
          Cancel
        </BButton>
        <BButton variant="primary" :disabled="!canSave || saving || deleting" @click="onSave">
          {{ saving ? 'Saving…' : 'Save Group' }}
        </BButton>
      </div>
    </div>
  </BModal>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import { useScriptStore } from '@/stores/script';
import { useCueDisplay } from '@/composables/useCueDisplay';
import { useConfirm } from '@/composables/useConfirm';
import type { Cue, CueGroup } from '@/types/api/cues';

const props = defineProps<{
  cueTypeOptions: { value: number | null; text: string }[];
}>();

const scriptStore = useScriptStore();
const { confirm } = useConfirm();
const { cueGroupLabel, cueGroupBackgroundColour, contrastColor } = useCueDisplay();

const modal = ref<InstanceType<typeof BModal> | null>(null);

const isEdit = ref(false);
const groupId = ref<number | null>(null);
const lineId = ref<number>(0);
const localCueTypeId = ref<number | null>(null);
const localLabelOverride = ref('');
const localCues = ref<{ id?: number; ident: string }[]>([]);
const rangeInput = ref('');
const saving = ref(false);
const deleting = ref(false);

const groupCueTypeOptions = computed(() => props.cueTypeOptions.filter((o) => o.value !== null));

const previewGroup = computed<CueGroup | null>(() => {
  if (localCueTypeId.value == null) return null;
  return {
    id: groupId.value ?? 0,
    cue_type_id: localCueTypeId.value,
    label_override: localLabelOverride.value || null,
  };
});

const previewCues = computed<Cue[]>(() =>
  localCues.value.map((c, i) => ({
    id: 0,
    cue_type_id: localCueTypeId.value!,
    ident: c.ident,
    group_id: groupId.value ?? 0,
    sort_order: i,
  }))
);

const previewLabel = computed(() => {
  const g = previewGroup.value;
  return g ? cueGroupLabel(g, previewCues.value) : '';
});

const previewColour = computed(() => {
  const g = previewGroup.value;
  return g ? cueGroupBackgroundColour(g) : '#000000';
});

const rangeState = computed<boolean | null>(() => {
  if (!rangeInput.value.trim()) return null;
  return parseRange(rangeInput.value) !== null;
});

const canAddRange = computed(
  () => !!rangeInput.value.trim() && parseRange(rangeInput.value) !== null
);

const canSave = computed(
  () =>
    localCueTypeId.value != null &&
    localCues.value.length > 0 &&
    localCues.value.every((c) => c.ident.trim() !== '')
);

function parseRange(input: string): number[] | null {
  const match = input.trim().match(/^(\d+)\s*>\s*(\d+)$/);
  if (!match) return null;
  const start = parseInt(match[1], 10);
  const end = parseInt(match[2], 10);
  if (start > end || end - start >= 10000) return null;
  return Array.from({ length: end - start + 1 }, (_, i) => start + i);
}

function addRange(): void {
  const nums = parseRange(rangeInput.value);
  if (!nums) return;
  for (const n of nums) localCues.value.push({ ident: String(n) });
  rangeInput.value = '';
}

function addSingleCue(): void {
  localCues.value.push({ ident: '' });
}

function removeCue(index: number): void {
  localCues.value.splice(index, 1);
}

function moveUp(index: number): void {
  if (index === 0) return;
  [localCues.value[index - 1], localCues.value[index]] = [
    localCues.value[index],
    localCues.value[index - 1],
  ];
}

function moveDown(index: number): void {
  if (index === localCues.value.length - 1) return;
  [localCues.value[index], localCues.value[index + 1]] = [
    localCues.value[index + 1],
    localCues.value[index],
  ];
}

function onHidden(): void {
  saving.value = false;
  deleting.value = false;
}

async function onSave(): Promise<void> {
  if (!canSave.value || saving.value) return;
  saving.value = true;
  const cuesPayload = localCues.value.map((c, i) => ({ id: c.id, ident: c.ident, sortOrder: i }));
  if (isEdit.value && groupId.value != null) {
    await scriptStore.editCueGroup({
      groupId: groupId.value,
      labelOverride: localLabelOverride.value || undefined,
      lineId: lineId.value,
      cues: cuesPayload,
    });
  } else {
    await scriptStore.addCueGroup({
      cueTypeId: localCueTypeId.value!,
      labelOverride: localLabelOverride.value || undefined,
      lineId: lineId.value,
      cues: cuesPayload.map(({ ident, sortOrder }) => ({ ident, sortOrder })),
    });
  }
  modal.value?.hide();
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
  await scriptStore.deleteCueGroup({ groupId: groupId.value, lineId: lineId.value });
  modal.value?.hide();
}

function openCreate(targetLineId: number): void {
  isEdit.value = false;
  groupId.value = null;
  lineId.value = targetLineId;
  localCueTypeId.value = null;
  localLabelOverride.value = '';
  localCues.value = [];
  rangeInput.value = '';
  modal.value?.show();
}

function openEdit(group: CueGroup, cues: Cue[], targetLineId: number): void {
  isEdit.value = true;
  groupId.value = group.id;
  lineId.value = targetLineId;
  localCueTypeId.value = group.cue_type_id;
  localLabelOverride.value = group.label_override ?? '';
  localCues.value = cues.map((c) => ({ id: c.id, ident: c.ident ?? '' }));
  rangeInput.value = '';
  modal.value?.show();
}

defineExpose({ openCreate, openEdit });
</script>
