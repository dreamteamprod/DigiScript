import { computed } from 'vue';
import type { Ref } from 'vue';
import type { Scene } from '@/types/api/show';
import { useShowStore } from '@/stores/show';

export interface TimelineRow {
  id: number;
  name: string;
  type: string;
}

export interface ActGroup {
  actId: number;
  actName: string;
  startX: number;
  width: number;
}

export interface TimelineSegment {
  startIndex: number;
  endIndex: number;
  startScene: string;
  endScene: string;
}

type EntityType = 'mic' | 'character' | 'cast' | 'prop' | 'scenery';

const EXPORT_STYLES: Record<string, Record<string, string>> = {
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

function getColorForEntity(entityId: number, entityType: string): string {
  const typeOffsets: Record<string, number> = {
    mic: 0,
    character: 120,
    cast: 240,
    prop: 60,
    scenery: 180,
  };
  const hue = (entityId * 137.508 + (typeOffsets[entityType] ?? 0)) % 360;
  return `hsl(${hue}, 70%, 50%)`;
}

function applyExportStyles(svgClone: SVGSVGElement): void {
  Object.entries(EXPORT_STYLES).forEach(([selector, attrs]) => {
    svgClone.querySelectorAll(selector).forEach((el) => {
      Object.entries(attrs).forEach(([attr, value]) => {
        el.setAttribute(attr, value);
      });
    });
  });
}

export function useTimeline(scenes: Ref<Scene[]>, rows: Ref<TimelineRow[]>) {
  const showStore = useShowStore();

  const margin = { top: 75, right: 20, bottom: 20, left: 150 };
  const sceneWidth = 100;
  const rowHeight = 50;
  const barPadding = 6;

  const contentWidth = computed(() => scenes.value.length * sceneWidth);
  const contentHeight = computed(() => rows.value.length * rowHeight);
  const totalWidth = computed(() => margin.left + contentWidth.value + margin.right);
  const totalHeight = computed(() => margin.top + contentHeight.value + margin.bottom);

  const actGroups = computed((): ActGroup[] => {
    const groups: ActGroup[] = [];
    let currentActId: number | null = null;
    let startIndex = 0;

    scenes.value.forEach((scene, index) => {
      const act = showStore.actById(scene.act);
      if (!act) return;
      if (currentActId !== act.id) {
        if (currentActId !== null) {
          groups.push({
            actId: currentActId,
            actName: showStore.actById(currentActId)?.name ?? 'Unknown',
            startX: getSceneX(startIndex),
            width: getSceneX(index) - getSceneX(startIndex),
          });
        }
        currentActId = act.id;
        startIndex = index;
      }
    });

    if (currentActId !== null) {
      groups.push({
        actId: currentActId,
        actName: showStore.actById(currentActId)?.name ?? 'Unknown',
        startX: getSceneX(startIndex),
        width: getSceneX(scenes.value.length) - getSceneX(startIndex),
      });
    }

    return groups;
  });

  function getSceneX(sceneIndex: number): number {
    return sceneIndex * sceneWidth;
  }

  function getRowY(rowIndex: number): number {
    return rowIndex * rowHeight;
  }

  function processAllocationEntry(
    hasAllocation: boolean,
    scene: Scene,
    sceneIndex: number,
    segments: TimelineSegment[],
    currentSegment: TimelineSegment | null
  ): TimelineSegment | null {
    if (!hasAllocation) {
      if (currentSegment) segments.push(currentSegment);
      return null;
    }
    const sameAct = currentSegment
      ? scene.act === scenes.value[currentSegment.startIndex].act
      : true;
    if (currentSegment && sameAct) {
      return { ...currentSegment, endIndex: sceneIndex, endScene: scene.name ?? '' };
    }
    if (currentSegment) segments.push(currentSegment);
    return {
      startIndex: sceneIndex,
      endIndex: sceneIndex,
      startScene: scene.name ?? '',
      endScene: scene.name ?? '',
    };
  }

  function groupConsecutiveScenes(
    allocations: Array<Record<string, unknown>>,
    sceneIdField = 'scene_id'
  ): TimelineSegment[] {
    if (!allocations || allocations.length === 0) return [];

    const segments: TimelineSegment[] = [];
    let currentSegment: TimelineSegment | null = null;

    scenes.value.forEach((scene, sceneIndex) => {
      const hasAllocation = allocations.some((a) => a[sceneIdField] === scene.id);
      currentSegment = processAllocationEntry(
        hasAllocation,
        scene,
        sceneIndex,
        segments,
        currentSegment
      );
    });

    if (currentSegment) segments.push(currentSegment);
    return segments;
  }

  function exportTimeline(
    svgRef: Ref<SVGSVGElement | null>,
    filenamePrefix = 'timeline',
    viewModeName = ''
  ): void {
    const svgElement = svgRef.value;
    if (!svgElement) return;

    const svgClone = svgElement.cloneNode(true) as SVGSVGElement;
    applyExportStyles(svgClone);

    const serializer = new XMLSerializer();
    const svgString = serializer.serializeToString(svgClone);

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d')!;
    const img = new Image();

    canvas.width = totalWidth.value;
    canvas.height = totalHeight.value;

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
  }

  return {
    margin,
    sceneWidth,
    rowHeight,
    barPadding,
    contentWidth,
    contentHeight,
    totalWidth,
    totalHeight,
    actGroups,
    getSceneX,
    getRowY,
    getColorForEntity,
    groupConsecutiveScenes,
    exportTimeline,
  };
}
