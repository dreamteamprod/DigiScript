import { describe, it, expect, beforeEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { mount } from '@vue/test-utils';
import ConfigScript from './ConfigScript.vue';
import { useSystemStore } from '@/stores/system';
import ScriptEditor from '@/components/show/config/script/ScriptEditor.vue';
import CollabScriptEditor from '@/components/show/config/script/CollabScriptEditor.vue';

describe('ConfigScript', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  function mountView() {
    return mount(ConfigScript, {
      global: {
        stubs: {
          ScriptEditor: true,
          CollabScriptEditor: true,
          StageDirectionStyles: true,
          BTabs: { template: '<div><slot /></div>' },
          BTab: { template: '<div><slot /></div>' },
        },
      },
    });
  }

  it('renders the classic editor when collaborative_script_editing is off', () => {
    useSystemStore().settings = { collaborative_script_editing: false } as never;
    const w = mountView();

    expect(w.findComponent(ScriptEditor).exists()).toBe(true);
    expect(w.findComponent(CollabScriptEditor).exists()).toBe(false);
  });

  it('renders the collaborative editor when collaborative_script_editing is on', () => {
    useSystemStore().settings = { collaborative_script_editing: true } as never;
    const w = mountView();

    expect(w.findComponent(CollabScriptEditor).exists()).toBe(true);
    expect(w.findComponent(ScriptEditor).exists()).toBe(false);
  });
});
