<template>
  <div>
    <b-form-group label="Cue Type">
      <b-form-select v-model="localCueTypeId" :options="groupCueTypeOptions" :disabled="readonly" />
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
      <div class="cue-list-scroll">
        <div
          v-for="(cue, index) in localCues"
          :key="index"
          class="d-flex align-items-center mb-1 cue-row"
          style="gap: 0.5rem"
          :class="{ 'drag-over': dragOverIndex === index && dragIndex !== index }"
          @dragover.prevent="dragOverIndex = index"
          @dragleave="dragOverIndex = null"
          @drop.prevent="onDrop(index)"
        >
          <span
            draggable="true"
            class="drag-handle"
            @dragstart="onDragStart(index, $event)"
            @dragend="onDragEnd"
          >
            <b-icon-grip-vertical />
          </span>
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
        Use format: start &gt; end (e.g. 1 &gt; 100), max 10000 cues per range.
      </b-form-invalid-feedback>
    </b-form-group>

    <b-button class="mb-2" size="sm" variant="outline-secondary" @click="addSingleCue">
      <b-icon-plus-square-fill /> Add Single Cue
    </b-button>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapGetters } from 'vuex';
import { contrastColor } from 'contrast-color';
import type { CueType } from '@/types/api/cues';

export default defineComponent({
  name: 'CueGroupForm',
  props: {
    cueTypeOptions: {
      required: true,
      type: Array,
    },
    cueTypes: {
      required: true,
      type: Array,
    },
    readonly: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      localCueTypeId: null as number | null,
      localLabelOverride: '',
      localCues: [] as { id?: number; ident: string }[],
      rangeInput: '',
      dragIndex: null as number | null,
      dragOverIndex: null as number | null,
    };
  },
  computed: {
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
      if (!cueType) return '#000000';
      const override = (this.CUE_COLOUR_OVERRIDES as any[]).find(
        (o: any) => o.settings?.id === cueType.id
      );
      return override?.settings?.colour ?? cueType.colour ?? '#000000';
    },
    ...mapGetters(['CUE_COLOUR_OVERRIDES']),
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
  watch: {
    canSave(val: boolean): void {
      this.$emit('validity-change', val);
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
    onDragStart(index: number, event: DragEvent): void {
      this.dragIndex = index;
      const { dataTransfer } = event;
      if (dataTransfer) {
        dataTransfer.effectAllowed = 'move';
        dataTransfer.setData('text/plain', '');
      }
    },
    onDrop(targetIndex: number): void {
      if (this.dragIndex === null || this.dragIndex === targetIndex) {
        this.dragIndex = null;
        this.dragOverIndex = null;
        return;
      }
      const items = [...this.localCues];
      const [removed] = items.splice(this.dragIndex, 1);
      items.splice(targetIndex, 0, removed);
      this.localCues = items;
      this.dragIndex = null;
      this.dragOverIndex = null;
    },
    onDragEnd(): void {
      this.dragIndex = null;
      this.dragOverIndex = null;
    },
    reset(initial?: {
      cueTypeId?: number | null;
      labelOverride?: string;
      cues?: { id?: number; ident: string }[];
    }): void {
      this.localCueTypeId = initial?.cueTypeId ?? null;
      this.localLabelOverride = initial?.labelOverride ?? '';
      this.localCues = initial?.cues ? [...initial.cues] : [];
      this.rangeInput = '';
      this.dragIndex = null;
      this.dragOverIndex = null;
    },
    getFormData(): {
      cueTypeId: number | null;
      labelOverride: string;
      cues: { id?: number; ident: string }[];
    } {
      return {
        cueTypeId: this.localCueTypeId,
        labelOverride: this.localLabelOverride,
        cues: [...this.localCues],
      };
    },
    isValid(): boolean {
      return this.canSave;
    },
  },
});
</script>

<style scoped>
.cue-list-scroll {
  border: 1px solid #dee2e6;
  border-radius: 0.25rem;
  padding: 0.25rem 0.5rem;
  margin-bottom: 0.5rem;
}

.cue-row {
  border-radius: 4px;
  transition: background-color 0.1s ease;
}

.cue-row.drag-over {
  background-color: rgba(0, 123, 255, 0.1);
}

.drag-handle {
  cursor: grab;
  color: #6c757d;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding: 0.25rem;
}

.drag-handle:active {
  cursor: grabbing;
}
</style>
