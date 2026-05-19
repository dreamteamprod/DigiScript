<template>
  <div
    ref="lineContainer"
    style="margin: 0; padding: 0"
    :style="{ paddingTop: spacingBefore + 'rem', '--spacing-before': spacingBefore + 'rem' }"
  >
    <BContainer v-once fluid class="mx-0" style="margin: 0; padding: 0">
      <BRow v-if="needsIntervalBanner" class="interval-header">
        <template v-if="cuePositionRight">
          <BCol cols="9" class="interval-banner">
            <BAlert variant="warning" style="margin: 0">
              <h3>{{ previousActLabel }} - Interval</h3>
            </BAlert>
          </BCol>
          <BCol
            cols="3"
            :class="[
              'cue-column-right',
              'd-flex',
              'align-items-center',
              'justify-content-center',
              { 'first-row': isFirstRowIntervalBanner },
            ]"
          >
            <BButton v-if="isScriptLeader" variant="primary" @click.stop="startInterval">
              Start Interval
            </BButton>
          </BCol>
        </template>
        <template v-else>
          <BCol
            cols="3"
            :class="[
              'cue-column',
              'd-flex',
              'align-items-center',
              'justify-content-center',
              { 'first-row': isFirstRowIntervalBanner },
            ]"
          >
            <BButton v-if="isScriptLeader" variant="primary" @click.stop="startInterval">
              Start Interval
            </BButton>
          </BCol>
          <BCol cols="9" class="interval-banner">
            <BAlert variant="warning" style="margin: 0">
              <h3>{{ previousActLabel }} - Interval</h3>
            </BAlert>
          </BCol>
        </template>
      </BRow>
      <BRow v-if="needsActSceneLabel" class="act-scene-header">
        <template v-if="cuePositionRight">
          <BCol cols="9">
            <h4>{{ actLabel }} - {{ sceneLabel }}</h4>
          </BCol>
          <BCol cols="3" :class="['cue-column-right', { 'first-row': isFirstRowActScene }]" />
        </template>
        <template v-else>
          <BCol cols="3" :class="['cue-column', { 'first-row': isFirstRowActScene }]" />
          <BCol cols="9">
            <h4>{{ actLabel }} - {{ sceneLabel }}</h4>
          </BCol>
        </template>
      </BRow>
      <BRow
        :class="{
          'stage-direction': line.line_type === LINE_TYPES.STAGE_DIRECTION,
          'heading-padding': line.line_type === LINE_TYPES.DIALOGUE && needsHeadingsAll,
        }"
      >
        <template v-if="cuePositionRight">
          <template v-if="line.line_type === LINE_TYPES.DIALOGUE">
            <BCol>
              <BRow v-if="needsHeadingsAny">
                <BCol
                  v-for="(part, index) in line.line_parts"
                  :key="`heading_${lineIndex}_part_${index}`"
                  :style="headingStyle"
                >
                  <template v-if="needsHeadings[index]">
                    <b>
                      <template v-if="part.character_id != null">
                        {{ characters.find((c) => c.id === part.character_id)?.name }}
                      </template>
                      <template v-else>
                        {{ characterGroups.find((g) => g.id === part.character_group_id)?.name }}
                      </template>
                    </b>
                  </template>
                  <b v-else>&nbsp;</b>
                </BCol>
              </BRow>
              <BRow>
                <BCol
                  v-for="(part, index) in line.line_parts"
                  :key="`line_${lineIndex}_part_${index}`"
                  :style="dialogueStyle"
                >
                  <p class="viewable-line" :class="{ 'cut-line-part': cuts.includes(part.id) }">
                    {{ part.line_text }}
                  </p>
                </BCol>
              </BRow>
            </BCol>
          </template>
          <template v-else-if="line.line_type === LINE_TYPES.STAGE_DIRECTION">
            <BCol :style="{ textAlign: scriptTextAlign }">
              <BRow v-if="isTaggedStageDirection && needsHeadingsAny" style="margin-bottom: 1rem">
                <BCol :style="headingStyle">
                  <b>{{ taggedStageDirectionHeadingName }}</b>
                </BCol>
              </BRow>
              <i class="viewable-line" :style="stageDirectionStylingObj">
                <template v-if="stageDirectionStyle?.text_format === 'upper'">
                  {{ line.line_parts[0]?.line_text?.toUpperCase() }}
                </template>
                <template v-else-if="stageDirectionStyle?.text_format === 'lower'">
                  {{ line.line_parts[0]?.line_text?.toLowerCase() }}
                </template>
                <template v-else>
                  {{ line.line_parts[0]?.line_text }}
                </template>
              </i>
            </BCol>
          </template>
          <template v-else-if="line.line_type === LINE_TYPES.CUE_LINE">
            <BCol :style="dialogueStyle" />
          </template>
          <BCol cols="3" :class="['cue-column-right', { 'first-row': isFirstRowContent }]">
            <BButtonGroup>
              <BButton
                v-for="cue in cues"
                :key="cue.id"
                class="cue-button"
                :style="{
                  backgroundColor: cueBackgroundColour(cue),
                  color: contrastColor(cueBackgroundColour(cue)),
                }"
              >
                {{ cueLabel(cue) }}
              </BButton>
              <BButton
                v-if="cueAddMode"
                variant="success"
                class="cue-button"
                :disabled="isLineCut"
                @click.stop="addNewCue"
              >
                +
              </BButton>
            </BButtonGroup>
          </BCol>
        </template>
        <template v-else>
          <BCol cols="3" :class="['cue-column', { 'first-row': isFirstRowContent }]">
            <BButtonGroup>
              <BButton
                v-for="cue in cues"
                :key="cue.id"
                class="cue-button"
                :style="{
                  backgroundColor: cueBackgroundColour(cue),
                  color: contrastColor(cueBackgroundColour(cue)),
                }"
              >
                {{ cueLabel(cue) }}
              </BButton>
              <BButton
                v-if="cueAddMode"
                variant="success"
                class="cue-button"
                :disabled="isLineCut"
                @click.stop="addNewCue"
              >
                +
              </BButton>
            </BButtonGroup>
          </BCol>
          <template v-if="line.line_type === LINE_TYPES.DIALOGUE">
            <BCol>
              <BRow v-if="needsHeadingsAny">
                <BCol
                  v-for="(part, index) in line.line_parts"
                  :key="`heading_${lineIndex}_part_${index}`"
                  :style="headingStyle"
                >
                  <template v-if="needsHeadings[index]">
                    <b>
                      <template v-if="part.character_id != null">
                        {{ characters.find((c) => c.id === part.character_id)?.name }}
                      </template>
                      <template v-else>
                        {{ characterGroups.find((g) => g.id === part.character_group_id)?.name }}
                      </template>
                    </b>
                  </template>
                  <b v-else>&nbsp;</b>
                </BCol>
              </BRow>
              <BRow>
                <BCol
                  v-for="(part, index) in line.line_parts"
                  :key="`line_${lineIndex}_part_${index}`"
                  :style="dialogueStyle"
                >
                  <p class="viewable-line" :class="{ 'cut-line-part': cuts.includes(part.id) }">
                    {{ part.line_text }}
                  </p>
                </BCol>
              </BRow>
            </BCol>
          </template>
          <template v-else-if="line.line_type === LINE_TYPES.STAGE_DIRECTION">
            <BCol :style="{ textAlign: scriptTextAlign }">
              <BRow v-if="isTaggedStageDirection && needsHeadingsAny" style="margin-bottom: 1rem">
                <BCol :style="headingStyle">
                  <b>{{ taggedStageDirectionHeadingName }}</b>
                </BCol>
              </BRow>
              <i class="viewable-line" :style="stageDirectionStylingObj">
                <template v-if="stageDirectionStyle?.text_format === 'upper'">
                  {{ line.line_parts[0]?.line_text?.toUpperCase() }}
                </template>
                <template v-else-if="stageDirectionStyle?.text_format === 'lower'">
                  {{ line.line_parts[0]?.line_text?.toLowerCase() }}
                </template>
                <template v-else>
                  {{ line.line_parts[0]?.line_text }}
                </template>
              </i>
            </BCol>
          </template>
          <template v-else-if="line.line_type === LINE_TYPES.CUE_LINE">
            <BCol :style="dialogueStyle" />
          </template>
        </template>
      </BRow>
    </BContainer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useScriptNavigation } from '@/composables/useScriptNavigation';
