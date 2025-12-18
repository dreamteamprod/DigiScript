<template>
  <div class="revision-graph-container">
    <div
      v-if="loading"
      class="text-center py-5"
    >
      <b-spinner label="Loading graph..." />
    </div>
    <div
      v-else-if="!hasRevisions"
      class="text-center py-5 text-muted"
    >
      No revisions to display
    </div>
    <div
      v-else
      class="graph-wrapper"
    >
      <svg
        ref="svg"
        :width="width"
        :height="height"
        class="revision-graph"
      >
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="10"
            refX="9"
            refY="3"
            orient="auto"
          >
            <polygon
              points="0 0, 10 3, 0 6"
              fill="#6c757d"
            />
          </marker>
        </defs>
        <g
          ref="zoomGroup"
          class="zoom-group"
        >
          <g
            ref="contentGroup"
            :transform="`translate(${margin.left},${margin.top})`"
          >
            <!-- Links (edges) -->
            <g class="links">
              <path
                v-for="link in links"
                :key="`link-${link.source.data.id}-${link.target.data.id}`"
                :d="linkPath(link)"
                class="revision-link"
                marker-end="url(#arrowhead)"
              />
            </g>
            <!-- Nodes -->
            <g class="nodes">
              <g
                v-for="node in nodes"
                :key="`node-${node.data.id}`"
                :transform="`translate(${node.y},${node.x})`"
                class="node-group"
                @click="handleNodeClick(node)"
              >
                <title>{{ nodeTooltip(node) }}</title>
                <circle
                  :r="nodeRadius"
                  :class="nodeClass(node)"
                />
                <text
                  class="node-label"
                  dy=".35em"
                  :x="nodeRadius + 5"
                >
                  Rev {{ node.data.revision }}
                </text>
                <!-- Current revision indicator -->
                <circle
                  v-if="isCurrentRevision(node)"
                  :r="nodeRadius + 4"
                  class="current-indicator"
                />
              </g>
            </g>
          </g>
        </g>
      </svg>
      <!-- Zoom controls -->
      <div class="zoom-controls">
        <b-button-group vertical>
          <b-button
            size="sm"
            variant="outline-secondary"
            @click="zoomIn"
          >
            <b-icon-zoom-in />
          </b-button>
          <b-button
            size="sm"
            variant="outline-secondary"
            @click="zoomOut"
          >
            <b-icon-zoom-out />
          </b-button>
          <b-button
            size="sm"
            variant="outline-secondary"
            @click="resetZoom"
          >
            <b-icon-arrow-clockwise />
          </b-button>
        </b-button-group>
      </div>
    </div>
  </div>
</template>

<script>
import { hierarchy, tree } from 'd3-hierarchy';
import { select } from 'd3-selection';
import { zoom, zoomIdentity } from 'd3-zoom';

