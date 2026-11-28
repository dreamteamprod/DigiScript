<template>
  <BModal
    ref="modal"
    title="Set Character or Group"
    size="md"
    :ok-title="`Change ${changeCount} Line${changeCount === 1 ? '' : 's'}`"
    :ok-disabled="!canApply"
    @ok.prevent="handleOk"
    @hidden="reset"
  >
    <p class="text-muted small mb-3">Change who is speaking on every selected line.</p>

    <BFormGroup v-if="partOptions.length > 1" label="Apply to" label-for="set-char-part-input">
      <BFormSelect id="set-char-part-input" v-model="selectedPartIndex" :options="partOptions" />
    </BFormGroup>

    <template v-if="combinedDropdown">
      <BFormGroup label="Character / Character Group" label-for="set-char-combined-input">
        <BFormSelect
          id="set-char-combined-input"
          v-model="combinedValue"
          :options="combinedOptions"
        />
      </BFormGroup>
    </template>
    <template v-else>
      <BFormGroup
        v-show="selectedCharacterGroupId == null"
        label="Character"
        label-for="set-char-input"
      >
        <BFormSelect
          id="set-char-input"
          v-model="selectedCharacterId"
          data-testid="set-character-select"
          :options="characterOptions"
        />
      </BFormGroup>
      <BFormGroup
        v-show="selectedCharacterId == null"
        label="Character Group"
        label-for="set-char-group-input"
      >
        <BFormSelect
          id="set-char-group-input"
          v-model="selectedCharacterGroupId"
          :options="characterGroupOptions"
        />
      </BFormGroup>
    </template>

    <p class="sech mt-3 mb-2">What will change</p>
    <div class="set-char-preview">
      <div v-for="(item, index) in preview" :key="index" class="set-char-preview-row">
        <span class="text-muted">{{ item.label }}</span>
        <span v-if="item.kind === 'change'">
          {{ item.before }} <span class="text-muted">&rarr;</span> <strong>{{ newLabel }}</strong>
        </span>
        <span v-else class="text-muted">{{ item.reason }}</span>
      </div>
    </div>
  </BModal>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import { useUserStore } from '@/stores/user';
import { buildCombinedCharacterOptions, type CombinedSelectOption } from '@/js/mruSortUtils';
import type { Character, CharacterGroup } from '@/types/api/show';
import type { CharacterAssignee } from '@/types/bulkEdit';

export interface SelectedLinePreview {
  label: string;
  lineTypeLabel: string;
  parts: Array<{ characterId: number | null; characterGroupId: number | null }>;
}

const props = defineProps<{
  lines: SelectedLinePreview[];
  characters: Character[];
  characterGroups: CharacterGroup[];
}>();

const emit = defineEmits<{
  apply: [payload: CharacterAssignee];
}>();

const userStore = useUserStore();
const modal = ref<InstanceType<typeof BModal>>();

const selectedPartIndex = ref(1);
const selectedCharacterId = ref<number | null>(null);
const selectedCharacterGroupId = ref<number | null>(null);

const combinedDropdown = computed(
  () =>
    !!(userStore.userSettings as { character_combined_dropdown?: boolean })
      .character_combined_dropdown
);

const maxParts = computed(() =>
  Math.min(4, Math.max(1, ...props.lines.map((l) => l.parts.length)))
);
const partOptions = computed(() =>
  Array.from({ length: maxParts.value }, (_, i) => ({ value: i + 1, text: `Part ${i + 1}` }))
);

const characterOptions = computed(() => [
  { value: null, text: 'N/A' },
  ...props.characters.map((c) => ({ value: c.id, text: c.name })),
]);
const characterGroupOptions = computed(() => [
  { value: null, text: 'N/A' },
  ...props.characterGroups.map((g) => ({ value: g.id, text: g.name })),
]);
const combinedOptions = computed<CombinedSelectOption[]>(() =>
  buildCombinedCharacterOptions(props.characters, props.characterGroups, {}, false)
);

const combinedValue = computed<string | null>({
  get() {
    if (selectedCharacterId.value != null) return `c:${selectedCharacterId.value}`;
    if (selectedCharacterGroupId.value != null) return `g:${selectedCharacterGroupId.value}`;
    return null;
  },
  set(val: string | null) {
    if (val == null) {
      selectedCharacterId.value = null;
      selectedCharacterGroupId.value = null;
    } else if (val.startsWith('c:')) {
      selectedCharacterId.value = Number.parseInt(val.slice(2), 10);
      selectedCharacterGroupId.value = null;
    } else if (val.startsWith('g:')) {
      selectedCharacterId.value = null;
      selectedCharacterGroupId.value = Number.parseInt(val.slice(2), 10);
    }
  },
});

function nameFor(characterId: number | null, characterGroupId: number | null): string {
  if (characterId != null) return props.characters.find((c) => c.id === characterId)?.name ?? '—';
  if (characterGroupId != null) {
    return props.characterGroups.find((g) => g.id === characterGroupId)?.name ?? '—';
  }
  return 'N/A';
}

const newLabel = computed(() => nameFor(selectedCharacterId.value, selectedCharacterGroupId.value));

type PreviewRow =
  | { label: string; kind: 'change'; before: string }
  | { label: string; kind: 'skip'; reason: string };

const preview = computed<PreviewRow[]>(() =>
  props.lines.map((line) => {
    const part = line.parts[selectedPartIndex.value - 1];
    if (!part) {
      return { label: line.label, kind: 'skip', reason: `${line.lineTypeLabel} — left alone` };
    }
    return {
      label: line.label,
      kind: 'change',
      before: nameFor(part.characterId, part.characterGroupId),
    };
  })
);

const changeCount = computed(() => preview.value.filter((p) => p.kind === 'change').length);
/** The chosen assignee, narrowed once: exactly one of character / group, or null if
 * neither is picked. The character wins if both were somehow set (the combined dropdown
 * can't do that, but the two separate selects could). `canApply` and `handleOk` both
 * derive from this, so they can never disagree about what is applicable. */
const assignee = computed<CharacterAssignee | null>(() => {
  const partIndex = selectedPartIndex.value;
  if (selectedCharacterId.value != null) {
    return { partIndex, characterId: selectedCharacterId.value, characterGroupId: null };
  }
  if (selectedCharacterGroupId.value != null) {
    return { partIndex, characterId: null, characterGroupId: selectedCharacterGroupId.value };
  }
  return null;
});
const canApply = computed(() => changeCount.value > 0 && assignee.value !== null);

function handleOk(): void {
  if (assignee.value === null || !canApply.value) return;
  emit('apply', assignee.value);
}

function reset(): void {
  selectedPartIndex.value = 1;
  selectedCharacterId.value = null;
  selectedCharacterGroupId.value = null;
}

defineExpose({ show: () => modal.value?.show(), hide: () => modal.value?.hide() });
</script>

<style scoped>
.sech {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.4px;
  text-transform: uppercase;
  color: var(--bs-secondary-color);
}
.set-char-preview {
  padding: 2px 12px;
  background: var(--bs-body-bg);
  /* --bs-border-color isn't redefined by Darkly — see ScriptLineEditor.vue's
     comment — --bs-gray-700 is this theme's own border colour instead. */
  border: 1px solid var(--bs-gray-700);
  border-radius: var(--bs-border-radius);
}
.set-char-preview-row {
  display: flex;
  gap: 10px;
  padding: 6px 0;
  border-bottom: 1px solid var(--bs-gray-700);
  font-size: 0.875rem;
}
.set-char-preview-row:last-child {
  border-bottom: 0;
}
</style>