import { useScriptDisplay } from '@/composables/useScriptDisplay';
import { useCueDisplay } from '@/composables/useCueDisplay';
import { useUserStore } from '@/stores/user';
import { useScriptStore } from '@/stores/script';
import { isWholeLineCut } from '@/js/scriptUtils';
import { LINE_TYPES } from '@/constants/lineTypes';
import type { ScriptLine, ScriptCut, StageDirectionStyle } from '@/types/api/script';
import type { Act, Scene, Character, CharacterGroup } from '@/types/api/show';
import type { Cue, CueType } from '@/types/api/cues';

const props = defineProps<{
  line: ScriptLine;
  lineIndex: number;
  previousLine: ScriptLine | null;
  previousLineIndex: number | null;
  acts: Act[];
  scenes: Scene[];
  characters: Character[];
  characterGroups: CharacterGroup[];
  cueTypes: CueType[];
  cues: Cue[];
  cuts: ScriptCut[];
  stageDirectionStyles: StageDirectionStyle[];
  stageDirectionStyleOverrides: StageDirectionStyle[];
  isScriptLeader: boolean;
  cueAddMode: boolean;
  spacingBefore?: number;
}>();

const emit = defineEmits<{
  'last-line-change': [page: number, lineIndex: number];
  'first-line-change': [page: number, lineIndex: number, previousLineRef: string | null];
  'start-interval': [actId: number];
  'add-cue': [lineId: number];
}>();

