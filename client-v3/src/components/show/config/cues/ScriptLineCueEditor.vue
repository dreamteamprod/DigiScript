<template>
  <div ref="lineContainer" style="margin: 0; padding: 0 0 0.2rem">
    <!-- Act/scene heading -->
    <BContainer v-if="needsActSceneLabelValue" fluid class="mx-0" style="margin: 0; padding: 0">
      <BRow>
        <BCol cols="3" />
        <BCol>
          <h4>{{ actLabel }} - {{ sceneLabel }}</h4>
        </BCol>
      </BRow>
    </BContainer>

    <!-- Main line row -->
    <BContainer fluid class="mx-0" style="margin: 0; padding: 0">
      <BRow
        class="line-row"
        :class="{
          'stage-direction': line.line_type === LINE_TYPES.STAGE_DIRECTION,
        }"
      >
        <!-- Cue column -->
        <BCol cols="3" class="cue-column">
          <template v-if="line.line_type !== LINE_TYPES.SPACING">
            <BButtonGroup>
              <BButton
                v-for="cue in individualCues"
                :key="cue.id"
                class="cue-button"
                :disabled="!systemStore.isCueEditor"
                :style="{
                  backgroundColor: cueBackgroundColour(cue),
                  color: contrastColor(cueBackgroundColour(cue)),
                }"
                @click.stop="openEditForm(cue)"
              >
                {{ cueLabel(cue) }}
              </BButton>
              <BButton
                v-for="grp in lineGroups"
                :key="`group_${grp.group.id}`"
                class="cue-button cue-group-btn"
                :disabled="!systemStore.isCueEditor"
                :style="{
                  backgroundColor: cueGroupBackgroundColour(grp.group),
                  color: contrastColor(cueGroupBackgroundColour(grp.group)),
                }"
                @click.stop="openEditGroup(grp.group, grp.cues)"
              >
                {{ cueGroupLabel(grp.group, grp.cues) }}
              </BButton>
              <BButton
                v-if="systemStore.isCueEditor"
                class="cue-button add-cue-btn"
                :disabled="isLineCut"
                @click.stop="openNewForm"
              >
                <IMdiPlusBox style="color: #06bc8c" />
              </BButton>
            </BButtonGroup>
          </template>
        </BCol>

        <!-- Line content -->
        <template v-if="line.line_type === LINE_TYPES.DIALOGUE">
          <BCol>
            <BRow v-if="needsHeadingsAnyValue">
              <BCol
                v-for="(part, index) in line.line_parts"
                :key="`heading_${lineIndex}_part_${index}`"
                :style="{ textAlign: textAlign }"
              >
                <b v-if="needsHeadingsValue[index]">
                  <template v-if="part.character_id != null">
                    {{ characters.find((c) => c.id === part.character_id)?.name }}
                  </template>
                  <template v-else>
                    {{ characterGroups.find((g) => g.id === part.character_group_id)?.name }}
                  </template>
                </b>
                <b v-else>&nbsp;</b>
              </BCol>
            </BRow>
            <BRow>
              <BCol
                v-for="(part, index) in line.line_parts"
                :key="`line_${lineIndex}_part_${index}`"
                :style="{ textAlign: textAlign }"
              >
                <p class="viewable-line" :class="{ 'cut-line-part': cuts.includes(part.id) }">
                  {{ part.line_text }}
                </p>
              </BCol>
            </BRow>
          </BCol>
        </template>

        <template v-else-if="line.line_type === LINE_TYPES.STAGE_DIRECTION">
          <BCol :style="{ textAlign: textAlign }">
            <i class="viewable-line" :style="sdStylingWithCuts">
              <template v-if="sdStyle?.text_format === 'upper'">
                {{ line.line_parts[0]?.line_text?.toUpperCase() }}
              </template>
              <template v-else-if="sdStyle?.text_format === 'lower'">
                {{ line.line_parts[0]?.line_text?.toLowerCase() }}
              </template>
              <template v-else>
                {{ line.line_parts[0]?.line_text }}
              </template>
            </i>
          </BCol>
        </template>

        <template v-else-if="line.line_type === LINE_TYPES.CUE_LINE">
          <BCol>
            <BAlert variant="secondary" :model-value="true" class="text-muted small mb-0">
              Cue Line
            </BAlert>
          </BCol>
        </template>

        <template v-else-if="line.line_type === LINE_TYPES.SPACING">
          <BCol>
            <BAlert variant="secondary" :model-value="true" class="text-muted small mb-0">
              Spacing Line
            </BAlert>
          </BCol>
        </template>
      </BRow>
    </BContainer>

    <!-- Add Cue Modal (tabs: Individual Cue / Cue Group) -->
    <BModal ref="newCueModal" title="Add Cue" scrollable @hidden="resetNewForm">
      <BTabs v-model:index="activeTab" class="mt-1">
        <BTab title="Individual Cue">
          <BForm class="mt-3" @submit.stop.prevent="onSubmitNew">
            <BFormGroup label="Cue Type" label-for="new-cue-type">
              <BFormSelect
                id="new-cue-type"
                v-model="v$.newFormState.cueType.$model"
                :options="cueTypeOptions"
                :state="newFieldState('cueType')"
              />
              <BFormInvalidFeedback>This is a required field.</BFormInvalidFeedback>
            </BFormGroup>
            <BFormGroup label="Identifier" label-for="new-cue-ident">
              <BFormInput
                id="new-cue-ident"
                v-model="v$.newFormState.ident.$model"
                :state="newFieldState('ident')"
              />
              <BFormInvalidFeedback>This is a required field.</BFormInvalidFeedback>
              <BFormText v-if="isDuplicateNewCue" class="text-warning">
                A cue with this identifier already exists for this cue type.
              </BFormText>
            </BFormGroup>
            <!-- Line preview -->
            <template
              v-if="
                line.line_type === LINE_TYPES.DIALOGUE ||
                line.line_type === LINE_TYPES.STAGE_DIRECTION
              "
            >
              <hr />
              <template v-if="line.line_type === LINE_TYPES.DIALOGUE">
                <p v-for="part in line.line_parts" :key="part.id" class="viewable-line">
                  {{ part.line_text }}
                </p>
              </template>
              <i v-else class="viewable-line">{{ line.line_parts[0]?.line_text }}</i>
            </template>
          </BForm>
        </BTab>
        <BTab title="Cue Group">
          <CueGroupForm
            ref="newGroupForm"
            :cue-type-options="cueTypeOptions"
            class="mt-3"
            @update:valid="groupFormValid = $event"
          />
        </BTab>
      </BTabs>
      <template #footer>
        <BButton variant="secondary" @click="newCueModal?.hide()">Cancel</BButton>
        <template v-if="activeTab === 0">
          <BButton
            variant="primary"
            :disabled="v$.newFormState.$invalid || submittingNewCue"
            @click="onSubmitNew"
          >
            {{ submittingNewCue ? 'Adding…' : 'Add Cue' }}
          </BButton>
        </template>
        <template v-else>
          <BButton
            variant="primary"
            :disabled="!groupFormValid || submittingGroup"
            @click="onSubmitGroup"
          >
            {{ submittingGroup ? 'Saving…' : 'Save Group' }}
          </BButton>
        </template>
      </template>
    </BModal>

    <!-- Cue Group Modal (create + edit) -->
    <CueGroupEditModal ref="groupModal" :cue-type-options="cueTypeOptions" />

    <!-- Edit Cue Modal -->
    <BModal
      ref="editCueModal"
      title="Edit Cue"
      :ok-disabled="v$.editFormState.$invalid || submittingEditCue"
      @hidden="resetEditForm"
      @ok="onSubmitEdit"
    >
      <template #footer>
        <BButton
          variant="secondary"
          :disabled="submittingEditCue || deletingCue"
          @click="editCueModal?.hide()"
        >
          Cancel
        </BButton>
        <BButton variant="danger" :disabled="submittingEditCue || deletingCue" @click="deleteCue">
          Delete
        </BButton>
        <BButton
          variant="primary"
          :disabled="v$.editFormState.$invalid || submittingEditCue || deletingCue"
          @click="onSubmitEdit"
        >
          Save
        </BButton>
      </template>
      <BForm @submit.stop.prevent="onSubmitEdit">
        <BFormGroup label="Cue Type" label-for="edit-cue-type">
          <BFormSelect
            id="edit-cue-type"
            v-model="v$.editFormState.cueType.$model"
            :options="cueTypeOptions"
            :state="editFieldState('cueType')"
          />
          <BFormInvalidFeedback>This is a required field.</BFormInvalidFeedback>
        </BFormGroup>
        <BFormGroup label="Identifier" label-for="edit-cue-ident">
          <BFormInput
            id="edit-cue-ident"
            v-model="v$.editFormState.ident.$model"
            :state="editFieldState('ident')"
          />
          <BFormInvalidFeedback>This is a required field.</BFormInvalidFeedback>
          <BFormText v-if="isDuplicateEditCue" class="text-warning">
            A cue with this identifier already exists for this cue type.
          </BFormText>
        </BFormGroup>
      </BForm>
    </BModal>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { BModal } from 'bootstrap-vue-next';
