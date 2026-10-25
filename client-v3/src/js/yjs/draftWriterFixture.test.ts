import { createHash } from 'node:crypto';
import { describe, it, expect } from 'vitest';
import * as Y from 'yjs';
import stateFixture from './__fixtures__/pycrdt_state.json';
import { addLine, addPart, deleteLine, setLineActScene, setPartText } from './draftWriter';
import { bytesToBase64, base64ToBytes } from './base64';

/**
 * Cross-language pin for the draft writer: a realistic sequence of editor operations is
 * applied to the doc the *server* built (pycrdt_state.json), and the resulting update is
 * committed as writer_ops.json. `test_draft_writer_interop.py` applies that update in
 * pycrdt and runs the real `extract_lines_from_ydoc` — the first step of the server's
 * save — asserting the writer produced exactly what save expects. While the editor isn't
 * wired into a page, this stands in for an end-to-end save test.
 *
 * The fixture is a Vitest file snapshot: it is only rewritten with `vitest -u`, and the
 * client id and generated ids are fixed so the bytes are deterministic. If this test
 * fails, the writer's wire output changed — check the server-side test still agrees,
 * then regenerate with `pnpm exec vitest run -u src/js/yjs/draftWriterFixture.test.ts`.
 */

function makeIds(): () => string {
  let n = 0;
  return () => {
    n += 1;
    return `n-${n}`;
  };
}

function buildEditedDoc(): { doc: Y.Doc; before: Uint8Array } {
  const doc = new Y.Doc();
  doc.clientID = 4242; // fixed, so the encoded update is byte-for-byte reproducible
  Y.applyUpdate(doc, base64ToBytes(stateFixture.state));
  const before = Y.encodeStateVector(doc);
  const newId = makeIds();

  // 1. a new dialogue line at the end of page 1, with a part, character and text
  const dialogue = addLine(
    doc,
    1,
    { lineType: 1, actId: 1, sceneId: 2, part: { characterId: 3 } },
    { newId }
  );
  setPartText(doc, 1, dialogue.lineUid, dialogue.partUid!, 'Brand new');

  // 2. edit an existing line's text (minimal diff)
  setPartText(doc, 1, '1', '10', 'Hello brave world');

  // 3. delete an existing line (recorded in deleted_line_ids)
  deleteLine(doc, 1, '2');

  // 4. insert a stage direction at the top of page 1 with a style
  const direction = addLine(
    doc,
    1,
    { lineType: 2, actId: 1, sceneId: 2, stageDirectionStyleId: 7, index: 0 },
    { newId }
  );
  setPartText(doc, 1, direction.lineUid, direction.partUid!, 'Enter stage left');

  // 5. move an existing line to another act/scene and give it a second part
  setLineActScene(doc, 2, '3', 9, 8);
  const chorus = addPart(doc, 2, '3', { characterGroupId: 4 }, { newId });
  setPartText(doc, 2, '3', chorus!, 'Chorus');

  // 6. start a line on the server-created trailing page (page 3)
  addLine(doc, 3, { lineType: 4 }, { newId }); // a spacing line: no parts

  return { doc, before };
}

describe('draft writer → server interop fixture', () => {
  it('produces the committed update (see draftWriterFixture.test.ts header)', async () => {
    const { doc, before } = buildEditedDoc();
    const diff = Y.encodeStateAsUpdate(doc, before);

    const fixture = {
      // Ties the update to the exact server-built state it was made on.
      base_sha256: createHash('sha256').update(stateFixture.state).digest('hex'),
      diff: bytesToBase64(diff),
    };

    await expect(`${JSON.stringify(fixture, null, 2)}\n`).toMatchFileSnapshot(
      './__fixtures__/writer_ops.json'
    );
  });

  it('leaves the JS doc in the state the server-side test expects', () => {
    const { doc } = buildEditedDoc();
    const pages = doc.getMap('pages');
    const ids = (page: string) =>
      (pages.get(page) as Y.Array<Y.Map<unknown>>).toArray().map((l) => l.get('_uid'));

    expect(ids('1')).toEqual(['n-3', '1', 'n-1']);
    expect(ids('2')).toEqual(['3']);
    expect(ids('3')).toEqual(['n-6']);
    expect(doc.getArray('deleted_line_ids').toArray()).toEqual(['2']);
  });
});