export default {
  name: 'RevisionGraph',
  props: {
    revisions: {
      type: Array,
      required: true,
    },
    currentRevisionId: {
      type: Number,
      default: null,
    },
    selectedRevisionId: {
      type: Number,
      default: null,
    },
    loading: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      width: 0,
      height: 400,
      margin: {
        top: 20, right: 120, bottom: 20, left: 40,
      },
      nodeRadius: 8,
      zoomBehavior: null,
      currentTransform: null,
    };
  },
  computed: {
    hasRevisions() {
      return this.revisions && this.revisions.length > 0;
    },
    /**
     * Build hierarchical tree structure from flat revision list
     */
    treeData() {
      if (!this.hasRevisions) return null;

      // Find root node (revision with no parent or revision 1)
      const root = this.revisions.find((r) => !r.previous_revision_id || r.revision === 1);
      if (!root) return null;

      // Build tree recursively
      const buildTree = (revision) => {
        const children = this.revisions
          .filter((r) => r.previous_revision_id === revision.id)
          .map((child) => buildTree(child));

        return {
          ...revision,
          children: children.length > 0 ? children : undefined,
        };
      };

      return buildTree(root);
    },
    /**
     * D3 hierarchy with calculated positions
     */
    hierarchyData() {
      if (!this.treeData) return null;

      const root = hierarchy(this.treeData);
      const treeLayout = tree()
        .size([this.height - this.margin.top - this.margin.bottom,
          this.width - this.margin.left - this.margin.right]);

      return treeLayout(root);
    },
    /**
     * Array of nodes with positions
     */
    nodes() {
      if (!this.hierarchyData) return [];
      return this.hierarchyData.descendants();
    },
    /**
     * Array of links between nodes
     */
    links() {
      if (!this.hierarchyData) return [];
      return this.hierarchyData.links();
    },
  },
  watch: {
    revisions: {
      handler() {
        this.$nextTick(() => {
          this.fitToContent();
        });
      },
      deep: true,
    },
  },
  mounted() {
    // Set initial width from container
    this.updateDimensions();

    // Add resize listener
    window.addEventListener('resize', this.updateDimensions);

    // Check if SVG is rendered before initializing zoom
    this.$nextTick(() => {
      if (this.$refs.svg && this.$refs.zoomGroup) {
        this.initZoom();
        this.fitToContent();
      }
    });
  },
  beforeDestroy() {
    // Remove resize listener
    window.removeEventListener('resize', this.updateDimensions);

    // Cleanup zoom behavior
    if (this.zoomBehavior && this.$refs.svg) {
      select(this.$refs.svg).on('.zoom', null);
    }
  },
  methods: {
    /**
     * Update SVG dimensions based on container size
     */
    updateDimensions() {
      const container = this.$el;
      if (container) {
        // Get the container width and update SVG dimensions
        this.width = container.clientWidth || 800;

        // Re-fit content when dimensions change
        this.$nextTick(() => {
          if (this.zoomBehavior) {
            this.fitToContent();
          }
        });
      }
    },
    /**
     * Initialize D3 zoom behavior
     */
    initZoom() {
      const svg = select(this.$refs.svg);
      const g = select(this.$refs.zoomGroup);

      this.zoomBehavior = zoom()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
          g.attr('transform', event.transform);
          this.currentTransform = event.transform;
        });

      svg.call(this.zoomBehavior);
    },
    /**
     * Zoom in
     */
    zoomIn() {
      if (!this.zoomBehavior || !this.$refs.svg) {
        this.initZoom();
      }
      const svg = select(this.$refs.svg);
      svg.transition().duration(300).call(this.zoomBehavior.scaleBy, 1.3);
    },
    /**
     * Zoom out
     */
    zoomOut() {
      if (!this.zoomBehavior || !this.$refs.svg) {
        this.initZoom();
      }
      const svg = select(this.$refs.svg);
      svg.transition().duration(300).call(this.zoomBehavior.scaleBy, 0.7);
    },
    /**
     * Reset zoom to initial state
     */
    resetZoom() {
      if (!this.zoomBehavior || !this.$refs.svg) {
        this.initZoom();
      }
      const svg = select(this.$refs.svg);
      svg.transition().duration(300).call(
        this.zoomBehavior.transform,
        zoomIdentity,
      );
    },
    /**
     * Fit graph to content
     */
    fitToContent() {
      if (!this.nodes.length || !this.$refs.svg) return;

      // Calculate bounding box
      const padding = 50;
      const minX = Math.min(...this.nodes.map((n) => n.x)) - padding;
      const maxX = Math.max(...this.nodes.map((n) => n.x)) + padding;
      const minY = Math.min(...this.nodes.map((n) => n.y)) - padding;
      const maxY = Math.max(...this.nodes.map((n) => n.y)) + padding;

      const contentWidth = maxY - minY;
      const contentHeight = maxX - minX;

      const scale = Math.min(
        (this.width - this.margin.left - this.margin.right) / contentWidth,
        (this.height - this.margin.top - this.margin.bottom) / contentHeight,
        1, // Don't zoom in beyond 1x
      );

      const translateX = (this.width - contentWidth * scale) / 2 - minY * scale;
      const translateY = (this.height - contentHeight * scale) / 2 - minX * scale;

      const svg = select(this.$refs.svg);
      const transform = zoomIdentity
        .translate(translateX, translateY)
        .scale(scale);

      svg.transition().duration(500).call(
        this.zoomBehavior.transform,
        transform,
      );
    },
    /**
     * Generate SVG path for link (using cubic Bezier curve)
     */
    linkPath(link) {
      const sourceX = link.source.x;
      const sourceY = link.source.y;
      const targetX = link.target.x;
      const targetY = link.target.y;

      // Horizontal Bezier curve (GitHub style)
      const midY = (sourceY + targetY) / 2;

      return `M${sourceY},${sourceX}
              C${midY},${sourceX}
               ${midY},${targetX}
               ${targetY},${targetX}`;
    },
    /**
     * Get CSS class for node based on state
     */
    nodeClass(node) {
      const classes = ['revision-node'];

      if (this.isCurrentRevision(node)) {
        classes.push('current');
      }

      if (this.isSelectedRevision(node)) {
        classes.push('selected');
      }

      return classes.join(' ');
    },
    /**
     * Check if node is current revision
     */
    isCurrentRevision(node) {
      return node.data.id === this.currentRevisionId;
    },
    /**
     * Check if node is selected
     */
    isSelectedRevision(node) {
      return node.data.id === this.selectedRevisionId;
    },
    /**
     * Generate tooltip text for a node
     */
    nodeTooltip(node) {
      const { data } = node;
      const parts = [
        `Revision ${data.revision}`,
        `Description: ${data.description || 'N/A'}`,
        `Created: ${data.created_at || 'N/A'}`,
      ];

      if (this.isCurrentRevision(node)) {
        parts.push('(Current)');
      }

      return parts.join('\n');
    },
    /**
     * Handle node click
     */
    handleNodeClick(node) {
      this.$emit('node-click', node.data);
    },
  },
};
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

/* Links */
.revision-link {
  fill: none;
  stroke: #6c757d;
  stroke-width: 2px;
  opacity: 0.6;
}

/* Nodes */
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
  0%, 100% {
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

/* Zoom controls */
.zoom-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 10;
}

.zoom-controls .btn {
  background-color: rgba(52, 58, 64, 0.9);
  border-color: #6c757d;
  color: #dee2e6;
}

.zoom-controls .btn:hover {
  background-color: rgba(73, 80, 87, 0.9);
  border-color: #adb5bd;
  color: #fff;
}
</style>