import { useVuelidate } from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import { useScriptDisplay } from '@/composables/useScriptDisplay';
import { useCueDisplay } from '@/composables/useCueDisplay';
import { useScriptNavigation } from '@/composables/useScriptNavigation';
import { useScriptStore } from '@/stores/script';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import { useUserStore } from '@/stores/user';
import { useConfirm } from '@/composables/useConfirm';
import { isWholeLineCut } from '@/js/scriptUtils';
import { LINE_TYPES } from '@/constants/lineTypes';
import type { ScriptLine } from '@/types/api/script';
import type { Cue, CueGroup, CueType } from '@/types/api/cues';
import type { Act, Scene, Character, CharacterGroup } from '@/types/api/show';
import CueGroupEditModal from './CueGroupEditModal.vue';
import CueGroupForm from './CueGroupForm.vue';

const props = defineProps<{
  line: ScriptLine;
  lineIndex: number;
  previousLine: ScriptLine | null;
  acts: Act[];
  scenes: Scene[];
  characters: Character[];
  characterGroups: CharacterGroup[];
  cues: Cue[];
  cueTypes: CueType[];
  cuts: (number | null)[];
}>();

const scriptStore = useScriptStore();
const showStore = useShowStore();
const systemStore = useSystemStore();
const userStore = useUserStore();
const { confirm } = useConfirm();

