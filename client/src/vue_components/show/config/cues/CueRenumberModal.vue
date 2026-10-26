<template>
  <b-modal
    id="cue-renumber-modal"
    ref="cue-renumber-modal"
    title="Renumber Cues"
    size="xl"
    :hide-header-close="submitting"
    :no-close-on-backdrop="submitting"
    :no-close-on-esc="submitting"
    hide-footer
    @hidden="onHidden"
  >
    <!-- Step 1: Configure -->
    <template v-if="step === 1">
      <b-form-group label="MagicQ Cue Stack CSV (before renumber)" class="mb-3">
        <input ref="csvFileInput" type="file" accept=".csv" class="d-none" @change="onCsvUpload" />
        <div
          class="csv-dropzone"
          :class="{ 'csv-dropzone--over': isDragOver, 'csv-dropzone--loaded': csvParsed }"
          role="button"
          tabindex="0"
          @click="$refs.csvFileInput.click()"
          @keydown.enter.space.prevent="$refs.csvFileInput.click()"
          @dragover.prevent="isDragOver = true"
          @dragleave.prevent="isDragOver = false"
          @drop.prevent="onDrop"
        >
          <template v-if="!csvParsed && !csvError">
            <span class="csv-dropzone__icon text-muted">&#8679;</span>
            <div class="csv-dropzone__label">
              <span class="font-weight-bold">Click to browse</span> or drag &amp; drop your MagicQ
              cue stack CSV here
            </div>
          </template>
          <template v-else-if="csvParsed">
            <span class="csv-dropzone__icon text-success">&#10003;</span>
            <div>
              <div class="font-weight-bold text-success">{{ csvFileName }}</div>
              <small class="text-muted">{{ csvRowCount }} cues loaded — click to replace</small>
            </div>
          </template>
          <template v-else>
            <span class="csv-dropzone__icon text-danger">&#9888;</span>
            <div>
              <div class="font-weight-bold text-danger">
                {{ csvFileName || 'Upload failed' }}
              </div>
              <small class="text-danger">{{ csvError }}</small>
            </div>
          </template>
        </div>
      </b-form-group>
      <b-form-group label="Cue Types to Renumber">
        <b-form-checkbox
          v-for="ct in CUE_TYPES"
          :key="ct.id"
          v-model="selectedTypeIds"
          :value="ct.id"
          class="mb-1"
        >
          <span
            class="badge mr-2"
            :style="{ backgroundColor: ct.colour || '#000', color: '#fff' }"
            >{{ ct.prefix }}</span
          >
          {{ ct.description || '' }}
        </b-form-checkbox>
        <p v-if="CUE_TYPES.length === 0" class="text-muted mb-0">
          No cue types defined for this show.
        </p>
      </b-form-group>
    </template>

    <!-- Step 2: Preview -->
    <template v-if="step === 2">
      <h6>Changed Cues</h6>
      <p v-if="changes.length === 0" class="text-muted">
        No cues require renumbering for the selected type(s).
      </p>
      <b-table v-else :items="changes" :fields="changeFields" bordered small class="mb-4">
        <template #cell(cueLabel)="{ item }">
          <span
            class="badge mr-1"
            :style="{ backgroundColor: cueTypeColour(item.cue.cue_type_id), color: '#fff' }"
            >{{ cueTypePrefix(item.cue.cue_type_id) }}</span
          >
          {{ item.oldIdent }}
        </template>
        <template #cell(newIdent)="{ item }">
          <b-form-input
            v-model="item.newIdent"
            size="sm"
            :state="
              item.newIdent.trim().length > 0 && item.newIdent.trim().length <= 50 ? null : false
            "
          />
        </template>
      </b-table>

      <template v-if="unmatched.length > 0">
        <h6>Unmatched Cues</h6>
        <p class="text-muted small">
          These cues are skipped by default — either their identifier was not found in the uploaded
          CSV, or it has no numeric prefix. Check the box to assign them a new identifier.
        </p>
        <b-table :items="unmatched" :fields="unmatchedFields" bordered small>
          <template #cell(include)="{ item }">
            <b-form-checkbox v-model="item.include" />
          </template>
          <template #cell(cueLabel)="{ item }">
            <span
              class="badge mr-1"
              :style="{ backgroundColor: cueTypeColour(item.cue.cue_type_id), color: '#fff' }"
              >{{ cueTypePrefix(item.cue.cue_type_id) }}</span
            >
            {{ item.originalIdent || '(empty)' }}
          </template>
          <template #cell(newIdent)="{ item }">
            <b-form-input
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
        </b-table>
      </template>

      <b-alert v-if="!step2Valid && hasActiveIdents" variant="danger" show>
        One or more identifiers are invalid or duplicate within the same cue type.
      </b-alert>
    </template>

    <!-- Custom footer (always rendered) -->
    <div class="d-flex justify-content-end mt-3">
      <b-button
        variant="secondary"
        :disabled="submitting"
        class="mr-2"
        @click="$bvModal.hide('cue-renumber-modal')"
      >
        Cancel
      </b-button>
      <b-button
        v-if="step === 2"
        variant="outline-secondary"
        :disabled="submitting"
        class="mr-2"
        @click="step = 1"
      >
        Back
      </b-button>
      <b-button
        v-if="step === 1"
        variant="primary"
        :disabled="!csvParsed || selectedTypeIds.length === 0"
        @click="onNext"
      >
        Next
      </b-button>
      <b-button
        v-if="step === 2"
        variant="primary"
        :disabled="!step2Valid || submitting || totalOperations === 0"
        @click="onConfirm"
      >
        <b-spinner v-if="submitting" small class="mr-1" />
        Confirm Renumber
      </b-button>
    </div>
  </b-modal>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapGetters, mapActions } from 'vuex';
