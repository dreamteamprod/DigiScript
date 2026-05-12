<template>
  <div class="side-panel" :class="{ open: isOpen }">
    <div v-if="selectedItem" class="panel-content">
      <div class="panel-header">
        <h5>{{ itemName }}</h5>
        <b-button variant="link" size="sm" class="close-btn" @click="$emit('close')">
          <b-icon-x />
        </b-button>
      </div>
      <div class="panel-body">
        <div class="block-info text-muted mb-3">Block: {{ blockRange }}</div>

        <!-- SET Section -->
        <div class="assignment-section mb-4">
          <h6 class="section-header">SET ({{ setSceneName }})</h6>
          <div v-if="setAssignments.length === 0" class="text-muted small">No crew assigned</div>
          <div v-else class="assignment-list">
            <div v-for="assignment in setAssignments" :key="assignment.id" class="assignment-item">
              <span class="crew-name">{{ getCrewDisplayName(assignment.crew_id) }}</span>
              <b-button
                variant="link"
                size="sm"
                class="remove-btn text-danger"
                :disabled="saving"
                @click="removeAssignment(assignment)"
              >
                <b-icon-x />
              </b-button>
            </div>
          </div>
          <div class="add-crew-container mt-2">
            <b-form-select
              v-model="newSetCrewId"
              :options="availableCrewForSet"
              :disabled="saving"
              size="sm"
              class="add-crew-select"
            >
              <template #first>
                <b-form-select-option :value="null" disabled>
                  + Add crew member
                </b-form-select-option>
              </template>
            </b-form-select>
            <b-button
              v-show="newSetCrewId"
              variant="primary"
              size="sm"
              :disabled="saving"
              @click="addSetAssignment"
            >
              Add
            </b-button>
          </div>
        </div>

        <!-- STRIKE Section (only if different from SET) -->
        <div v-if="!isSingleSceneBlock" class="assignment-section mb-4">
          <h6 class="section-header">STRIKE ({{ strikeSceneName }})</h6>
          <div v-if="strikeAssignments.length === 0" class="text-muted small">No crew assigned</div>
          <div v-else class="assignment-list">
            <div
              v-for="assignment in strikeAssignments"
              :key="assignment.id"
              class="assignment-item"
            >
              <span class="crew-name">{{ getCrewDisplayName(assignment.crew_id) }}</span>
              <b-button
                variant="link"
                size="sm"
                class="remove-btn text-danger"
                :disabled="saving"
                @click="removeAssignment(assignment)"
              >
                <b-icon-x />
              </b-button>
            </div>
          </div>
          <div class="add-crew-container mt-2">
            <b-form-select
              v-model="newStrikeCrewId"
              :options="availableCrewForStrike"
              :disabled="saving"
              size="sm"
              class="add-crew-select"
            >
              <template #first>
                <b-form-select-option :value="null" disabled>
                  + Add crew member
                </b-form-select-option>
              </template>
            </b-form-select>
            <b-button
              v-show="newStrikeCrewId"
              variant="primary"
              size="sm"
              :disabled="saving"
              @click="addStrikeAssignment"
            >
              Add
            </b-button>
          </div>
        </div>

        <!-- Combined SET/STRIKE for single-scene blocks -->
        <div v-if="isSingleSceneBlock" class="assignment-section mb-4">
          <h6 class="section-header">STRIKE ({{ strikeSceneName }})</h6>
          <div v-if="strikeAssignments.length === 0" class="text-muted small">No crew assigned</div>
          <div v-else class="assignment-list">
            <div
              v-for="assignment in strikeAssignments"
              :key="assignment.id"
              class="assignment-item"
            >
              <span class="crew-name">{{ getCrewDisplayName(assignment.crew_id) }}</span>
              <b-button
                variant="link"
                size="sm"
                class="remove-btn text-danger"
                :disabled="saving"
                @click="removeAssignment(assignment)"
              >
                <b-icon-x />
              </b-button>
            </div>
          </div>
          <div class="add-crew-container mt-2">
            <b-form-select
              v-model="newStrikeCrewId"
              :options="availableCrewForStrike"
              :disabled="saving"
              size="sm"
              class="add-crew-select"
            >
              <template #first>
                <b-form-select-option :value="null" disabled>
                  + Add crew member
                </b-form-select-option>
              </template>
            </b-form-select>
            <b-button
              v-show="newStrikeCrewId"
              variant="primary"
              size="sm"
              :disabled="saving"
              @click="addStrikeAssignment"
            >
              Add
            </b-button>
          </div>
        </div>

        <!-- Conflict Warnings -->
        <div v-if="conflicts.length > 0" class="conflicts-section">
          <h6 class="section-header text-warning">
            <b-icon-exclamation-triangle class="mr-1" />
            Conflicts
          </h6>
          <div v-for="conflict in conflicts" :key="conflict.key" class="conflict-item small">
            <strong>{{ conflict.crewName }}</strong> has conflict in {{ conflict.sceneName }} ({{
              conflict.itemName
            }}
            {{ conflict.type }})
          </div>
        </div>
      </div>
    </div>
    <div v-else class="panel-placeholder text-muted">Click an allocation bar to view details</div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapGetters, mapActions } from 'vuex';