const { getStageDirectionStyle, stageDirectionStyling, scriptTextAlign } = useScriptDisplay();
const { cueLabel, cueBackgroundColour, cueGroupLabel, cueGroupBackgroundColour, contrastColor } =
  useCueDisplay();
const { needsHeadings, needsActSceneLabel } = useScriptNavigation();

// Modal refs
const newCueModal = ref<InstanceType<typeof BModal> | null>(null);
const editCueModal = ref<InstanceType<typeof BModal> | null>(null);
const groupModal = ref<InstanceType<typeof CueGroupEditModal> | null>(null);
const newGroupForm = ref<InstanceType<typeof CueGroupForm> | null>(null);
const lineContainer = ref<HTMLElement | null>(null);

// Form state
const newFormState = ref({
  cueType: null as number | null,
  ident: null as string | null,
  lineId: null as number | null,
});
const editFormState = ref({
  cueId: null as number | null,
  cueType: null as number | null,
  ident: null as string | null,
  lineId: null as number | null,
});
const activeTab = ref(0);
const groupFormValid = ref(false);
const submittingNewCue = ref(false);
const submittingGroup = ref(false);
const submittingEditCue = ref(false);
const deletingCue = ref(false);

const newRules = {
  newFormState: {
    cueType: { required },
    ident: { required },
    lineId: { required },
  },
};
const editRules = {
  editFormState: {
    cueId: { required },
    cueType: { required },
    ident: { required },
    lineId: { required },
  },
};
const v$ = useVuelidate({ ...newRules, ...editRules }, { newFormState, editFormState });