import { computeRenumber, flattenCuesForType, parseMagicQCsv } from '@/js/cueRenumberUtils';
import type { RenumberChange, RenumberUnmatched, RenumberAllMatched } from '@/js/cueRenumberUtils';

export default defineComponent({
  name: 'CueRenumberModal',
  data() {
    return {
      step: 1 as 1 | 2,
      selectedTypeIds: [] as number[],
      csvMapping: new Map<number, number>(),
      csvRowCount: 0,
      csvFileName: '',
      csvError: '',
      isDragOver: false,
      allMatched: [] as RenumberAllMatched[],
      changes: [] as RenumberChange[],
      unmatched: [] as RenumberUnmatched[],
      submitting: false,
      changeFields: [
        { key: 'cueLabel', label: 'Cue' },
        { key: 'oldIdent', label: 'Current Identifier' },
        { key: 'newIdent', label: 'New Identifier' },
      ],
      unmatchedFields: [
        { key: 'include', label: 'Include' },
        { key: 'cueLabel', label: 'Cue' },
        { key: 'originalIdent', label: 'Current Identifier' },
        { key: 'newIdent', label: 'New Identifier' },
      ],
    };
  },
  computed: {
    ...mapGetters(['SCRIPT_CUES', 'CUE_TYPES']),
    csvParsed(): boolean {
      return this.csvRowCount > 0;
    },
    hasActiveIdents(): boolean {
      return this.changes.length > 0 || this.unmatched.some((u) => u.include);
    },
    totalOperations(): number {
      return this.changes.length + this.unmatched.filter((u) => u.include).length;
    },
    step2Valid(): boolean {
      for (const typeId of this.selectedTypeIds) {
        const allForType = this.allMatched.filter((m) => m.cue.cue_type_id === typeId);

        const changeOverrides = new Map<number, string>(
          this.changes
            .filter((c) => c.cue.cue_type_id === typeId)
            .map((c) => [c.cue.id, c.newIdent.trim()])
        );
        for (const ident of changeOverrides.values()) {
          if (!ident || ident.length > 50) return false;
        }

        const finalMatchedIdents = allForType.map(
          (m) => changeOverrides.get(m.cue.id) ?? m.computedIdent
        );

        const includedUnmatchedIdents = this.unmatched
          .filter((u) => u.include && u.cue.cue_type_id === typeId)
          .map((u) => u.newIdent.trim());
        if (includedUnmatchedIdents.some((x) => !x || x.length > 50)) return false;

        const all = [...finalMatchedIdents, ...includedUnmatchedIdents];
        if (new Set(all).size !== all.length) return false;
      }
      return true;
    },
  },
  methods: {
    ...mapActions(['RENUMBER_CUES']),
    cueTypePrefix(cueTypeId: number | null): string {
      return (this as any).CUE_TYPES.find((ct: any) => ct.id === cueTypeId)?.prefix ?? '';
    },
    cueTypeColour(cueTypeId: number | null): string {
      return (this as any).CUE_TYPES.find((ct: any) => ct.id === cueTypeId)?.colour ?? '#000';
    },
    processFile(file: File): void {
      this.csvMapping = new Map();
      this.csvRowCount = 0;
      this.csvError = '';
      this.csvFileName = file.name;

      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        const mapping = parseMagicQCsv(text);
        if (mapping.size === 0) {
          this.csvError =
            'Could not find a "Cue id" column in this file. Please check it is a valid MagicQ cue stack export.';
        } else {
          this.csvMapping = mapping;
          this.csvRowCount = mapping.size;
        }
      };
      reader.onerror = () => {
        this.csvError = 'Failed to read the file. Please try again.';
      };
      reader.readAsText(file);
    },
    onCsvUpload(event: Event): void {
      const input = event.target as HTMLInputElement | null;
      const file = input?.files?.[0];
      if (file) this.processFile(file);
    },
    onDrop(event: DragEvent): void {
      this.isDragOver = false;
      const file = event.dataTransfer?.files?.[0];
      if (file) this.processFile(file);
    },
    onNext(): void {
      this.changes = [];
      this.unmatched = [];
      this.allMatched = [];
      const allCues = this.selectedTypeIds.flatMap((typeId: number) =>
        flattenCuesForType((this as any).SCRIPT_CUES, typeId)
      );
      const result = computeRenumber(allCues, this.csvMapping);
      this.allMatched = result.allMatched;
      this.changes = result.changes;
      this.unmatched = result.unmatched;
      this.step = 2;
    },
    async onConfirm(): Promise<void> {
      this.submitting = true;
      try {
        const operations = [
          ...this.changes.map((c) => ({ cue_id: c.cue.id, new_ident: c.newIdent.trim() })),
          ...this.unmatched
            .filter((u) => u.include)
            .map((u) => ({ cue_id: u.cue.id, new_ident: u.newIdent.trim() })),
        ];
        await (this as any).RENUMBER_CUES(operations);
        this.$bvModal.hide('cue-renumber-modal');
      } finally {
        this.submitting = false;
      }
    },
    onHidden(): void {
      this.step = 1;
      this.selectedTypeIds = [];
      this.csvMapping = new Map();
      this.csvRowCount = 0;
      this.csvFileName = '';
      this.csvError = '';
      this.isDragOver = false;
      const input = this.$refs.csvFileInput as HTMLInputElement | null;
      if (input) input.value = '';
      this.changes = [];
      this.unmatched = [];
      this.allMatched = [];
      this.submitting = false;
    },
  },
});
</script>

<style scoped>
.csv-dropzone {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.25rem 1rem;
  border: 2px dashed #6c757d;
  border-radius: 0.375rem;
  cursor: pointer;
  transition:
    border-color 0.15s,
    background-color 0.15s;
  user-select: none;
}

.csv-dropzone:hover,
.csv-dropzone:focus {
  border-color: #007bff;
  background-color: rgba(0, 123, 255, 0.05);
  outline: none;
}

.csv-dropzone--over {
  border-color: #007bff;
  background-color: rgba(0, 123, 255, 0.1);
}

.csv-dropzone--loaded {
  border-style: solid;
  border-color: #28a745;
}

.csv-dropzone__icon {
  font-size: 2rem;
  flex-shrink: 0;
  line-height: 1;
}

.csv-dropzone__label {
  color: #6c757d;
  font-size: 0.9rem;
}
</style>
