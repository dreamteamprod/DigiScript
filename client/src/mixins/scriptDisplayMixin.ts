import { defineComponent } from 'vue';
import { mapGetters } from 'vuex';
import { LINE_TYPES } from '@/constants/lineTypes';
import { TEXT_ALIGNMENT_CSS } from '@/constants/textAlignment';
import type { ScriptLine, StageDirectionStyle } from '@/types/api/script';
import type { Act, Scene } from '@/types/api/show';

export default defineComponent({
  data() {
    return {
      observer: null as MutationObserver | null,
    };
  },
  computed: {
    needsActSceneLabel(): boolean {
      let previousLine: ScriptLine | null = (this as any).previousLine;
      let lineIndex: number | null = (this as any).previousLineIndex;
      while (previousLine != null && (this as any).isWholeLineCut(previousLine)) {
        [lineIndex, previousLine] = (this as any).getPreviousLineForIndex(
          previousLine.page,
          lineIndex
        );
      }
      if (previousLine == null) return true;
      const line: ScriptLine = (this as any).line;
      return !(previousLine.act_id === line.act_id && previousLine.scene_id === line.scene_id);
    },
    needsIntervalBanner(): boolean {
      let previousLine: ScriptLine | null = (this as any).previousLine;
      let lineIndex: number | null = (this as any).lineIndex;
      while (previousLine != null && (this as any).isWholeLineCut(previousLine)) {
        [lineIndex, previousLine] = (this as any).getPreviousLineForIndex(
          previousLine.page,
          lineIndex
        );
      }
      if (previousLine == null) return false;
      return previousLine.act_id !== (this as any).line.act_id;
    },
    previousActLabel(): string | null {
      const previousLine: ScriptLine = (this as any).previousLine;
      return (this as any).acts?.find((act: Act) => act.id === previousLine.act_id)?.name ?? null;
    },
    actLabel(): string | null {
      const line: ScriptLine = (this as any).line;
      return (this as any).acts?.find((act: Act) => act.id === line.act_id)?.name ?? null;
    },
    sceneLabel(): string | null {
      const line: ScriptLine = (this as any).line;
      return (this as any).scenes?.find((scene: Scene) => scene.id === line.scene_id)?.name ?? null;
    },
    stageDirectionStyle(): StageDirectionStyle | null {
      const line: ScriptLine = (this as any).line;
      const sdStyle: StageDirectionStyle | undefined = (this as any).stageDirectionStyles?.find(
        (style: StageDirectionStyle) => style.id === line.stage_direction_style_id
      );
      if (!sdStyle) return null;
      const override = (this as any).stageDirectionStyleOverrides?.find(
        (elem: any) => elem.settings?.id === sdStyle.id
      );
      if (line.line_type === LINE_TYPES.STAGE_DIRECTION) {
        return override ? override.settings : sdStyle;
      }
      return null;
    },
    stageDirectionStyling(): Record<string, string> {
      const line: ScriptLine = (this as any).line;
      if (line.stage_direction_style_id == null || (this as any).stageDirectionStyle == null) {
        const userSettings = (this as any).USER_SETTINGS ?? {};
        const result: Record<string, string> = {
          'background-color': userSettings.default_sd_background_colour ?? 'darkslateblue',
          'font-style': 'italic',
        };
        if (userSettings.default_sd_text_colour) {
          result['color'] = userSettings.default_sd_text_colour;
        }
        return result;
      }
      const style: StageDirectionStyle = (this as any).stageDirectionStyle;
      const result: Record<string, string> = {
        'font-weight': style.bold ? 'bold' : 'normal',
        'font-style': style.italic ? 'italic' : 'normal',
        'text-decoration-line': style.underline ? 'underline' : 'none',
        color: style.text_colour ?? '',
      };
      if (style.enable_background_colour) {
        result['background-color'] = style.background_colour ?? '';
      }
      return result;
    },
    scriptTextAlign(): string {
      const alignment = (this as any).USER_SETTINGS?.script_text_alignment ?? 2;
      return TEXT_ALIGNMENT_CSS[alignment] || 'center';
    },
    headingStyle(): Record<string, string> {
      return { textAlign: (this as any).scriptTextAlign };
    },
    dialogueStyle(): Record<string, string> {
      return { textAlign: (this as any).scriptTextAlign };
    },
    needsHeadingsAny(): boolean {
      return (this as any).needsHeadings.some((x: boolean) => x === true);
    },
    needsHeadingsAll(): boolean {
      return (this as any).needsHeadings.every((x: boolean) => x === true);
    },
    isTaggedStageDirection(): boolean {
      const line: ScriptLine = (this as any).line;
      const part = line.line_parts?.[0];
      return (
        line.line_type === LINE_TYPES.STAGE_DIRECTION &&
        (part?.character_id != null || part?.character_group_id != null)
      );
    },
    taggedStageDirectionHeadingName(): string {
      const part = ((this as any).line as ScriptLine).line_parts?.[0];
      return part ? (this as any).characterOrGroupName(part) : '';
    },
    ...mapGetters(['USER_SETTINGS']),
  },
  mounted() {
    if (this.$refs.lineContainer) {
      this.observer = new MutationObserver((mutations) => {
        for (const m of mutations) {
          const newValue = (m.target as Element).getAttribute(m.attributeName!);
          this.$nextTick(() => {
            (this as any).onClassChange(newValue, m.oldValue);
          });
        }
      });

      this.observer.observe(this.$refs.lineContainer as Element, {
        attributes: true,
        attributeOldValue: true,
        attributeFilter: ['class'],
      });
    }
  },
  destroyed() {
    if (this.observer) {
      this.observer.disconnect();
    }
  },
  methods: {
    characterOrGroupName(part: any): string {
      if (part.character_id != null) {
        return (this as any).characters?.find((c: any) => c.id === part.character_id)?.name ?? '';
      }
      return (
        (this as any).characterGroups?.find((c: any) => c.id === part.character_group_id)?.name ??
        ''
      );
    },
    onClassChange(classAttrValue: string | null, oldClassAttrValue: string | null): void {
      const classList = classAttrValue?.split(' ') ?? [];
      const oldClassList = oldClassAttrValue?.split(' ') ?? [];
      const line: ScriptLine = (this as any).line;
      const lineIndex: number = (this as any).lineIndex;
      if (
        classList.includes('last-script-element') &&
        !oldClassList.includes('last-script-element')
      ) {
        this.$emit('last-line-change', line.page, lineIndex);
      }
      if (
        classList.includes('first-script-element') &&
        !oldClassList.includes('first-script-element')
      ) {
        const previousLine: ScriptLine | null = (this as any).previousLine;
        const previousLineIndex: number | null = (this as any).previousLineIndex;
        let previousLineRef: string | null = null;
        if (previousLine != null) {
          previousLineRef = `page_${previousLine.page}_line_${previousLineIndex}`;
        }
        this.$emit('first-line-change', line.page, lineIndex, previousLineRef);
      }
    },
    startInterval(): void {
      const previousLine: ScriptLine = (this as any).previousLine;
      this.$emit(
        'start-interval',
        (this as any).acts?.find((act: Act) => act.id === previousLine.act_id)?.id
      );
    },
  },
});
