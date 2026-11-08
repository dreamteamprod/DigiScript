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
      <BFormGroup label="MagicQ Cue Stack CSV (before renumber)" class="mb-3">
        <input ref="csvFileInput" type="file" accept=".csv" class="d-none" @change="onCsvUpload" />
        <div
          class="csv-dropzone"
          :class="{ 'csv-dropzone--over': isDragOver, 'csv-dropzone--loaded': csvParsed }"
          role="button"
          tabindex="0"
          @click="csvFileInput!.click()"
          @keydown.enter.space.prevent="csvFileInput!.click()"
          @dragover.prevent="isDragOver = true"
          @dragleave.prevent="isDragOver = false"
          @drop.prevent="onDrop"
        >
          <template v-if="!csvParsed && !csvError">
            <i-mdi-file-upload class="csv-dropzone__icon text-muted" />
            <div class="csv-dropzone__label">
              <span class="fw-semibold">Click to browse</span> or drag &amp; drop your MagicQ cue
              stack CSV here
            </div>
          </template>
          <template v-else-if="csvParsed">
            <i-mdi-check-circle class="csv-dropzone__icon text-success" />
            <div>
              <div class="fw-semibold text-success">{{ csvFileName }}</div>
              <small class="text-muted">{{ csvRowCount }} cues loaded — click to replace</small>
            </div>
          </template>
          <template v-else>
            <i-mdi-alert-circle class="csv-dropzone__icon text-danger" />
            <div>
              <div class="fw-semibold text-danger">{{ csvFileName || 'Upload failed' }}</div>
              <small class="text-danger">{{ csvError }}</small>
            </div>
          </template>
        </div>
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
          These cues are skipped by default — either their identifier was not found in the uploaded
          CSV, or it has no numeric prefix. Check the box to assign them a new identifier.
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
        :disabled="!csvParsed || selectedTypeIds.length === 0"
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
import { computeRenumber, parseMagicQCsv, useCueRenumber } from '@/composables/useCueRenumber';
import type {
  RenumberChange,
  RenumberUnmatched,
  RenumberAllMatched,
} from '@/composables/useCueRenumber';

const scriptStore = useScriptStore();
const showStore = useShowStore();
const { flattenCuesForType } = useCueRenumber();

const modal = ref<InstanceType<typeof BModal> | null>(null);
const csvFileInput = ref<HTMLInputElement | null>(null);
const step = ref<1 | 2>(1);
const selectedTypeIds = ref<number[]>([]);
const csvMapping = ref<Map<number, number>>(new Map());
const csvRowCount = ref(0);
const csvFileName = ref('');
const csvError = ref('');
const isDragOver = ref(false);
const allMatched = ref<RenumberAllMatched[]>([]);
const changes = ref<RenumberChange[]>([]);
const unmatched = ref<RenumberUnmatched[]>([]);
const submitting = ref(false);

const csvParsed = computed(() => csvRowCount.value > 0);

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

function processFile(file: File): void {
  csvMapping.value = new Map();
  csvRowCount.value = 0;
  csvError.value = '';
  csvFileName.value = file.name;

  const reader = new FileReader();
  reader.onload = (e) => {
    const text = e.target?.result as string;
    const mapping = parseMagicQCsv(text);
    if (mapping.size === 0) {
      csvError.value =
        'Could not find a "Cue id" column in this file. Please check it is a valid MagicQ cue stack export.';
    } else {
      csvMapping.value = mapping;
      csvRowCount.value = mapping.size;
    }
  };
  reader.onerror = () => {
    csvError.value = 'Failed to read the file. Please try again.';
  };
  reader.readAsText(file);
}

function onCsvUpload(event: Event): void {
  const input = event.target as HTMLInputElement | null;
  const file = input?.files?.[0];
  if (file) processFile(file);
}

function onDrop(event: DragEvent): void {
  isDragOver.value = false;
  const file = event.dataTransfer?.files?.[0];
  if (file) processFile(file);
}

const hasActiveIdents = computed(
  () => changes.value.length > 0 || unmatched.value.some((u) => u.include)
);

const totalOperations = computed(
  () => changes.value.length + unmatched.value.filter((u) => u.include).length
);

const step2Valid = computed(() => {
  for (const typeId of selectedTypeIds.value) {
    const allForType = allMatched.value.filter((m) => m.cue.cue_type_id === typeId);

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
  allMatched.value = [];
  const allCues = selectedTypeIds.value.flatMap((typeId) =>
    flattenCuesForType(scriptStore.cues, typeId)
  );
  const result = computeRenumber(allCues, csvMapping.value);
  allMatched.value = result.allMatched;
  changes.value = result.changes;
  unmatched.value = result.unmatched;
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
  csvMapping.value = new Map();
  csvRowCount.value = 0;
  csvFileName.value = '';
  csvError.value = '';
  isDragOver.value = false;
  if (csvFileInput.value) csvFileInput.value.value = '';
  changes.value = [];
  unmatched.value = [];
  allMatched.value = [];
  submitting.value = false;
}

defineExpose({ show: () => modal.value?.show() });
</script>

<style scoped>
.csv-dropzone {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.25rem 1rem;
  border: 2px dashed var(--bs-border-color);
  border-radius: var(--bs-border-radius);
  cursor: pointer;
  transition:
    border-color 0.15s,
    background-color 0.15s;
  user-select: none;
}

.csv-dropzone:hover,
.csv-dropzone:focus-visible {
  border-color: var(--bs-primary);
  background-color: rgba(var(--bs-primary-rgb), 0.05);
  outline: none;
}

.csv-dropzone--over {
  border-color: var(--bs-primary);
  background-color: rgba(var(--bs-primary-rgb), 0.1);
}

.csv-dropzone--loaded {
  border-style: solid;
  border-color: var(--bs-success);
}

.csv-dropzone__icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.csv-dropzone__label {
  color: var(--bs-secondary-color);
  font-size: 0.9rem;
}
</style>