export default defineComponent({
  name: 'TimelineSidePanel',
  props: {
    selectedItem: {
      type: Object,
      default: null,
    },
    isOpen: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      newSetCrewId: null as number | null,
      newStrikeCrewId: null as number | null,
      saving: false,
    };
  },
  computed: {
    ...mapGetters([
      'ORDERED_SCENES',
      'CREW_LIST',
      'CREW_MEMBER_BY_ID',
      'CREW_ASSIGNMENTS',
      'CREW_ASSIGNMENTS_BY_PROP',
      'CREW_ASSIGNMENTS_BY_SCENERY',
      'CREW_ASSIGNMENTS_BY_SCENE',
      'PROP_BY_ID',
      'SCENERY_BY_ID',
      'ACT_BY_ID',
    ]),
    item(): any {
      if (!this.selectedItem) return null;
      return this.selectedItem.type === 'prop'
        ? (this as any).PROP_BY_ID(this.selectedItem.itemId)
        : (this as any).SCENERY_BY_ID(this.selectedItem.itemId);
    },
    itemExists(): boolean {
      return this.item != null;
    },
    itemName(): string {
      return this.item?.name || 'Unknown';
    },
    setScene(): any {
      if (!this.selectedItem) return null;
      return (this as any).ORDERED_SCENES[this.selectedItem.startScene] || null;
    },
    strikeScene(): any {
      if (!this.selectedItem) return null;
      return (this as any).ORDERED_SCENES[this.selectedItem.endScene] || null;
    },
    setSceneId(): number | null {
      return this.setScene?.id || null;
    },
    strikeSceneId(): number | null {
      return this.strikeScene?.id || null;
    },
    setSceneName(): string {
      if (!this.setScene) return '';
      const act = (this as any).ACT_BY_ID(this.setScene.act);
      return `${act?.name || 'Act'}: ${this.setScene.name}`;
    },
    strikeSceneName(): string {
      if (!this.strikeScene) return '';
      const act = (this as any).ACT_BY_ID(this.strikeScene.act);
      return `${act?.name || 'Act'}: ${this.strikeScene.name}`;
    },
    isSingleSceneBlock(): boolean {
      return this.setSceneId === this.strikeSceneId;
    },
    blockRange(): string {
      if (this.isSingleSceneBlock) {
        return this.setSceneName;
      }
      return `${this.setSceneName} - ${this.strikeSceneName}`;
    },
    itemAssignments(): any[] {
      if (!this.selectedItem) return [];
      return this.selectedItem.type === 'prop'
        ? (this as any).CREW_ASSIGNMENTS_BY_PROP[this.selectedItem.itemId] || []
        : (this as any).CREW_ASSIGNMENTS_BY_SCENERY[this.selectedItem.itemId] || [];
    },
    setAssignments(): any[] {
      return this.itemAssignments.filter(
        (a: any) => a.assignment_type === 'set' && a.scene_id === this.setSceneId
      );
    },
    strikeAssignments(): any[] {
      return this.itemAssignments.filter(
        (a: any) => a.assignment_type === 'strike' && a.scene_id === this.strikeSceneId
      );
    },
    assignedSetCrewIds(): Set<number> {
      return new Set(this.setAssignments.map((a: any) => a.crew_id));
    },
    assignedStrikeCrewIds(): Set<number> {
      return new Set(this.strikeAssignments.map((a: any) => a.crew_id));
    },
    availableCrewForSet(): any[] {
      return (this as any).CREW_LIST.filter((c: any) => !this.assignedSetCrewIds.has(c.id)).map(
        (c: any) => ({
          value: c.id,
          text: this.formatCrewName(c),
        })
      );
    },
    availableCrewForStrike(): any[] {
      return (this as any).CREW_LIST.filter((c: any) => !this.assignedStrikeCrewIds.has(c.id)).map(
        (c: any) => ({
          value: c.id,
          text: this.formatCrewName(c),
        })
      );
    },
    conflicts(): any[] {
      const conflicts: any[] = [];
      const allAssignments = [...this.setAssignments, ...this.strikeAssignments];

      for (const assignment of allAssignments) {
        const sceneAssignments = (this as any).CREW_ASSIGNMENTS_BY_SCENE[assignment.scene_id] || [];
        const otherAssignments = sceneAssignments.filter(
          (a: any) =>
            a.crew_id === assignment.crew_id &&
            a.id !== assignment.id &&
            (a.prop_id !== this.selectedItem?.itemId || this.selectedItem?.type !== 'prop') &&
            (a.scenery_id !== this.selectedItem?.itemId || this.selectedItem?.type !== 'scenery')
        );

        for (const other of otherAssignments) {
          const otherItem =
            other.prop_id != null
              ? (this as any).PROP_BY_ID(other.prop_id)
              : (this as any).SCENERY_BY_ID(other.scenery_id);
          const crew = (this as any).CREW_MEMBER_BY_ID(assignment.crew_id);
          const scene = (this as any).ORDERED_SCENES.find((s: any) => s.id === assignment.scene_id);
          conflicts.push({
            key: `${assignment.id}-${other.id}`,
            crewName: this.formatCrewName(crew),
            sceneName: scene?.name || 'Unknown',
            itemName: otherItem?.name || 'Unknown',
            type: other.assignment_type.toUpperCase(),
          });
        }
      }

      return conflicts;
    },
  },
  watch: {
    selectedItem(): void {
      this.newSetCrewId = null;
      this.newStrikeCrewId = null;
    },
    itemExists(exists: boolean): void {
      if (!exists && this.selectedItem) {
        this.$emit('close');
      }
    },
  },
  methods: {
    ...mapActions(['ADD_CREW_ASSIGNMENT', 'DELETE_CREW_ASSIGNMENT']),
    formatCrewName(crew: any): string {
      if (!crew) return 'Unknown';
      return crew.last_name ? `${crew.first_name} ${crew.last_name}` : crew.first_name;
    },
    getCrewDisplayName(crewId: number): string {
      const crew = (this as any).CREW_MEMBER_BY_ID(crewId);
      return this.formatCrewName(crew);
    },
    async addSetAssignment(): Promise<void> {
      if (!this.newSetCrewId || !this.setSceneId || this.saving) return;

      this.saving = true;
      try {
        const assignment: any = {
          crew_id: this.newSetCrewId,
          scene_id: this.setSceneId,
          assignment_type: 'set',
        };

        if (this.selectedItem.type === 'prop') {
          assignment.prop_id = this.selectedItem.itemId;
        } else {
          assignment.scenery_id = this.selectedItem.itemId;
        }

        const result = await (this as any).ADD_CREW_ASSIGNMENT(assignment);
        if (result.success) {
          this.newSetCrewId = null;
        }
      } finally {
        this.saving = false;
      }
    },
    async addStrikeAssignment(): Promise<void> {
      if (!this.newStrikeCrewId || !this.strikeSceneId || this.saving) return;

      this.saving = true;
      try {
        const assignment: any = {
          crew_id: this.newStrikeCrewId,
          scene_id: this.strikeSceneId,
          assignment_type: 'strike',
        };

        if (this.selectedItem.type === 'prop') {
          assignment.prop_id = this.selectedItem.itemId;
        } else {
          assignment.scenery_id = this.selectedItem.itemId;
        }

        const result = await (this as any).ADD_CREW_ASSIGNMENT(assignment);
        if (result.success) {
          this.newStrikeCrewId = null;
        }
      } finally {
        this.saving = false;
      }
    },
    async removeAssignment(assignment: any): Promise<void> {
      if (this.saving) return;

      const crew = (this as any).CREW_MEMBER_BY_ID(assignment.crew_id);
      const crewName = this.formatCrewName(crew);
      const confirmed = await (this as any).$bvModal.msgBoxConfirm(
        `Remove ${crewName} from this ${assignment.assignment_type.toUpperCase()} assignment?`,
        { okTitle: 'Remove', okVariant: 'danger' }
      );
      if (confirmed) {
        this.saving = true;
        try {
          await (this as any).DELETE_CREW_ASSIGNMENT(assignment.id);
        } finally {
          this.saving = false;
        }
      }
    },
  },
});
</script>

