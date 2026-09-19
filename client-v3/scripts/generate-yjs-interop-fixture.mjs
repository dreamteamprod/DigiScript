// Produces src/js/yjs/__fixtures__/yjs_edit.json: a real Yjs diff made on top of the
// committed pycrdt_state.json, consumed by the server's test_yjs_interop.py. See
// server/test/helpers/yjs_interop_fixture.py for why both sides are committed.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as Y from 'yjs';

const dir = path.join(path.dirname(fileURLToPath(import.meta.url)), '../src/js/yjs/__fixtures__');
const { state } = JSON.parse(fs.readFileSync(path.join(dir, 'pycrdt_state.json'), 'utf8'));

const doc = new Y.Doc();
Y.applyUpdate(doc, Buffer.from(state, 'base64'));
const before = Y.encodeStateVector(doc);

doc.transact(() => {
  const line = doc.getMap('pages').get('1').get(0);
  line.get('parts').get(0).get('line_text').insert(5, ' there');
  line.set('act_id', 9);
}, 'local-edit');

const diff = Y.encodeStateAsUpdate(doc, before);
fs.writeFileSync(
  path.join(dir, 'yjs_edit.json'),
  `${JSON.stringify({ diff: Buffer.from(diff).toString('base64') }, null, 2)}\n`
);
console.log('wrote yjs_edit.json');
