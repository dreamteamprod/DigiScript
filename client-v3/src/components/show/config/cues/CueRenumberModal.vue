<template>
  <BModal
    ref="modal"
    title="Renumber Cues"
    size="xl"
    :no-header-close="submitting"
    :no-close-on-backdrop="submitting"
    :no-close-on-esc="submitting"
    :no-footer="false"
    @hidden="onHidden"
  >
    <!-- Step 1: Configure -->
    <template v-if="step === 1">
      <BFormGroup label="Renumber Method" label-for="renumber-method" class="mb-3">
        <BFormSelect
          id="renumber-method"
          v-model="method"
          :options="[{ value: 'magicq', text: 'MagicQ (Sequential)' }]"
        />
      </BFormGroup>
      <BFormGroup label="Cue Types to Renumber">
        <BFormCheckbox
          v-for="ct in showStore.cueTypes"
          :key="ct.id"
          v-model="selectedTypeIds"
          :value="ct.id"
          class="mb-1"
        >
          <span
            class="badge me-2"
            :style="{ backgroundColor: ct.colour ?? '#000', color: '#fff' }"
            >{{ ct.prefix }}</span
          >
          {{ ct.description ?? '' }}
        </BFormCheckbox>
        <p v-if="showStore.cueTypes.length === 0" class="text-muted mb-0">
          No cue types defined for this show.
        </p>
      </BFormGroup>
    </template>

    <!-- Step 2: Preview -->
    <template v-if="step === 2">
      <h6>Changed Cues</h6>
      <p v-if="changes.length === 0" class="text-muted">
        No cues require renumbering for the selected type(s).
      </p>
      <BTable v-else :items="changes" :fields="changeFields" bordered small class="mb-4">
        <template #cell(cueLabel)="{ item }">
          <span
            class="badge me-1"
            :style="{ backgroundColor: cueTypeColour(item.cue.cue_type_id), color: '#fff' }"
            >{{ cueTypePrefix(item.cue.cue_type_id) }}</span
          >
          {{ item.oldIdent }}
        </template>
        <template #cell(newIdent)="{ item }">
          <BFormInput
            v-model="item.newIdent"
            size="sm"
            :state="
              item.newIdent.trim().length > 0 && item.newIdent.trim().length <= 50 ? null : false
            "
          />
        </template>
      </BTable>

      <template v-if="unmatched.length > 0">
        <h6>Unmatched Cues</h6>
        <p class="text-muted small">
          These cue identifiers did not match the numeric pattern and are skipped by default. Check
          the box to assign them a new identifier.
        </p>
        <BTable :items="unmatched" :fields="unmatchedFields" bordered small>
          <template #cell(include)="{ item }">
            <BFormCheckbox v-model="item.include" />
          </template>
          <template #cell(cueLabel)="{ item }">
            <span
              class="badge me-1"
              :style="{ backgroundColor: cueTypeColour(item.cue.cue_type_id), color: '#fff' }"
              >{{ cueTypePrefix(item.cue.cue_type_id) }}</span
            >
            {{ item.originalIdent || '(empty)' }}
          </template>
          <template #cell(newIdent)="{ item }">
            <BFormInput
              v-model="item.newIdent"
              size="sm"
              :disabled="!item.include"
              :state="
                item.include
                  ? item.newIdent.trim().length > 0 && item.newIdent.trim().length <= 50
                    ? null
                    : false
                  : null
              "
            />
          </template>
        </BTable>
      </template>

      <BAlert v-if="!step2Valid && hasActiveIdents" variant="danger" :model-value="true">
        One or more identifiers are invalid or duplicate within the same cue type.
      </BAlert>
    </template>

    <template #footer>
      <BButton variant="secondary" :disabled="submitting" @click="modal?.hide()">Cancel</BButton>
      <BButton
        v-if="step === 2"
        variant="outline-secondary"
        :disabled="submitting"
        @click="step = 1"
      >
        Back
      </BButton>
      <BButton
        v-if="step === 1"
        variant="primary"
        :disabled="selectedTypeIds.length === 0"
        @click="onNext"
      >
        Next
      </BButton>
      <BButton
        v-if="step === 2"
        variant="primary"
        :disabled="!step2Valid || submitting || totalOperations === 0"
        @click="onConfirm"
      >
        <BSpinner v-if="submitting" small class="me-1" />
        Confirm Renumber
      </BButton>
    </template>
  </BModal>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import { useScriptStore } from '@/stores/script';