const userStore = useUserStore();
const scriptStore = useScriptStore();
const { needsHeadings: computeNeedsHeadings, needsActSceneLabel: computeNeedsActSceneLabel } =
  useScriptNavigation();
const {
  getStageDirectionStyle,
  stageDirectionStyling: computeStyling,
  scriptTextAlign: computeTextAlign,
} = useScriptDisplay();
const { cueLabel, cueBackgroundColour, contrastColor } = useCueDisplay();

const lineContainer = ref<HTMLElement | null>(null);
let observer: MutationObserver | null = null;

const cuePositionRight = computed(() => userStore.userSettings?.cue_position_right ?? true);

const needsHeadings = computed(() =>
  computeNeedsHeadings(props.line, props.previousLine, props.cuts, scriptStore.getScriptPage)
);
const needsHeadingsAny = computed(() => needsHeadings.value.some(Boolean));
const needsHeadingsAll = computed(() => needsHeadings.value.every(Boolean));

const needsActSceneLabel = computed(() =>
  computeNeedsActSceneLabel(props.line, props.previousLine, props.cuts, scriptStore.getScriptPage)
);

const needsIntervalBanner = computed(() => {
  let prev: ScriptLine | null = props.previousLine;
  while (prev != null && isWholeLineCut(prev, props.cuts)) {
    const prevPage = scriptStore.getScriptPage(prev.page ?? 0);
    const idx = prevPage.indexOf(prev);
    prev = idx > 0 ? prevPage[idx - 1] : null;
  }
  if (prev == null || prev.act_id === props.line.act_id) return false;
  const prevAct = props.acts.find((a) => a.id === prev!.act_id);
  return prevAct?.interval_after === true;
});

const previousActLabel = computed(
  () => props.acts.find((a) => a.id === props.previousLine?.act_id)?.name ?? null
);
const actLabel = computed(() => props.acts.find((a) => a.id === props.line.act_id)?.name ?? null);
const sceneLabel = computed(
  () => props.scenes.find((s) => s.id === props.line.scene_id)?.name ?? null
);

