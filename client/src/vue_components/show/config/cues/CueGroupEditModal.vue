<template>
  <b-modal
    :id="modalId"
    :title="isEdit ? 'Edit Cue Group' : 'Add Cue Group'"
    size="lg"
    hide-footer
    @hidden="onHidden"
  >
    <b-form-group label="Cue Type">
      <b-form-select v-model="localCueTypeId" :options="groupCueTypeOptions" />
    </b-form-group>

    <b-form-group
      label="Label Override"
      description="Optional — leave blank for automatic label based on first/last cue."
    >
      <b-form-input v-model="localLabelOverride" placeholder="e.g. Music Intro" />
    </b-form-group>

    <div v-if="localCueTypeId != null" class="mb-3 d-flex align-items-center">
      <small class="text-muted mr-2">Preview:</small>
      <span
        class="badge"
        :style="{
          backgroundColor: previewColour,
          color: contrastColor({ bgColor: previewColour }),
          padding: '0.3rem 0.5rem',
          fontSize: '0.9rem',
        }"
      >
        {{ previewLabel }}
      </span>
    </div>

    <b-form-group label="Cues">
      <div v-if="localCues.length === 0" class="text-muted small mb-2">
        No cues yet. Add a range or single cue below.
      </div>
      <div
        v-for="(cue, index) in localCues"
        :key="index"
        class="d-flex align-items-center mb-1"
        style="gap: 0.5rem"
      >
        <b-form-input v-model="cue.ident" placeholder="Identifier" />
        <b-button
          size="sm"
          variant="outline-secondary"
          :disabled="index === 0"
          @click="moveUp(index)"
        >
          <b-icon-chevron-up />
        </b-button>
        <b-button
          size="sm"
          variant="outline-secondary"
          :disabled="index === localCues.length - 1"
          @click="moveDown(index)"
        >
          <b-icon-chevron-down />
        </b-button>
        <b-button size="sm" variant="outline-danger" @click="removeCue(index)">
          <b-icon-x />
        </b-button>
      </div>
    </b-form-group>

    <b-form-group label="Add Range" description="e.g. 1 > 100 adds cues 1 through 100">
      <b-input-group>
        <b-form-input
          v-model="rangeInput"
          placeholder="1 > 100"
          :state="rangeState"
          @keyup.enter="addRange"
        />
        <b-input-group-append>
          <b-button variant="outline-primary" :disabled="!canAddRange" @click="addRange">
            Add Range
          </b-button>
        </b-input-group-append>
      </b-input-group>
      <b-form-invalid-feedback :state="rangeState">
        Use format: start &gt; end (e.g. 1 &gt; 100), max 10000 cues.
      </b-form-invalid-feedback>
    </b-form-group>

    <b-button class="mb-3" size="sm" variant="outline-secondary" @click="addSingleCue">
      <b-icon-plus-square-fill /> Add Single Cue
    </b-button>

    <hr />

    <div class="d-flex justify-content-between">
      <b-button v-if="isEdit" variant="danger" :disabled="saving || deleting" @click="onDelete">
        Delete Group
      </b-button>
      <div v-else />
      <div class="d-flex" style="gap: 0.5rem">
        <b-button
          variant="secondary"
          :disabled="saving || deleting"
          @click="$bvModal.hide(modalId)"
        >
          Cancel
        </b-button>
        <b-button variant="primary" :disabled="!canSave || saving || deleting" @click="onSave">
          {{ saving ? 'Saving…' : 'Save Group' }}
        </b-button>
      </div>
    </div>
  </b-modal>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapActions } from 'vuex';
import { contrastColor } from 'contrast-color';
import type { CueGroup, CueType, Cue } from '@/types/api/cues';

