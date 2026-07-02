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
      <b-form-group label="Renumber Method" label-for="renumber-method" class="mb-3">
        <b-form-select
          id="renumber-method"
          v-model="method"
          :options="[{ value: 'magicq', text: 'MagicQ (Sequential)' }]"
        />
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
          These cue identifiers did not match the numeric pattern and are skipped by default. Check
          the box to assign them a new identifier.
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
    <div class="d-flex justify-content-end gap-2 mt-3">
      <b-button
        variant="secondary"
        :disabled="submitting"
        @click="$bvModal.hide('cue-renumber-modal')"
      >
        Cancel
      </b-button>
      <b-button
        v-if="step === 2"
        variant="outline-secondary"
        :disabled="submitting"
        @click="step = 1"
      >
        Back
      </b-button>
      <b-button
        v-if="step === 1"
        variant="primary"
        :disabled="selectedTypeIds.length === 0"
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
import { computeRenumber, flattenCuesForType } from '@/js/cueRenumberUtils';
import type { RenumberChange, RenumberUnmatched, RenumberAllMatched } from '@/js/cueRenumberUtils';

export default defineComponent({
  name: 'CueRenumberModal',
  data() {
    return {
      step: 1 as 1 | 2,
      method: 'magicq' as const,
      selectedTypeIds: [] as number[],
      allMatchedByType: new Map<number, RenumberAllMatched[]>(),
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
    hasActiveIdents(): boolean {
      return this.changes.length > 0 || this.unmatched.some((u) => u.include);
    },
    totalOperations(): number {
      return this.changes.length + this.unmatched.filter((u) => u.include).length;
    },
    step2Valid(): boolean {
      for (const typeId of this.selectedTypeIds) {
        const allForType = this.allMatchedByType.get(typeId) ?? [];

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
    onNext(): void {
      this.changes = [];
      this.unmatched = [];
      this.allMatchedByType = new Map();
      for (const typeId of this.selectedTypeIds) {
        const cues = flattenCuesForType((this as any).SCRIPT_CUES, typeId);
        const result = computeRenumber(cues);
        this.allMatchedByType.set(typeId, result.allMatched);
        this.changes.push(...result.changes);
        this.unmatched.push(...result.unmatched);
      }
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
      this.method = 'magicq';
      this.changes = [];
      this.unmatched = [];
      this.allMatchedByType = new Map();
      this.submitting = false;
    },
  },
});
</script>