// Computed display values
const sdStyle = computed(() =>
  getStageDirectionStyle(
    props.line,
    scriptStore.stageDirectionStyles,
    userStore.stageDirectionStyleOverrides
  )
);
const sdStylingWithCuts = computed<Record<string, string>>(() => {
  const base = stageDirectionStyling(sdStyle.value);
  const firstPartId = props.line.line_parts[0]?.id;
  if (firstPartId != null && props.cuts.includes(firstPartId)) {
    const existing = base['text-decoration-line'];
    base['text-decoration-line'] =
      existing && existing !== 'none' ? `${existing} line-through` : 'line-through';
  }
  return base;
});
const textAlign = computed(() =>
  scriptTextAlign(userStore.userSettings as Record<string, unknown>)
);

const needsHeadingsValue = computed(() =>
  needsHeadings(props.line, props.previousLine, props.cuts, scriptStore.getScriptPage)
);
const needsHeadingsAnyValue = computed(() => needsHeadingsValue.value.some(Boolean));

const needsActSceneLabelValue = computed(() =>
  needsActSceneLabel(props.line, props.previousLine, props.cuts, scriptStore.getScriptPage)
);

const actLabel = computed(() => props.acts.find((a) => a.id === props.line.act_id)?.name ?? null);
const sceneLabel = computed(
  () => props.scenes.find((s) => s.id === props.line.scene_id)?.name ?? null
);

const isLineCut = computed(() => isWholeLineCut(props.line, props.cuts));

const individualCues = computed(() => props.cues.filter((c) => c.group_id == null));
const lineGroups = computed(() => scriptStore.groupedCuesForLine(props.line.id).groups);

// RBAC-filtered cue type options: admins see all, others only see types they can write
const cueTypeOptions = computed(() => {
  const base = [{ value: null, text: 'N/A' }];
  if (systemStore.isAdminUser) {
    return [
      ...base,
      ...props.cueTypes.map((t) => ({
        value: t.id,
        text: `${t.prefix}: ${t.description ?? ''}`,
      })),
    ];
  }
  const writeMask = systemStore.rbacRoles.find((r) => r.key === 'WRITE')?.value ?? 0;
  const writableIds = new Set(
    (userStore.currentRbac?.cuetypes ?? []).filter((x) => (x[1] & writeMask) !== 0).map((x) => x[0])
  );
  return [
    ...base,
    ...props.cueTypes
      .filter((t) => writableIds.has(t.id))
      .map((t) => ({ value: t.id, text: `${t.prefix}: ${t.description ?? ''}` })),
  ];
});

// Duplicate detection across all cues
const flatCues = computed(() => Object.values(scriptStore.cues).flat());

const isDuplicateNewCue = computed(
  () =>
    newFormState.value.cueType != null &&
    newFormState.value.ident != null &&
    flatCues.value.some(
      (c) => c.cue_type_id === newFormState.value.cueType && c.ident === newFormState.value.ident
    )
);

const isDuplicateEditCue = computed(
  () =>
    editFormState.value.cueType != null &&
    editFormState.value.ident != null &&
    flatCues.value.some(
      (c) =>
        c.cue_type_id === editFormState.value.cueType &&
        c.ident === editFormState.value.ident &&
        c.id !== editFormState.value.cueId
    )
);

function newFieldState(field: 'cueType' | 'ident'): boolean | null {
  const f = v$.value.newFormState[field];
  return f.$dirty ? !f.$error : null;
}

function editFieldState(field: 'cueType' | 'ident'): boolean | null {
  const f = v$.value.editFormState[field];
  return f.$dirty ? !f.$error : null;
}

