<template>
  <div class="show">
    <h1>{{ systemStore.currentShow?.name }}</h1>
    <BContainer fluid class="mx-0 show-config-container">
      <BRow>
        <BCol cols="1">
          <BButtonGroup vertical class="sticky-nav" :style="{ top: navbarHeight + 'px' }">
            <BButton
              :disabled="!shouldViewShowConfig"
              replace
              :to="{ name: 'show-config' }"
              variant="outline-info"
              exact-active-class="active"
            >
              Show
            </BButton>
            <BButton
              :disabled="!shouldViewShowConfig"
              replace
              :to="{ name: 'show-config-stage' }"
              variant="outline-info"
              active-class="active"
            >
              Staging
            </BButton>
            <BButton
              :disabled="!shouldViewShowConfig"
              replace
              :to="{ name: 'show-config-cast' }"
              variant="outline-info"
              active-class="active"
            >
              Cast
            </BButton>
            <BButton
              :disabled="!shouldViewShowConfig"
              replace
              :to="{ name: 'show-config-characters' }"
              variant="outline-info"
              active-class="active"
            >
              Characters
            </BButton>
            <BButton
              :disabled="!shouldViewShowConfig"
              replace
              :to="{ name: 'show-config-acts-scenes' }"
              variant="outline-info"
              active-class="active"
            >
              Acts & Scenes
            </BButton>
            <BButton
              :disabled="!shouldShowScriptConfig"
              replace
              :to="{ name: 'show-config-script-revisions' }"
              variant="outline-info"
              active-class="active"
            >
              Revisions
            </BButton>
            <BButton
              :disabled="!shouldShowScriptConfig"
              replace
              :to="{ name: 'show-config-script' }"
              variant="outline-info"
              active-class="active"
            >
              Script
            </BButton>
            <BButton
              :disabled="!shouldShowCueConfig"
              replace
              :to="{ name: 'show-config-cues' }"
              variant="outline-info"
              active-class="active"
            >
              Cues
            </BButton>
            <BButton
              :disabled="!shouldViewShowConfig"
              replace
              :to="{ name: 'show-config-mics' }"
              variant="outline-info"
              active-class="active"
            >
              Mics
            </BButton>
            <BButton
              :disabled="!shouldShowSessionConfig"
              replace
              :to="{ name: 'show-sessions' }"
              variant="outline-info"
              active-class="active"
            >
              Sessions
            </BButton>
          </BButtonGroup>
        </BCol>
        <BCol cols="11">
          <RouterView />
        </BCol>
      </BRow>
    </BContainer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeMount, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { useSystemStore } from '@/stores/system';
import { toast } from '@/js/toast';

const router = useRouter();
const systemStore = useSystemStore();

const navbarHeight = ref(0);

const shouldViewShowConfig = computed(() => systemStore.isShowEditor || systemStore.isShowReader);
const shouldShowCueConfig = computed(
  () => shouldViewShowConfig.value || systemStore.isCueEditor || systemStore.isCueReader
);
const shouldShowScriptConfig = computed(
  () => shouldViewShowConfig.value || systemStore.isScriptEditor || systemStore.isScriptReader
);
const shouldShowSessionConfig = computed(
  () => shouldViewShowConfig.value || systemStore.isShowExecutor
);
const requiresRedirect = computed(
  () =>
    !shouldViewShowConfig.value &&
    !shouldShowCueConfig.value &&
    !shouldShowScriptConfig.value &&
    !shouldShowSessionConfig.value
);

onBeforeMount(() => {
  if (!shouldViewShowConfig.value) {
    if (shouldShowCueConfig.value) {
      router.replace({ name: 'show-config-cues' });
    } else if (shouldShowScriptConfig.value) {
      // Fix V2 double-redirect bug — redirect to revisions only
      router.replace({ name: 'show-config-script-revisions' });
    } else if (shouldShowSessionConfig.value) {
      router.replace({ name: 'show-sessions' });
    } else {
      toast.warning('Something went wrong viewing show config page');
      router.replace('/');
    }
  }
});

watch(requiresRedirect, (val) => {
  if (val) {
    toast.warning('Something went wrong viewing show config page');
    router.replace('/');
  }
});

function calculateNavbarHeight(): void {
  const navbar = document.querySelector('.navbar');
  navbarHeight.value = navbar ? (navbar as HTMLElement).offsetHeight : 56;
}

onMounted(() => {
  calculateNavbarHeight();
  window.addEventListener('resize', calculateNavbarHeight);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', calculateNavbarHeight);
});
</script>

<style scoped>
.show-config-container {
  position: relative;
}

.sticky-nav {
  position: sticky;
  padding: 10px 0;
  background: var(--bs-body-bg);
}
</style>
