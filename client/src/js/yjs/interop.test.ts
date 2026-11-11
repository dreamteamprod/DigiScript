import { describe, it, expect, vi } from 'vitest';
import * as Y from 'yjs';
import { ScriptDocProvider } from './ScriptDocProvider';
import { ydocPagesToPlain } from './yjsSnapshot';
import stateFixture from './__fixtures__/pycrdt_state.json';

// The fixture is a full doc state produced by real pycrdt through the production
// build_ydoc (regenerate via server/test/helpers/yjs_interop_fixture.py). Every other
// test in this folder builds its "server" updates with Yjs itself, so none of them
// would notice the two implementations drifting apart on the wire format.
describe('pycrdt → Yjs interop', () => {
  it('applies a real server full-state sync and reads it back through the snapshot builder', () => {
    const doc = new Y.Doc();
    const send = vi.fn();
    const provider = new ScriptDocProvider(doc, send);

    const applied = provider.applySync({ step: 0, payload: stateFixture.state });

    expect(applied).toBe(true);
    expect(send).not.toHaveBeenCalled();
    expect(doc.getMap('meta').get('revision_id')).toBe(stateFixture.revision_id);

    const pages = ydocPagesToPlain(doc);
    // Page 3 is the empty trailing page the server always adds (clients never create pages).
    expect(Object.keys(pages).sort()).toEqual(['1', '2', '3']);
    expect(pages['3']).toEqual([]);
    expect(pages['1'].map((l) => l.parts[0].line_text)).toEqual(['Hello world', 'Héllo ☃ wörld']);
    expect(pages['2'][0].parts[0].line_text).toBe('Second page');
    expect(pages['1'][0]).toMatchObject({
      _id: '1',
      id: 1,
      act_id: 1,
      scene_id: 2,
      stage_direction_style_id: null,
    });
    expect(pages['1'][0].parts[0]).toMatchObject({
      id: 10,
      character_id: 3,
      character_group_id: null,
    });

    provider.destroy();
  });
});