function openEditGroup(group: CueGroup, cues: Cue[]): void {
  groupModal.value?.openEdit(group, cues, props.line.id!);
}

// Add cue modal (tabs)
function openNewForm(): void {
  activeTab.value = 0;
  newFormState.value = { cueType: null, ident: null, lineId: props.line.id ?? null };
  v$.value.newFormState.$reset();
  newGroupForm.value?.reset();
  newCueModal.value?.show();
}

function resetNewForm(): void {
  newFormState.value = { cueType: null, ident: null, lineId: null };
  activeTab.value = 0;
  groupFormValid.value = false;
  submittingNewCue.value = false;
  submittingGroup.value = false;
  v$.value.newFormState.$reset();
  newGroupForm.value?.reset();
}

async function onSubmitGroup(): Promise<void> {
  if (!groupFormValid.value || submittingGroup.value || !newGroupForm.value) return;
  submittingGroup.value = true;
  try {
    const data = newGroupForm.value.getFormData();
    await scriptStore.addCueGroup({
      cueTypeId: data.cueTypeId!,
      labelOverride: data.labelOverride || undefined,
      lineId: props.line.id!,
      cues: data.cues.map((c, i) => ({ ident: c.ident, sortOrder: i })),
    });
    newCueModal.value?.hide();
  } finally {
    submittingGroup.value = false;
  }
}

async function onSubmitNew(event: Event): Promise<void> {
  v$.value.newFormState.$touch();
  if (v$.value.newFormState.$invalid || submittingNewCue.value) {
    (event as SubmitEvent).preventDefault?.();
    return;
  }
  submittingNewCue.value = true;
  newCueModal.value?.hide();
  await scriptStore.addNewCue({
    cueType: newFormState.value.cueType!,
    ident: newFormState.value.ident!,
    lineId: newFormState.value.lineId!,
  });
}

// Edit cue modal
function openEditForm(cue: Cue): void {
  editFormState.value = {
    cueId: cue.id ?? null,
    cueType: cue.cue_type_id ?? null,
    ident: cue.ident ?? null,
    lineId: props.line.id ?? null,
  };
  v$.value.editFormState.$reset();
  editCueModal.value?.show();
}

function resetEditForm(): void {
  editFormState.value = { cueId: null, cueType: null, ident: null, lineId: null };
  submittingEditCue.value = false;
  deletingCue.value = false;
  v$.value.editFormState.$reset();
}

async function onSubmitEdit(event?: Event): Promise<void> {
  v$.value.editFormState.$touch();
  if (v$.value.editFormState.$invalid || submittingEditCue.value) {
    (event as SubmitEvent | undefined)?.preventDefault?.();
    return;
  }
  submittingEditCue.value = true;
  await scriptStore.editCue({
    cueId: editFormState.value.cueId!,
    cueType: editFormState.value.cueType!,
    ident: editFormState.value.ident!,
    lineId: editFormState.value.lineId!,
  });
  editCueModal.value?.hide();
  resetEditForm();
}

async function deleteCue(): Promise<void> {
  const confirmed = await confirm('Are you sure you want to delete this cue?', {
    title: 'Delete Cue',
    okVariant: 'danger',
    okTitle: 'Delete',
  });
  if (!confirmed) return;
  deletingCue.value = true;
  await scriptStore.deleteCue({
    cueId: editFormState.value.cueId!,
    lineId: editFormState.value.lineId!,
  });
  editCueModal.value?.hide();
  resetEditForm();
}
</script>

<style scoped>
.viewable-line {
  margin: 0;
}

.cue-column {
  text-align: right;
}

.cue-button {
  padding: 0.2rem;
}

.cue-group-btn {
  border-style: dashed !important;
}

.stage-direction {
  margin-top: 1rem;
  margin-bottom: 1rem;
}

.cut-line-part {
  text-decoration: line-through;
}

.line-row:has(.add-cue-btn:hover) {
  background-color: rgba(255, 255, 255, 0.06);
  border-radius: 4px;
  transition: background-color 0.15s ease;
}
</style>
