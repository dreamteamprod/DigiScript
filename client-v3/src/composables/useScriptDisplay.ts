import { LINE_TYPES } from '@/constants/lineTypes';
import { TEXT_ALIGNMENT_CSS } from '@/constants/textAlignment';
import type { TextAlignment } from '@/constants/textAlignment';
import type { ScriptLine, StageDirectionStyle } from '@/types/api/script';

function getStageDirectionStyle(
  line: ScriptLine,
  styles: StageDirectionStyle[],
  overrides: StageDirectionStyle[]
): StageDirectionStyle | null {
  if (line.line_type !== LINE_TYPES.STAGE_DIRECTION) return null;
  const style = styles.find((s) => s.id === line.stage_direction_style_id) ?? null;
  if (!style) return null;
  const override = (overrides as any[]).find((o) => o.settings?.id === style.id);
  return override ? override.settings : style;
}

function stageDirectionStyling(style: StageDirectionStyle | null): Record<string, string> {
  if (!style) return { 'background-color': 'darkslateblue', 'font-style': 'italic' };
  const result: Record<string, string> = {
    'font-weight': style.bold ? 'bold' : 'normal',
    'font-style': style.italic ? 'italic' : 'normal',
    'text-decoration-line': style.underline ? 'underline' : 'none',
    color: style.text_colour ?? '',
  };
  if (style.enable_background_colour) result['background-color'] = style.background_colour ?? '';
  return result;
}

function scriptTextAlign(userSettings: Record<string, unknown>): string {
  const alignment = (userSettings?.script_text_alignment as TextAlignment) ?? 2;
  return TEXT_ALIGNMENT_CSS[alignment] || 'center';
}

export function useScriptDisplay() {
  return { getStageDirectionStyle, stageDirectionStyling, scriptTextAlign };
}
