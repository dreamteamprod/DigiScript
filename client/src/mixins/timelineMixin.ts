import { defineComponent } from 'vue';
import { mapGetters } from 'vuex';
import type { Scene } from '@/types/api/show';

interface ActGroup {
  actId: number;
  actName: string;
  startX: number;
  width: number;
}

interface TimelineSegment {
  startIndex: number;
  endIndex: number;
  startScene: string;
  endScene: string;
}

type EntityType = 'mic' | 'character' | 'cast' | 'prop' | 'scenery';

export default defineComponent({
  data() {
    return {
      margin: { top: 75, right: 20, bottom: 20, left: 150 },
      sceneWidth: 100,
      rowHeight: 50,
      barPadding: 6,
    };
  },

  computed: {
    ...mapGetters(['ACT_BY_ID']),
    contentWidth(): number {
      return (this as any).scenes.length * this.sceneWidth;
    },
    contentHeight(): number {
      return (this as any).rows.length * this.rowHeight;
    },
    totalWidth(): number {
      return this.margin.left + (this as any).contentWidth + this.margin.right;
    },
    totalHeight(): number {
      return this.margin.top + (this as any).contentHeight + this.margin.bottom;
    },
    actGroups(): ActGroup[] {
      const groups: ActGroup[] = [];
      let currentActId: number | null = null;
      let startIndex = 0;

      (this as any).scenes.forEach((scene: Scene, index: number) => {
        const act = (this as any).ACT_BY_ID(scene.act);
        if (!act) return;

        if (currentActId !== act.id) {
          if (currentActId !== null) {
            groups.push({
              actId: currentActId,
              actName: (this as any).ACT_BY_ID(currentActId)?.name || 'Unknown',
              startX: this.getSceneX(startIndex),
              width: this.getSceneX(index) - this.getSceneX(startIndex),
            });
          }
          currentActId = act.id;
          startIndex = index;
        }
      });

      if (currentActId !== null) {
        const scenes: Scene[] = (this as any).scenes;
        groups.push({
          actId: currentActId,
          actName: (this as any).ACT_BY_ID(currentActId)?.name || 'Unknown',
          startX: this.getSceneX(startIndex),
          width: this.getSceneX(scenes.length) - this.getSceneX(startIndex),
        });
      }

      return groups;
    },
  },

  methods: {
    getSceneX(sceneIndex: number): number {
      return sceneIndex * this.sceneWidth;
    },
    getRowY(rowIndex: number): number {
      return rowIndex * this.rowHeight;
    },
    getColorForEntity(entityId: number, entityType: EntityType | string): string {
      const GOLDEN_RATIO_CONJUGATE = 137.508;
      const typeOffsets: Record<string, number> = {
        mic: 0,
        character: 120,
        cast: 240,
        prop: 60,
        scenery: 180,
      };
      const offset = typeOffsets[entityType] ?? 0;
      const hue = (entityId * GOLDEN_RATIO_CONJUGATE + offset) % 360;
      return `hsl(${hue}, 70%, 50%)`;
    },
    groupConsecutiveScenes(
      allocations: Array<Record<string, unknown>>,
      sceneIdField = 'scene_id'
    ): TimelineSegment[] {
      if (!allocations || allocations.length === 0) return [];

      const segments: TimelineSegment[] = [];
      let currentSegment: TimelineSegment | null = null;
      const scenes: Scene[] = (this as any).scenes;

      scenes.forEach((scene, sceneIndex) => {
        const hasAllocation = allocations.some((a) => a[sceneIdField] === scene.id);

        if (hasAllocation) {
          const sameAct = currentSegment
            ? scene.act === scenes[currentSegment.startIndex].act
            : true;

          if (currentSegment && sameAct) {
            currentSegment.endIndex = sceneIndex;
            currentSegment.endScene = scene.name ?? '';
          } else {
            if (currentSegment) segments.push(currentSegment);
            currentSegment = {
              startIndex: sceneIndex,
              endIndex: sceneIndex,
              startScene: scene.name ?? '',
              endScene: scene.name ?? '',
            };
          }
        } else if (currentSegment) {
          segments.push(currentSegment);
          currentSegment = null;
        }
      });

      if (currentSegment) segments.push(currentSegment);
      return segments;
    },
    exportTimeline(filenamePrefix = 'timeline', viewModeName = ''): void {
      const svgElement = this.$refs.svg as SVGSVGElement | undefined;
      if (!svgElement) return;

      const svgClone = svgElement.cloneNode(true) as SVGSVGElement;
      this.applyExportStyles(svgClone);

      const serializer = new XMLSerializer();
      const svgString = serializer.serializeToString(svgClone);

      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d')!;
      const img = new Image();

      canvas.width = (this as any).totalWidth;
      canvas.height = (this as any).totalHeight;

      img.onload = () => {
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0);

        canvas.toBlob((blob) => {
          if (!blob) return;
          const url = URL.createObjectURL(blob);
          const link = document.createElement('a');
          const dateSuffix = new Date().toISOString().slice(0, 10);
          const modeSuffix = viewModeName ? `-${viewModeName}` : '';
          link.download = `${filenamePrefix}${modeSuffix}-${dateSuffix}.png`;
          link.href = url;
          link.click();
          URL.revokeObjectURL(url);
        });
      };

      const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
      img.src = URL.createObjectURL(svgBlob);
    },
    applyExportStyles(svgClone: SVGSVGElement): void {
      const exportStyles: Record<string, Record<string, string>> = {
        '.scene-divider': { stroke: '#495057', 'stroke-width': '1', opacity: '0.4' },
        '.row-separator': { stroke: '#495057', 'stroke-width': '1', opacity: '0.3' },
        '.act-header': { fill: '#e9ecef', stroke: '#495057', 'stroke-width': '1' },
        '.act-label': { fill: '#212529', 'font-size': '14', 'font-weight': '600' },
        '.scene-label': { fill: '#495057', 'font-size': '11' },
        '.row-label': { fill: '#212529', 'font-size': '12', 'font-weight': '500' },
        '.allocation-bar': { stroke: '#212529', 'stroke-width': '1' },
        '.bar-label': {
          fill: '#ffffff',
          'font-weight': '600',
          style: 'text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8)',
        },
      };

      Object.entries(exportStyles).forEach(([selector, attrs]) => {
        svgClone.querySelectorAll(selector).forEach((el) => {
          Object.entries(attrs).forEach(([attr, value]) => {
            el.setAttribute(attr, value);
          });
        });
      });
    },
  },
});