export default defineComponent({
  name: 'CueGroupEditModal',
  props: {
    lineId: {
      required: true,
      type: Number,
    },
    lineIndex: {
      required: true,
      type: Number,
    },
    cueTypeOptions: {
      required: true,
      type: Array,
    },
    cueTypes: {
      required: true,
      type: Array,
    },
  },
  data() {
    return {
      isEdit: false,
      groupId: null as number | null,
      localCueTypeId: null as number | null,
      localLabelOverride: '',
      localCues: [] as { id?: number; ident: string }[],
      rangeInput: '',
      saving: false,
      deleting: false,
    };
  },
  computed: {
    modalId(): string {
      return `line_${this.lineIndex}_-group-modal`;
    },
    groupCueTypeOptions(): unknown[] {
      return (this.cueTypeOptions as any[]).filter((o) => o.value !== null);
    },
    previewLabel(): string {
      if (this.localCueTypeId == null) return '';
      const cueType = (this.cueTypes as CueType[]).find((ct) => ct.id === this.localCueTypeId);
      const prefix = cueType?.prefix ?? '';
      if (this.localLabelOverride) return `${prefix} - ${this.localLabelOverride}`;
      if (this.localCues.length === 0) return prefix;
      const first = this.localCues[0].ident;
      const last = this.localCues[this.localCues.length - 1].ident;
      if (first === last) return `${prefix} ${first}`;
      return `${prefix} ${first} - ${prefix} ${last}`;
    },
    previewColour(): string {
      if (this.localCueTypeId == null) return '#000000';
      const cueType = (this.cueTypes as CueType[]).find((ct) => ct.id === this.localCueTypeId);
      return cueType?.colour ?? '#000000';
    },
    rangeState(): boolean | null {
      if (!this.rangeInput.trim()) return null;
      return this.parseRange(this.rangeInput) !== null;
    },
    canAddRange(): boolean {
      return !!this.rangeInput.trim() && this.parseRange(this.rangeInput) !== null;
    },
    canSave(): boolean {
      return (
        this.localCueTypeId != null &&
        this.localCues.length > 0 &&
        this.localCues.every((c) => c.ident.trim() !== '')
      );
    },
  },
  methods: {
    contrastColor,
    parseRange(input: string): number[] | null {
      const match = input.trim().match(/^(\d+)\s*>\s*(\d+)$/);
      if (!match) return null;
      const start = parseInt(match[1], 10);
      const end = parseInt(match[2], 10);
      if (start > end || end - start >= 10000) return null;
      return Array.from({ length: end - start + 1 }, (_, i) => start + i);
    },
    addRange(): void {
      const nums = this.parseRange(this.rangeInput);
      if (!nums) return;
      for (const n of nums) this.localCues.push({ ident: String(n) });
      this.rangeInput = '';
    },
    addSingleCue(): void {
      this.localCues.push({ ident: '' });
    },
    removeCue(index: number): void {
      this.localCues.splice(index, 1);
    },
    moveUp(index: number): void {
      if (index === 0) return;
      const arr = this.localCues;
      const tmp = arr[index - 1];
      this.$set(arr, index - 1, arr[index]);
      this.$set(arr, index, tmp);
    },
    moveDown(index: number): void {
      const arr = this.localCues;
      if (index === arr.length - 1) return;
      const tmp = arr[index];
      this.$set(arr, index, arr[index + 1]);
      this.$set(arr, index + 1, tmp);
    },
    onHidden(): void {
      this.saving = false;
      this.deleting = false;
    },
    async onSave(): Promise<void> {
      if (!this.canSave || this.saving) return;
      this.saving = true;
      const cuesPayload = this.localCues.map((c, i) => ({
        id: c.id,
        ident: c.ident,
        sortOrder: i,
      }));
      if (this.isEdit && this.groupId != null) {
        await (this as any).EDIT_CUE_GROUP({
          groupId: this.groupId,
          labelOverride: this.localLabelOverride || undefined,
          lineId: this.lineId,
          cues: cuesPayload,
        });
      } else {
        await (this as any).ADD_CUE_GROUP({
          cueTypeId: this.localCueTypeId,
          labelOverride: this.localLabelOverride || undefined,
          lineId: this.lineId,
          cues: cuesPayload.map(({ ident, sortOrder }) => ({ ident, sortOrder })),
        });
      }
      (this as any).$bvModal.hide(this.modalId);
    },
    async onDelete(): Promise<void> {
      if (this.deleting || this.groupId == null) return;
      const confirmed = await (this as any).$bvModal.msgBoxConfirm(
        'Delete this cue group and all its cues?',
        { title: 'Delete Cue Group', okVariant: 'danger', okTitle: 'Delete' }
      );
      if (!confirmed) return;
      this.deleting = true;
      await (this as any).DELETE_CUE_GROUP({ groupId: this.groupId, lineId: this.lineId });
      (this as any).$bvModal.hide(this.modalId);
    },
    openCreate(): void {
      this.isEdit = false;
      this.groupId = null;
      this.localCueTypeId = null;
      this.localLabelOverride = '';
      this.localCues = [];
      this.rangeInput = '';
      (this as any).$bvModal.show(this.modalId);
    },
    openEdit(group: CueGroup, cues: Cue[]): void {
      this.isEdit = true;
      this.groupId = group.id;
      this.localCueTypeId = group.cue_type_id;
      this.localLabelOverride = group.label_override ?? '';
      this.localCues = cues.map((c) => ({ id: c.id, ident: c.ident ?? '' }));
      this.rangeInput = '';
      (this as any).$bvModal.show(this.modalId);
    },
    ...mapActions(['ADD_CUE_GROUP', 'EDIT_CUE_GROUP', 'DELETE_CUE_GROUP']),
  },
});
</script>