<style scoped lang="scss">
.side-panel {
  width: 0;
  min-width: 0;
  overflow: hidden;
  transition:
    width 0.3s ease,
    min-width 0.3s ease;
  border-left: 1px solid rgba(255, 255, 255, 0.1);
  background: var(--body-background);

  &.open {
    width: 300px;
    min-width: 300px;
  }
}

.panel-content {
  width: 300px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);

  h5 {
    margin: 0;
    font-size: 1rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .close-btn {
    padding: 0;
    line-height: 1;
  }
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.block-info {
  font-size: 0.85rem;
}

.assignment-section {
  .section-header {
    font-size: 0.9rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
    padding-bottom: 0.25rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }
}

.assignment-list {
  margin-bottom: 0.5rem;
}

.assignment-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.05);
  margin-bottom: 0.25rem;

  .crew-name {
    font-size: 0.9rem;
  }

  .remove-btn {
    padding: 0;
    line-height: 1;
  }
}

.add-crew-container {
  display: flex;
  gap: 0.5rem;
  align-items: center;

  .add-crew-select {
    flex: 1;
  }
}

.conflicts-section {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 1rem;

  .section-header {
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
  }

  .conflict-item {
    padding: 0.5rem;
    background: rgba(255, 193, 7, 0.2);
    border-radius: 4px;
    margin-bottom: 0.25rem;
  }
}

.panel-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 1rem;
  text-align: center;
}
</style>