import { useShowStore } from '@/stores/show';
import { computeRenumber, useCueRenumber } from '@/composables/useCueRenumber';
import type {
  RenumberChange,
  RenumberUnmatched,
  RenumberAllMatched,
} from '@/composables/useCueRenumber';

const scriptStore = useScriptStore();
const showStore = useShowStore();
const { flattenCuesForType } = useCueRenumber();

const modal = ref<InstanceType<typeof BModal> | null>(null);
const step = ref<1 | 2>(1);
const method = ref<'magicq'>('magicq');
const selectedTypeIds = ref<number[]>([]);
const allMatchedByType = ref<Map<number, RenumberAllMatched[]>>(new Map());
const changes = ref<RenumberChange[]>([]);
const unmatched = ref<RenumberUnmatched[]>([]);
const submitting = ref(false);

const changeFields = [
  { key: 'cueLabel', label: 'Cue' },
  { key: 'oldIdent', label: 'Current Identifier' },
  { key: 'newIdent', label: 'New Identifier' },
];

const unmatchedFields = [
  { key: 'include', label: 'Include' },
  { key: 'cueLabel', label: 'Cue' },
  { key: 'originalIdent', label: 'Current Identifier' },
  { key: 'newIdent', label: 'New Identifier' },
];

function cueTypePrefix(cueTypeId: number | null): string {
  return showStore.cueTypes.find((ct) => ct.id === cueTypeId)?.prefix ?? '';
}

function cueTypeColour(cueTypeId: number | null): string {
  return showStore.cueTypes.find((ct) => ct.id === cueTypeId)?.colour ?? '#000';
}

const hasActiveIdents = computed(
  () => changes.value.length > 0 || unmatched.value.some((u) => u.include)
);

const totalOperations = computed(
  () => changes.value.length + unmatched.value.filter((u) => u.include).length
);

const step2Valid = computed(() => {
  for (const typeId of selectedTypeIds.value) {
    const allForType = allMatchedByType.value.get(typeId) ?? [];

    const changeOverrides = new Map(
      changes.value
        .filter((c) => c.cue.cue_type_id === typeId)
        .map((c) => [c.cue.id, c.newIdent.trim()])
    );
    for (const ident of changeOverrides.values()) {
      if (!ident || ident.length > 50) return false;
    }

    const finalMatchedIdents = allForType.map(
      (m) => changeOverrides.get(m.cue.id) ?? m.computedIdent
    );

    const includedUnmatchedIdents = unmatched.value
      .filter((u) => u.include && u.cue.cue_type_id === typeId)
      .map((u) => u.newIdent.trim());
    if (includedUnmatchedIdents.some((x) => !x || x.length > 50)) return false;

    const all = [...finalMatchedIdents, ...includedUnmatchedIdents];
    if (new Set(all).size !== all.length) return false;
  }
  return true;
});

function onNext(): void {
  changes.value = [];
  unmatched.value = [];
  allMatchedByType.value = new Map();
  for (const typeId of selectedTypeIds.value) {
    const cues = flattenCuesForType(scriptStore.cues, typeId);
    const result = computeRenumber(cues);
    allMatchedByType.value.set(typeId, result.allMatched);
    changes.value.push(...result.changes);
    unmatched.value.push(...result.unmatched);
  }
  step.value = 2;
}

async function onConfirm(): Promise<void> {
  submitting.value = true;
  try {
    const operations = [
      ...changes.value.map((c) => ({ cue_id: c.cue.id, new_ident: c.newIdent.trim() })),
      ...unmatched.value
        .filter((u) => u.include)
        .map((u) => ({ cue_id: u.cue.id, new_ident: u.newIdent.trim() })),
    ];
    await scriptStore.renumberCues(operations);
    modal.value?.hide();
  } finally {
    submitting.value = false;
  }
}

function onHidden(): void {
  step.value = 1;
  selectedTypeIds.value = [];
  method.value = 'magicq';
  changes.value = [];
  unmatched.value = [];
  allMatchedByType.value = new Map();
  submitting.value = false;
}

defineExpose({ show: () => modal.value?.show() });
</script>
