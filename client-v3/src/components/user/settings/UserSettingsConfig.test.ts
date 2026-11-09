import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import UserSettingsConfig from './UserSettingsConfig.vue';
import { useUserStore } from '@/stores/user';

// The backend's EDITABLE_USER_SETTINGS allowlist silently drops any field it
// doesn't recognise (logged, not errored) — a stray or re-added field such as
// the retired `preferred_ui` would be dropped there with nothing failing here.
// This test pins the wire payload shape so that kind of mismatch is caught
// on the frontend instead.
describe('UserSettingsConfig', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('PATCHes exactly the current settings fields, with no stray keys', async () => {
    const userStore = useUserStore();
    userStore.userSettings = {
      enable_script_auto_save: true,
      script_auto_save_interval: 15,
      cue_position_right: true,
      script_text_alignment: 2,
      console_log_level: 'WARN',
      character_mru_sort: false,
      character_combined_dropdown: false,
      table_page_sizes: null,
      default_sd_text_colour: null,
      default_sd_background_colour: null,
      show_current_cue_footer: true,
    };

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => userStore.userSettings,
    });
    vi.stubGlobal('fetch', fetchMock);

    const wrapper = mount(UserSettingsConfig);
    await flushPromises();

    // BForm doesn't resolve in this unit-test environment (no BVN resolver registered),
    // so it renders as a literal <bform> custom element rather than a real <form>.
    await wrapper.find('bform').trigger('submit');
    await flushPromises();

    expect(fetchMock).toHaveBeenCalledTimes(2); // PATCH, then the post-save GET
    const [, patchInit] = fetchMock.mock.calls[0];
    expect(patchInit.method).toBe('PATCH');

    const sentBody = JSON.parse(patchInit.body as string);
    expect(Object.keys(sentBody).sort()).toEqual(Object.keys(userStore.userSettings).sort());
    expect(sentBody.preferred_ui).toBeUndefined();

    vi.unstubAllGlobals();
  });
});
