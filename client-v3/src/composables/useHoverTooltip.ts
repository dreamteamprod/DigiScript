import { ref, computed } from 'vue';

export function useHoverTooltip() {
  const tooltipText = ref('');
  const tooltipVisible = ref(false);
  const tooltipX = ref(0);
  const tooltipY = ref(0);

  function showTooltip(text: string, event: MouseEvent): void {
    tooltipText.value = text;
    tooltipX.value = event.clientX;
    tooltipY.value = event.clientY;
    tooltipVisible.value = true;
  }

  function hideTooltip(): void {
    tooltipVisible.value = false;
  }

  const tooltipStyle = computed(() => ({
    position: 'fixed' as const,
    left: `${tooltipX.value + 12}px`,
    top: `${tooltipY.value - 30}px`,
    zIndex: 9999,
    pointerEvents: 'none' as const,
  }));

  return { tooltipText, tooltipVisible, tooltipStyle, showTooltip, hideTooltip };
}
