<template>
  <div
    ref="lineContainer"
    :data-line-id="line.id"
    :class="{ 'jump-highlight': highlightLineId != null && highlightLineId === line.id }"
    style="margin: 0; padding: 0 0 0.2rem"
  >
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
          'line-row-open': cardHere,
        }"
      >
        <!-- Cue column -->
        <BCol cols="3" class="cue-column">
          <template v-if="line.line_type !== LINE_TYPES.SPACING">
            <div class="cue-buttons">
              <template
                v-for="slot in visibleCueSlots"
                :key="slot.type === 'individual' ? slot.cue.id : `group_${slot.group.id}`"
              >
                <button
                  v-if="slot.type === 'individual'"
                  type="button"
                  class="btn cue-button"
                  :class="{ 'cue-selected': isOpenCue(slot.cue.id) }"
                  :data-cue-id="slot.cue.id"
                  :style="{
                    backgroundColor: cueBackgroundColour(slot.cue),
                    color: contrastColor(cueBackgroundColour(slot.cue)),
                  }"
                  @click.stop="openCue(slot.cue, $event)"
                >
                  {{ cueLabel(slot.cue) }}
                </button>
                <button
                  v-else
                  type="button"
                  class="btn cue-button cue-group-btn"
                  :class="{ 'cue-selected': isOpenGroup(slot.group.id) }"
                  :data-group-id="slot.group.id"
                  :style="{
                    backgroundColor: cueGroupBackgroundColour(slot.group),
                    color: contrastColor(cueGroupBackgroundColour(slot.group)),
                  }"
                  @click.stop="openGroup(slot.group, $event)"
                >
                  {{ cueGroupLabel(slot.group, slot.cues) }}
                </button>
              </template>
              <span v-if="canAdd && isLineCut" class="line-cut-note">Line cut</span>
              <button
                v-if="canAdd"
                type="button"
                class="btn cue-button add-cue-btn"
                :disabled="isLineCut || addOpen"
                :aria-label="addLabel"
                @click.stop="openAdd($event)"
              >
                {{ addOpen ? 'Adding…' : '+ Cue' }}
              </button>
            </div>
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
            <BRow
              v-if="isTaggedStageDirection && needsHeadingsAnyValue"
              class="tagged-sd-heading"
              style="margin-bottom: 1rem"
            >
              <BCol>
                <b>{{ taggedStageDirectionHeadingName }}</b>
              </BCol>
            </BRow>
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

      <!-- Card for this line, under it in the script column -->
      <BRow v-if="cardHere && cardKind">
        <BCol cols="3" />
        <BCol>
          <CueCard
            v-if="cardKind === 'add' && addMode === 'single'"
            v-model:type-id="addTypeId"
            mode="add"
            :line="line"
            :line-label="lineLabel"
            @cancel="emit('close-card')"
            @done="emit('close-card')"
            @added="(typeId, stay) => emit('added', typeId, stay)"
            @switch-group="addMode = 'group'"
          />
          <CueGroupCard
            v-else-if="cardKind === 'add'"
            v-model:type-id="addTypeId"
            mode="add"
            :line="line"
            :line-label="lineLabel"
            @cancel="emit('cancel-card')"
            @done="emit('close-card')"
            @added="(typeId) => emit('added', typeId, false)"
            @switch-single="switchToSingle"
            @dirty="(value) => emit('dirty', value)"
          />
          <CueCard
            v-else-if="cardKind === 'edit-cue' && targetCue"
            :key="`edit_${targetCue.id}`"
            mode="edit"
            :line="line"
            :line-label="lineLabel"
            :cue="targetCue"
            :type-id="null"
            @cancel="emit('close-card')"
            @done="emit('close-card')"
          />
          <CueCard
            v-else-if="cardKind === 'view' && targetCue"
            mode="view"
            :line="line"
            :line-label="lineLabel"
            :cue="targetCue"
            :type-id="null"
          />
          <CueGroupCard
            v-else-if="cardKind === 'edit-group' && targetGroup"
            :key="`group_${targetGroup.group.id}`"
            mode="edit"
            :line="line"
            :line-label="lineLabel"
            :group="targetGroup.group"
            :group-cues="targetGroup.cues"
            :type-id="null"
            @cancel="emit('cancel-card')"
            @done="emit('close-card')"
            @dirty="(value) => emit('dirty', value)"
          />
        </BCol>
      </BRow>
    </BContainer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import CueCard from '@/components/show/config/cues/CueCard.vue';
