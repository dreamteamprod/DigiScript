<template>
  <div class="revision-graph-container">
    <div v-if="!hasRevisions" class="text-center py-5 text-muted">No revisions to display</div>
    <div v-else class="graph-wrapper">
      <svg ref="svgRef" :width="width" :height="height" class="revision-graph">
        <defs>
          <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
            <polygon points="0 0, 10 3, 0 6" fill="#6c757d" />
          </marker>
        </defs>
        <g ref="zoomGroupRef" class="zoom-group">
          <g :transform="`translate(${margin.left},${margin.top})`">
            <g class="links">
              <path
                v-for="link in links"
                :key="`link-${link.source.data.id}-${link.target.data.id}`"
                :d="linkPath(link)"
                class="revision-link"
                marker-end="url(#arrowhead)"
              />
            </g>
            <g class="nodes">
              <g
                v-for="node in nodes"
                :key="`node-${node.data.id}`"
                :transform="`translate(${node.y},${node.x})`"
                class="node-group"
                @click="$emit('node-click', node.data)"
              >
                <title>{{ nodeTooltip(node) }}</title>
                <circle
                  v-if="node.data.id === currentRevisionId"
                  :r="nodeRadius + 4"
                  class="current-indicator"
                />
                <circle :r="nodeRadius" :class="nodeClass(node)" />
                <text class="node-label" dy=".35em" :x="nodeRadius + 5">
                  Rev {{ node.data.revision }}
                </text>
              </g>
            </g>
          </g>
        </g>
      </svg>
      <div class="zoom-controls">
        <BButtonGroup vertical>
          <BButton size="sm" variant="outline-secondary" @click="zoomIn"
            ><IMdiMagnifyPlus
          /></BButton>
          <BButton size="sm" variant="outline-secondary" @click="zoomOut"
            ><IMdiMagnifyMinus
          /></BButton>
          <BButton size="sm" variant="outline-secondary" @click="resetZoom"
            ><IMdiRefresh
          /></BButton>
        </BButtonGroup>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { hierarchy, tree } from 'd3-hierarchy';
import { select } from 'd3-selection';
import { zoom as d3zoom, zoomIdentity } from 'd3-zoom';
import type { ScriptRevision } from '@/types/api/script';

const props = defineProps<{
  revisions: ScriptRevision[];
  currentRevisionId: number | null;
  selectedRevisionId?: number | null;
}>();

defineEmits<{ 'node-click': [revision: ScriptRevision] }>();

const svgRef = ref<SVGSVGElement | null>(null);
const zoomGroupRef = ref<SVGGElement | null>(null);
const width = ref(800);
const height = 400;
const margin = { top: 20, right: 120, bottom: 20, left: 40 };
const nodeRadius = 8;

// D3 state — NOT in Vue reactive state (would cause infinite loops)
let zoomBehavior: ReturnType<typeof d3zoom> | null = null;

const hasRevisions = computed(() => props.revisions.length > 0);

const treeData = computed(() => {
  if (!hasRevisions.value) return null;
  const root = props.revisions.find((r) => !r.previous_revision_id || r.revision === 1);
  if (!root) return null;
  const buildTree = (revision: ScriptRevision): any => ({
    ...revision,
    children: props.revisions
      .filter((r) => r.previous_revision_id === revision.id)
      .map(buildTree)
      .filter((c) => c.children !== undefined || props.revisions.some((r) => r.id === c.id)),
  });
  return buildTree(root);
});

const hierarchyData = computed(() => {
  if (!treeData.value) return null;
  const root = hierarchy(treeData.value);
  const treeLayout = tree<ScriptRevision>().size([
    height - margin.top - margin.bottom,
    width.value - margin.left - margin.right,
  ]);
  return treeLayout(root as any);
});

const nodes = computed(() => hierarchyData.value?.descendants() ?? []);
const links = computed(() => hierarchyData.value?.links() ?? []);

function nodeClass(node: any): string {
  const classes = ['revision-node'];
  if (node.data.id === props.currentRevisionId) classes.push('current');
  if (node.data.id === props.selectedRevisionId) classes.push('selected');
  return classes.join(' ');
}

function nodeTooltip(node: any): string {
  const parts = [
    `Revision ${node.data.revision}`,
    `Description: ${node.data.description || 'N/A'}`,
    `Created: ${node.data.created_at || 'N/A'}`,
  ];
  if (node.data.id === props.currentRevisionId) parts.push('(Current)');
  return parts.join('\n');
}

function linkPath(link: any): string {
  const midY = (link.source.y + link.target.y) / 2;
  return `M${link.source.y},${link.source.x} C${midY},${link.source.x} ${midY},${link.target.x} ${link.target.y},${link.target.x}`;
}

