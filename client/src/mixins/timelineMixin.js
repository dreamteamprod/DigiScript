import { mapGetters } from 'vuex';

/**
 * Shared mixin for timeline visualization components (MicTimeline, StageTimeline).
 * Provides common SVG rendering utilities, layout calculations, and export functionality.
 *
 * This mixin assumes the component has:
 * - A Vuex store with ACT_BY_ID and ORDERED_SCENES getters
 * - A `scenes` computed property returning the ordered list of scenes
 * - A `rows` computed property returning items to display as rows
 * - A `$refs.svg` reference to the SVG element
 *
 * Components using this mixin should implement:
 * - computed.scenes - array of scene objects in order
 * - computed.rows - array of row items (e.g., mics, props, scenery)
 * - methods for generating bars specific to their domain
 */
export default {
  data() {
    return {
      margin: {
        top: 75,
        right: 20,
        bottom: 20,
        left: 150,
      },
      sceneWidth: 100,
      rowHeight: 50,
      barPadding: 6,
    };
  },

  computed: {
    ...mapGetters(['ACT_BY_ID']),
    contentWidth() {
      return this.scenes.length * this.sceneWidth;
    },
    contentHeight() {
      return this.rows.length * this.rowHeight;
    },
    totalWidth() {
      return this.margin.left + this.contentWidth + this.margin.right;
    },
    totalHeight() {
      return this.margin.top + this.contentHeight + this.margin.bottom;
    },
    actGroups() {
      const groups = [];
      let currentAct = null;
      let startIndex = 0;

      this.scenes.forEach((scene, index) => {
        const act = this.ACT_BY_ID(scene.act);
        if (!act) return;

        if (currentAct !== act.id) {
          if (currentAct !== null) {
            groups.push({
              actId: currentAct,
              actName: this.ACT_BY_ID(currentAct)?.name || 'Unknown',
              startX: this.getSceneX(startIndex),
              width: this.getSceneX(index) - this.getSceneX(startIndex),
            });
          }
          currentAct = act.id;
          startIndex = index;
        }
      });

      // Push final group
      if (currentAct !== null) {
        groups.push({
          actId: currentAct,
          actName: this.ACT_BY_ID(currentAct)?.name || 'Unknown',
          startX: this.getSceneX(startIndex),
          width: this.getSceneX(this.scenes.length) - this.getSceneX(startIndex),
        });
      }

      return groups;
    },
  },

  methods: {
    getSceneX(sceneIndex) {
      return sceneIndex * this.sceneWidth;
    },
    getRowY(rowIndex) {
      return rowIndex * this.rowHeight;
    },
    getColorForEntity(entityId, entityType) {
      // Golden ratio angle provides optimal distribution across hue spectrum
      const GOLDEN_RATIO_CONJUGATE = 137.508;

      // Different offsets for different entity types to avoid collisions
      const typeOffsets = {
        mic: 0,
        character: 120,
        cast: 240,
        prop: 60,
        scenery: 180,
      };

      const offset = typeOffsets[entityType] || 0;
      const hue = (entityId * GOLDEN_RATIO_CONJUGATE + offset) % 360;

      // Use high saturation and medium lightness for vibrant, visible colors
      return `hsl(${hue}, 70%, 50%)`;
    },
    groupConsecutiveScenes(allocations, sceneIdField = 'scene_id') {
      if (!allocations || allocations.length === 0) {
        return [];
      }

      const segments = [];
      let currentSegment = null;

      this.scenes.forEach((scene, sceneIndex) => {
        const hasAllocation = allocations.some((a) => a[sceneIdField] === scene.id);

        if (hasAllocation) {
          if (currentSegment) {
            // Extend current segment
            currentSegment.endIndex = sceneIndex;
            currentSegment.endScene = scene.name;
          } else {
            // Start new segment
            currentSegment = {
              startIndex: sceneIndex,
              endIndex: sceneIndex,
              startScene: scene.name,
              endScene: scene.name,
            };
          }
        } else if (currentSegment) {
          // End current segment
          segments.push(currentSegment);
          currentSegment = null;
        }
      });

      // Push final segment
      if (currentSegment) {
        segments.push(currentSegment);
      }

      return segments;
    },
    exportTimeline(filenamePrefix = 'timeline', viewModeName = '') {
      const svgElement = this.$refs.svg;
      if (!svgElement) return;

      // Create a clone of the SVG to avoid modifying the original
      const svgClone = svgElement.cloneNode(true);

      // Inline critical styles for export (for print-friendly output)
      this.applyExportStyles(svgClone);

      // Serialize the SVG to a string
      const serializer = new XMLSerializer();
      const svgString = serializer.serializeToString(svgClone);

      // Create a blob and download link
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const img = new Image();

      // Set canvas size to SVG size
      canvas.width = this.totalWidth;
      canvas.height = this.totalHeight;

      img.onload = () => {
        // Draw white background for print-friendly output
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Draw the SVG image
        ctx.drawImage(img, 0, 0);

        // Convert canvas to blob and download
        canvas.toBlob((blob) => {
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

      // Create a data URL from the SVG string
      const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
      const svgUrl = URL.createObjectURL(svgBlob);
      img.src = svgUrl;
    },
    applyExportStyles(svgClone) {
      // Style scene dividers (vertical grid lines)
      svgClone.querySelectorAll('.scene-divider').forEach((el) => {
        el.setAttribute('stroke', '#495057');
        el.setAttribute('stroke-width', '1');
        el.setAttribute('opacity', '0.4');
      });

      // Style row separators (horizontal grid lines)
      svgClone.querySelectorAll('.row-separator').forEach((el) => {
        el.setAttribute('stroke', '#495057');
        el.setAttribute('stroke-width', '1');
        el.setAttribute('opacity', '0.3');
      });

      // Style act headers and labels
      svgClone.querySelectorAll('.act-header').forEach((el) => {
        el.setAttribute('fill', '#e9ecef');
        el.setAttribute('stroke', '#495057');
        el.setAttribute('stroke-width', '1');
      });

      svgClone.querySelectorAll('.act-label').forEach((el) => {
        el.setAttribute('fill', '#212529');
        el.setAttribute('font-size', '14');
        el.setAttribute('font-weight', '600');
      });

      // Style scene labels
      svgClone.querySelectorAll('.scene-label').forEach((el) => {
        el.setAttribute('fill', '#495057');
        el.setAttribute('font-size', '11');
      });

      // Style row labels
      svgClone.querySelectorAll('.row-label').forEach((el) => {
        el.setAttribute('fill', '#212529');
        el.setAttribute('font-size', '12');
        el.setAttribute('font-weight', '500');
      });

      // Style allocation bars (keep their colors but add stroke)
      svgClone.querySelectorAll('.allocation-bar').forEach((el) => {
        el.setAttribute('stroke', '#212529');
        el.setAttribute('stroke-width', '1');
      });

      // Style bar labels
      svgClone.querySelectorAll('.bar-label').forEach((el) => {
        el.setAttribute('fill', '#ffffff');
        el.setAttribute('font-weight', '600');
        el.setAttribute('style', 'text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8)');
      });
    },
  },
};
