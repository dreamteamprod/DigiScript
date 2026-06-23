<template>
  <b-modal :id="modalId" title="Edit Cue Group" size="lg" scrollable @hidden="onHidden">
    <CueGroupForm
      ref="groupForm"
      :cue-type-options="cueTypeOptions"
      :cue-types="cueTypes"
      class="mt-1"
      @validity-change="isFormValid = $event"
    />
    <template #modal-footer>
      <b-button
        v-if="groupId != null"
        variant="danger"
        :disabled="saving || deleting"
        @click="onDelete"
      >
        Delete Group
      </b-button>
      <div v-else />
      <div class="ml-auto d-flex" style="gap: 0.5rem">
        <b-button
          variant="secondary"
          :disabled="saving || deleting"
          @click="$bvModal.hide(modalId)"
        >
          Cancel
        </b-button>
        <b-button variant="primary" :disabled="!isFormValid || saving || deleting" @click="onSave">
          {{ saving ? 'Saving…' : 'Save Group' }}
        </b-button>
      </div>
    </template>
  </b-modal>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapActions } from 'vuex';
import type { CueGroup, Cue } from '@/types/api/cues';
import CueGroupForm from './CueGroupForm.vue';

export default defineComponent({
  name: 'CueGroupEditModal',
  components: { CueGroupForm },
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
      groupId: null as number | null,
      activeLineId: null as number | null,
      saving: false,
      deleting: false,
      isFormValid: false,
    };
  },
  computed: {
    modalId(): string {
      return `line_${this.lineIndex}_-group-modal`;
    },
  },
  methods: {
    onHidden(): void {
      this.saving = false;
      this.deleting = false;
      this.activeLineId = null;
    },
    effectiveLineId(): number {
      return this.activeLineId ?? this.lineId;
    },
    async onSave(): Promise<void> {
      if (!this.isFormValid || this.saving || this.groupId == null) return;
      this.saving = true;
      try {
        const data = (this.$refs.groupForm as any).getFormData();
        const cuesPayload = data.cues.map((c: any, i: number) => ({
          id: c.id,
          ident: c.ident,
          sortOrder: i,
        }));
        await (this as any).EDIT_CUE_GROUP({
          groupId: this.groupId,
          labelOverride: data.labelOverride || undefined,
          lineId: this.effectiveLineId(),
          cues: cuesPayload,
        });
        (this as any).$bvModal.hide(this.modalId);
      } finally {
        this.saving = false;
      }
    },
    async onDelete(): Promise<void> {
      if (this.deleting || this.groupId == null) return;
      const confirmed = await (this as any).$bvModal.msgBoxConfirm(
        'Delete this cue group and all its cues?',
        { title: 'Delete Cue Group', okVariant: 'danger', okTitle: 'Delete' }
      );
      if (!confirmed) return;
      this.deleting = true;
      try {
        await (this as any).DELETE_CUE_GROUP({
          groupId: this.groupId,
          lineId: this.effectiveLineId(),
        });
        (this as any).$bvModal.hide(this.modalId);
      } finally {
        this.deleting = false;
      }
    },
    openEdit(group: CueGroup, cues: Cue[], lineId?: number): void {
      this.groupId = group.id;
      this.activeLineId = lineId ?? null;
      this.isFormValid = true;
      (this.$refs.groupForm as any)?.reset({
        cueTypeId: group.cue_type_id,
        labelOverride: group.label_override ?? '',
        cues: cues.map((c) => ({ id: c.id, ident: c.ident ?? '' })),
      });
      (this as any).$bvModal.show(this.modalId);
    },
    ...mapActions(['EDIT_CUE_GROUP', 'DELETE_CUE_GROUP']),
  },
});
</script>