const stageDirectionStyle = computed(() =>
  getStageDirectionStyle(props.line, props.stageDirectionStyles, props.stageDirectionStyleOverrides)
);
const stageDirectionStylingObj = computed(() => computeStyling(stageDirectionStyle.value));

const scriptTextAlign = computed(() => computeTextAlign(userStore.userSettings));
const headingStyle = computed(() => ({ textAlign: scriptTextAlign.value }));
const dialogueStyle = computed(() => ({ textAlign: scriptTextAlign.value }));

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
  if (part.character_id != null) {
    return props.characters.find((c) => c.id === part.character_id)?.name ?? '';
  }
  return props.characterGroups.find((g) => g.id === part.character_group_id)?.name ?? '';
});

const isLineCut = computed(() => isWholeLineCut(props.line, props.cuts));
const isFirstRowIntervalBanner = computed(() => needsIntervalBanner.value);
const isFirstRowActScene = computed(() => !needsIntervalBanner.value && needsActSceneLabel.value);
const isFirstRowContent = computed(() => !needsIntervalBanner.value && !needsActSceneLabel.value);

function addNewCue(): void {
  emit('add-cue', props.line.id);
}

function startInterval(): void {
  if (!props.previousLine) return;
  const actId = props.acts.find((a) => a.id === props.previousLine!.act_id)?.id;
  if (actId != null) emit('start-interval', actId);
}

function onClassChange(classAttrValue: string | null, oldClassAttrValue: string | null): void {
  const classList = classAttrValue?.split(' ') ?? [];
  const oldClassList = oldClassAttrValue?.split(' ') ?? [];
  if (classList.includes('last-script-element') && !oldClassList.includes('last-script-element')) {
    emit('last-line-change', props.line.page ?? 0, props.lineIndex);
  }
  if (
    classList.includes('first-script-element') &&
    !oldClassList.includes('first-script-element')
  ) {
    const prev = props.previousLine;
    const prevRef = prev != null ? `page_${prev.page}_line_${props.previousLineIndex}` : null;
    emit('first-line-change', props.line.page ?? 0, props.lineIndex, prevRef);
  }
}

onMounted(() => {
  if (lineContainer.value) {
    observer = new MutationObserver((mutations) => {
      for (const m of mutations) {
        const newValue = (m.target as Element).getAttribute(m.attributeName!);
        onClassChange(newValue, m.oldValue);
      }
    });
    observer.observe(lineContainer.value, {
      attributes: true,
      attributeOldValue: true,
      attributeFilter: ['class'],
    });
  }
});

onUnmounted(() => {
  observer?.disconnect();
});
</script>

<style scoped>
.cue-column {
  border-right: 0.1rem solid #3498db;
  margin-top: -1rem;
  margin-bottom: -1rem;
  padding-top: 1rem;
  padding-bottom: 1rem;
}

.cue-column.first-row {
  margin-top: calc(-1rem - var(--spacing-before, 0rem));
  padding-top: calc(1rem + var(--spacing-before, 0rem));
}

.cue-column-right {
  border-left: 0.1rem solid #3498db;
  margin-top: -1rem;
  margin-bottom: -1rem;
  padding-top: 1rem;
  padding-bottom: 1rem;
}

.cue-column-right.first-row {
  margin-top: calc(-1rem - var(--spacing-before, 0rem));
  padding-top: calc(1rem + var(--spacing-before, 0rem));
}

.interval-banner {
  margin-top: -1rem;
  margin-bottom: -1rem;
  padding-top: 1rem;
  padding-bottom: 1rem;
}

.cue-button {
  padding: 0.2rem;
}

.stage-direction {
  margin-top: 1rem;
  margin-bottom: 1rem;
}

.heading-padding {
  margin-top: 0.5rem;
}

.cut-line-part {
  text-decoration: line-through;
}

.current-line {
  background: #3498db54;
}

.interval-header,
.act-scene-header {
  background: var(--bs-body-bg);
}

.interval-header {
  margin-top: 1rem;
  padding-bottom: 1rem;
}
</style>