function updateWidth(): void {
  const container = svgRef.value?.parentElement as HTMLElement | null;
  if (container) width.value = container.clientWidth || 800;
}

function initZoom(): void {
  if (!svgRef.value || !zoomGroupRef.value) return;
  const svg = select(svgRef.value);
  const g = select(zoomGroupRef.value);
  zoomBehavior = d3zoom()
    .scaleExtent([0.1, 4])
    .on('zoom', (event: any) => {
      g.attr('transform', event.transform);
    });
  svg.call(zoomBehavior as any);
}

function fitToContent(): void {
  if (!nodes.value.length || !svgRef.value || !zoomBehavior) return;
  const padding = 50;
  const minX = Math.min(...nodes.value.map((n: any) => n.x)) - padding;
  const maxX = Math.max(...nodes.value.map((n: any) => n.x)) + padding;
  const minY = Math.min(...nodes.value.map((n: any) => n.y)) - padding;
  const maxY = Math.max(...nodes.value.map((n: any) => n.y)) + padding;
  const cw = maxY - minY;
  const ch = maxX - minX;
  if (cw === 0 || ch === 0) return;
  const scale = Math.min(
    (width.value - margin.left - margin.right) / cw,
    (height - margin.top - margin.bottom) / ch,
    1
  );
  const tx = (width.value - cw * scale) / 2 - minY * scale;
  const ty = (height - ch * scale) / 2 - minX * scale;
  select(svgRef.value as Element)
    .transition()
    .duration(500)
    .call((zoomBehavior as any).transform, zoomIdentity.translate(tx, ty).scale(scale));
}

function zoomIn(): void {
  if (!svgRef.value || !zoomBehavior) return;
  select(svgRef.value as Element)
    .transition()
    .duration(300)
    .call((zoomBehavior as any).scaleBy, 1.3);
}

function zoomOut(): void {
  if (!svgRef.value || !zoomBehavior) return;
  select(svgRef.value as Element)
    .transition()
    .duration(300)
    .call((zoomBehavior as any).scaleBy, 0.7);
}

function resetZoom(): void {
  if (!svgRef.value || !zoomBehavior) return;
  select(svgRef.value as Element)
    .transition()
    .duration(300)
    .call((zoomBehavior as any).transform, zoomIdentity);
}

onMounted(() => {
  updateWidth();
  window.addEventListener('resize', updateWidth);
  nextTick(() => {
    initZoom();
    fitToContent();
  });
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateWidth);
  if (zoomBehavior && svgRef.value) {
    select(svgRef.value as Element).on('.zoom', null);
  }
});

watch(
  () => props.revisions,
  () => {
    nextTick(() => fitToContent());
  },
  { deep: true }
);
</script>

<style scoped>
.revision-graph-container {
  position: relative;
  background-color: var(--body-background);
  border: 1px solid #dee2e6;
  border-radius: 0.25rem;
  overflow: hidden;
}
.graph-wrapper {
  position: relative;
}
.revision-graph {
  display: block;
  cursor: grab;
  background-color: var(--body-background);
}
.revision-graph:active {
  cursor: grabbing;
}
.revision-link {
  fill: none;
  stroke: #6c757d;
  stroke-width: 2px;
  opacity: 0.6;
}
.node-group {
  cursor: pointer;
}
.revision-node {
  fill: #007bff;
  stroke: #0056b3;
  stroke-width: 2px;
  transition: all 0.2s ease;
}
.node-group:hover .revision-node {
  fill: #0056b3;
  stroke: #004085;
  stroke-width: 3px;
  filter: drop-shadow(0 0 4px rgba(0, 123, 255, 0.6));
}
.revision-node.current {
  fill: #28a745;
  stroke: #1e7e34;
}
.node-group:hover .revision-node.current {
  fill: #1e7e34;
  stroke: #155724;
  stroke-width: 3px;
  filter: drop-shadow(0 0 4px rgba(40, 167, 69, 0.6));
}
.revision-node.selected {
  stroke: #ffc107;
  stroke-width: 3px;
}
.current-indicator {
  fill: none;
  stroke: #28a745;
  stroke-width: 2px;
  animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}
.node-label {
  fill: #dee2e6;
  font-size: 12px;
  font-weight: 500;
  pointer-events: none;
  user-select: none;
}
.zoom-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 10;
}
.zoom-controls :deep(.btn) {
  background-color: rgba(52, 58, 64, 0.9);
  border-color: #6c757d;
  color: #dee2e6;
}
.zoom-controls :deep(.btn:hover) {
  background-color: rgba(73, 80, 87, 0.9);
  border-color: #adb5bd;
  color: #fff;
}
</style>