import CueGroupCard from '@/components/show/config/cues/CueGroupCard.vue';
import { useScriptDisplay } from '@/composables/useScriptDisplay';
import { useCueDisplay } from '@/composables/useCueDisplay';
import { useCuePermissions } from '@/composables/useCuePermissions';
import { useScriptNavigation } from '@/composables/useScriptNavigation';
import { useScriptStore } from '@/stores/script';
import { useUserStore } from '@/stores/user';
import { isWholeLineCut } from '@/js/scriptUtils';
import { LINE_TYPES } from '@/constants/lineTypes';
import type { ScriptLine } from '@/types/api/script';
import type { Cue, CueGroup, CueType } from '@/types/api/cues';
import type { Act, Scene, Character, CharacterGroup } from '@/types/api/show';
import type { ActiveCueCard } from '@/types/cueCard';

const props = withDefaults(
  defineProps<{
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
    activeCard?: ActiveCueCard | null;
    /** Show only this cue type's cues and groups; null shows all. */
    filterTypeId?: number | null;
    /** The line a find just jumped to, marked briefly. */
    highlightLineId?: number | null;
  }>(),
  { activeCard: null, filterTypeId: null, highlightLineId: null }
);

const emit = defineEmits<{
  /** Open a card; `opener` is the control to give focus back to afterwards. */
  open: [card: ActiveCueCard, opener: HTMLElement | null];
  /** Close the card (done or cancelled with nothing to lose). */
  'close-card': [];
  /** Cancel asked for; the page decides whether changes need confirming. */
  'cancel-card': [];
  /** A cue was added; `stay` when the card stays open. */
  added: [typeId: number, stay: boolean];
  /** Whether the open group card has unsaved changes. */
  dirty: [value: boolean];
  /** The cue or group being edited no longer exists. */
  'target-gone': [];
}>();

const scriptStore = useScriptStore();
const userStore = useUserStore();

const { getStageDirectionStyle, stageDirectionStyling, scriptTextAlign } = useScriptDisplay();
const { cueLabel, cueBackgroundColour, cueGroupLabel, cueGroupBackgroundColour, contrastColor } =
  useCueDisplay();
const { needsHeadings, needsActSceneLabel } = useScriptNavigation();
const { canWriteType, canAddCues } = useCuePermissions();

const lineContainer = ref<HTMLElement | null>(null);

// ── Display ─────────────────────────────────────────────────────────────────

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

// A stage direction tagged with a character (or group) names them like dialogue does,
// and needsHeadings() counts it as having done so for the next line.
const isTaggedStageDirection = computed(() => {
  const part = props.line.line_parts?.[0];
  return (
    props.line.line_type === LINE_TYPES.STAGE_DIRECTION &&
    (part?.character_id != null || part?.character_group_id != null)
  );
});

const taggedStageDirectionHeadingName = computed(() => {
  const part = props.line.line_parts?.[0];
  if (!part) return '';
  if (part.character_id != null)
    return props.characters.find((c) => c.id === part.character_id)?.name ?? '';
  return props.characterGroups.find((g) => g.id === part.character_group_id)?.name ?? '';
});

const needsActSceneLabelValue = computed(() =>
  needsActSceneLabel(props.line, props.previousLine, props.cuts, scriptStore.getScriptPage)
);

const actLabel = computed(() => props.acts.find((a) => a.id === props.line.act_id)?.name ?? null);
const sceneLabel = computed(
  () => props.scenes.find((s) => s.id === props.line.scene_id)?.name ?? null
);

const isLineCut = computed(() => isWholeLineCut(props.line, props.cuts));

/** The start of the line's text: how the interface says which line it means. */
const lineLabel = computed(() => {
  const text =
    props.line.line_type === LINE_TYPES.CUE_LINE
      ? 'Cue Line'
      : props.line.line_parts
          .map((p) => p.line_text ?? '')
          .join(' ')
          .trim();
  return text.length > 40 ? `${text.slice(0, 40).trimEnd()}…` : text || 'this line';
});
const addLabel = computed(() =>
  isLineCut.value ? 'Add a cue (this line is cut)' : `Add a cue: ${lineLabel.value}`
);

// ── Cues on this line ───────────────────────────────────────────────────────

const mergedCueSlots = computed(() => scriptStore.groupedCuesForLine(props.line.id).merged);

/** The type filter hides other types' cues and groups. */
const visibleCueSlots = computed(() =>
  props.filterTypeId == null
    ? mergedCueSlots.value
    : mergedCueSlots.value.filter((slot) =>
        slot.type === 'individual'
          ? slot.cue.cue_type_id === props.filterTypeId
          : slot.group.cue_type_id === props.filterTypeId
      )
);

const canAdd = computed(() => canAddCues.value);

// ── Cards ───────────────────────────────────────────────────────────────────

const cardHere = computed(() => props.activeCard?.lineId === props.line.id);
const cardKind = computed(() => (cardHere.value ? props.activeCard!.kind : null));
const addOpen = computed(() => cardKind.value === 'add');

const addMode = ref<'single' | 'group'>('single');
const addTypeId = ref<number | null>(null);

function defaultAddType(): number | null {
  const writable = props.cueTypes.filter((t) => canWriteType(t.id));
  if (props.filterTypeId != null && canWriteType(props.filterTypeId)) return props.filterTypeId;
  try {
    const remembered = Number(localStorage.getItem('cueEditType'));
    if (remembered && writable.some((t) => t.id === remembered)) return remembered;
  } catch {
    // Storage can be unavailable; remembering the type is only a convenience.
  }
  return writable.length === 1 ? writable[0].id : null;
}

// Each time an add card opens on this line it starts as a single cue with the default type.
watch(
  addOpen,
  (open) => {
    if (open) {
      addMode.value = 'single';
      addTypeId.value = defaultAddType();
    }
  },
  { immediate: true }
);

const targetCue = computed<Cue | null>(() => {
  if (!cardHere.value || props.activeCard?.cueId == null) return null;
  return (
    scriptStore.cuesForLine(props.line.id).find((c) => c.id === props.activeCard!.cueId) ?? null
  );
});

const targetGroup = computed(() => {
  if (!cardHere.value || props.activeCard?.groupId == null) return null;
  return (
    scriptStore
      .groupedCuesForLine(props.line.id)
      .groups.find((g) => g.group.id === props.activeCard!.groupId) ?? null
  );
});

// If a reload removes the cue or group being edited, the page closes the card and says so.
watch(
  () =>
    cardHere.value &&
    ((props.activeCard?.cueId != null && !targetCue.value) ||
      (props.activeCard?.groupId != null && !targetGroup.value)),
  (gone) => {
    if (gone) emit('target-gone');
  }
);

function switchToSingle(): void {
  // The group card (and anything typed into it) goes away, so nothing is left to lose.
  addMode.value = 'single';
  emit('dirty', false);
}

function isOpenCue(cueId: number): boolean {
  return cardHere.value && props.activeCard?.cueId === cueId;
}
function isOpenGroup(groupId: number): boolean {
  return cardHere.value && props.activeCard?.groupId === groupId;
}

function openAdd(event: Event): void {
  emit(
    'open',
    { lineId: props.line.id as number, kind: 'add' },
    event.currentTarget as HTMLElement
  );
}

function openCue(cue: Cue, event: Event): void {
  // A type this person cannot write opens a read-only note instead of the editor.
  const kind = canWriteType(cue.cue_type_id) ? 'edit-cue' : 'view';
  emit(
    'open',
    { lineId: props.line.id as number, kind, cueId: cue.id },
    event.currentTarget as HTMLElement
  );
}

function openGroup(group: CueGroup, event: Event): void {
  const first = mergedCueSlots.value.find((s) => s.type === 'group' && s.group.id === group.id);
  const sample = first && first.type === 'group' ? first.cues[0] : null;
  const kind = canWriteType(group.cue_type_id) && sample ? 'edit-group' : 'view';
  emit(
    'open',
    {
      lineId: props.line.id as number,
      kind,
      groupId: kind === 'edit-group' ? group.id : undefined,
      cueId: kind === 'view' ? sample?.id : undefined,
    },
    event.currentTarget as HTMLElement
  );
}
</script>

<style scoped>
.viewable-line {
  margin: 0;
}

.cue-column {
  text-align: right;
}

.cue-buttons {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  align-items: center;
  gap: 6px;
}

.cue-button {
  min-height: 32px;
  padding: 0 10px;
  font-weight: 700;
  font-size: 0.875rem;
  white-space: nowrap;
  border: 1px solid transparent;
}

.cue-group-btn {
  border: 2px dashed #fff !important;
}

.cue-selected {
  box-shadow:
    0 0 0 2px var(--bs-body-bg),
    0 0 0 4px #fff;
}

.add-cue-btn {
  background: transparent;
  color: var(--bs-gray-500);
  border: 1px dashed var(--bs-gray-600);
}

.add-cue-btn:disabled {
  opacity: 0.45;
  border-style: dotted;
}

.cue-button:focus-visible {
  outline: 2px solid #fff;
  outline-offset: 2px;
}

.line-cut-note {
  color: var(--bs-gray-500);
  font-size: 0.8125rem;
}

.stage-direction {
  margin-top: 1rem;
  margin-bottom: 1rem;
}

.cut-line-part {
  text-decoration: line-through;
}

/* Briefly flags the line a find jumped to (same look as the script editor's). */
.jump-highlight {
  animation: jump-highlight-flash 2s ease-out;
}
@keyframes jump-highlight-flash {
  0%,
  40% {
    background-color: rgba(var(--bs-success-rgb), 0.25);
    border-radius: 4px;
  }
  100% {
    background-color: transparent;
  }
}

.line-row-open {
  background-color: rgba(255, 255, 255, 0.06);
  border-radius: 4px;
}
</style>
