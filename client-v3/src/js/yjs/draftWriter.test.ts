import { describe, it, expect } from 'vitest';
import * as Y from 'yjs';
import {
  LOCAL_EDIT_ORIGIN,
  DraftWriteError,
  addLine,
  deleteLine,
  setLineField,
  setLineActScene,
  addPart,
  removePart,
  setPartField,
  setPartCharacter,
  getPartText,
  setPartText,
} from './draftWriter';
import { ydocPagesToPlain, ydocDeletedLineIds } from './yjsSnapshot';
import { snapshotPagesToScriptLines } from './draftAdapter';

/** A doc shaped like the server's build_ydoc output: pages 1-2 with DB-id lines, empty page 3. */
function makeServerDoc(): Y.Doc {
  const doc = new Y.Doc();
  doc.getMap('meta').set('revision_id', 7);
  doc.getArray('deleted_line_ids');
  const pages = doc.getMap('pages');
  const addExisting = (page: string, id: string, text: string) => {
    let array = pages.get(page) as Y.Array<Y.Map<unknown>> | undefined;
    if (!array) {
      array = new Y.Array<Y.Map<unknown>>();
      pages.set(page, array);
    }
    const line = new Y.Map<unknown>();
    array.push([line]);
    line.set('_id', id);
    line.set('act_id', 1);
    line.set('scene_id', 2);
    line.set('line_type', 1);
    line.set('stage_direction_style_id', 0);
    const parts = new Y.Array<Y.Map<unknown>>();
    line.set('parts', parts);
    const part = new Y.Map<unknown>();
    parts.push([part]);
    part.set('_id', `${id}0`);
    part.set('part_index', 0);
    part.set('character_id', 3);
    part.set('character_group_id', 0);
    part.set('line_text', new Y.Text(text));
  };
  addExisting('1', '1', 'Hello world');
  addExisting('1', '2', 'Second line');
  addExisting('2', '3', 'Page two');
  pages.set('3', new Y.Array<Y.Map<unknown>>());
  return doc;
}

function replica(source: Y.Doc): Y.Doc {
  const doc = new Y.Doc();
  Y.applyUpdate(doc, Y.encodeStateAsUpdate(source));
  return doc;
}

function sync(a: Y.Doc, b: Y.Doc): void {
  Y.applyUpdate(b, Y.encodeStateAsUpdate(a, Y.encodeStateVector(b)));
  Y.applyUpdate(a, Y.encodeStateAsUpdate(b, Y.encodeStateVector(a)));
}

function ids(doc: Y.Doc, page: number): string[] {
  return ydocPagesToPlain(doc)[String(page)].map((l) => l._id);
}

function counter(prefix = 'new'): () => string {
  let n = 0;
  return () => {
    n += 1;
    return `${prefix}-${n}`;
  };
}

/** Records the origin of every update a doc emits. */
function recordUpdates(doc: Y.Doc): unknown[] {
  const origins: unknown[] = [];
  doc.on('update', (_u: Uint8Array, origin: unknown) => origins.push(origin));
  return origins;
}

describe('addLine', () => {
  it('appends an empty line with the exact structure the server builds and reads', () => {
    const doc = makeServerDoc();

    const id = addLine(
      doc,
      3,
      { lineType: 1, actId: 1, sceneId: 2, stageDirectionStyleId: 9 },
      { newId: counter() }
    );

    expect(id).toBe('new-1');
    const line = (doc.getMap('pages').get('3') as Y.Array<Y.Map<unknown>>).get(0);
    expect([...line.keys()].sort()).toEqual([
      '_id',
      'act_id',
      'line_type',
      'parts',
      'scene_id',
      'stage_direction_style_id',
    ]);
    expect(line.get('_id')).toBe('new-1');
    expect(line.get('act_id')).toBe(1);
    expect(line.get('scene_id')).toBe(2);
    expect(line.get('line_type')).toBe(1);
    expect(line.get('stage_direction_style_id')).toBe(9);
    expect(line.get('parts')).toBeInstanceOf(Y.Array);
  });

  it('stores "no value" as the 0 sentinel, not null', () => {
    const doc = makeServerDoc();
    addLine(doc, 3, { lineType: 2 }, { newId: counter() });

    const line = (doc.getMap('pages').get('3') as Y.Array<Y.Map<unknown>>).get(0);
    expect(line.get('act_id')).toBe(0);
    expect(line.get('scene_id')).toBe(0);
    expect(line.get('stage_direction_style_id')).toBe(0);
  });

  it('inserts at the given index and clamps out-of-range indexes', () => {
    const doc = makeServerDoc();

    addLine(doc, 1, { lineType: 1, index: 1 }, { newId: counter('mid') });
    addLine(doc, 1, { lineType: 1, index: 99 }, { newId: counter('end') });
    addLine(doc, 1, { lineType: 1, index: -5 }, { newId: counter('start') });

    expect(ids(doc, 1)).toEqual(['start-1', '1', 'mid-1', '2', 'end-1']);
  });

  it('is exactly one update, tagged as a local edit', () => {
    const doc = makeServerDoc();
    const origins = recordUpdates(doc);

    addLine(doc, 1, { lineType: 1 }, { newId: counter() });

    expect(origins).toEqual([LOCAL_EDIT_ORIGIN]);
  });

  it('refuses to create a page — only the server creates pages', () => {
    const doc = makeServerDoc();
    const before = Y.encodeStateVector(doc);

    expect(() => addLine(doc, 4, { lineType: 1 })).toThrow(DraftWriteError);

    expect(Y.encodeStateVector(doc)).toEqual(before);
    expect(doc.getMap('pages').has('4')).toBe(false);
  });

  it('generates a UUID id by default', () => {
    const doc = makeServerDoc();
    const id = addLine(doc, 1, { lineType: 1 });
    expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-/);
  });
});

describe('deleteLine', () => {
  it('removes a saved line and records its DB id for the server to delete', () => {
    const doc = makeServerDoc();

    deleteLine(doc, 1, '2');

    expect(ids(doc, 1)).toEqual(['1']);
    expect(ydocDeletedLineIds(doc)).toEqual([2]);
  });

  it('removes a never-saved line without recording anything', () => {
    const doc = makeServerDoc();
    const id = addLine(doc, 1, { lineType: 1 }, { newId: counter() });

    deleteLine(doc, 1, id);

    expect(ids(doc, 1)).toEqual(['1', '2']);
    expect(ydocDeletedLineIds(doc)).toEqual([]);
    expect(doc.getArray('deleted_line_ids').length).toBe(0);
  });

  it('is one update', () => {
    const doc = makeServerDoc();
    const origins = recordUpdates(doc);

    deleteLine(doc, 1, '1');

    expect(origins).toEqual([LOCAL_EDIT_ORIGIN]);
  });

  it('finds the line by id, not position, after another line was inserted before it', () => {
    const doc = makeServerDoc();
    addLine(doc, 1, { lineType: 1, index: 0 }, { newId: counter() });

    deleteLine(doc, 1, '2');

    expect(ids(doc, 1)).toEqual(['new-1', '1']);
  });

  it('throws, and writes nothing, for an unknown line or page', () => {
    const doc = makeServerDoc();
    const before = Y.encodeStateVector(doc);

    expect(() => deleteLine(doc, 1, 'nope')).toThrow(DraftWriteError);
    expect(() => deleteLine(doc, 9, '1')).toThrow(DraftWriteError);

    expect(Y.encodeStateVector(doc)).toEqual(before);
    expect(doc.getArray('deleted_line_ids').length).toBe(0);
  });
});

describe('line fields', () => {
  it('sets a field, storing null as 0', () => {
    const doc = makeServerDoc();

    setLineField(doc, 1, '1', 'stage_direction_style_id', 5);
    setLineField(doc, 1, '1', 'act_id', null);

    const line = ydocPagesToPlain(doc)['1'][0];
    expect(line.stage_direction_style_id).toBe(5);
    expect(line.act_id).toBeNull();
  });

  it('sets act and scene together as one update', () => {
    const doc = makeServerDoc();
    const origins = recordUpdates(doc);

    setLineActScene(doc, 2, '3', 7, 8);

    const line = ydocPagesToPlain(doc)['2'][0];
    expect([line.act_id, line.scene_id]).toEqual([7, 8]);
    expect(origins).toEqual([LOCAL_EDIT_ORIGIN]);
  });
});

describe('parts', () => {
  it('appends a part with the next part_index, character, and empty text', () => {
    const doc = makeServerDoc();

    const partId = addPart(doc, 1, '1', { characterId: 4 }, { newId: counter('p') });

    const parts = ydocPagesToPlain(doc)['1'][0].parts;
    expect(partId).toBe('p-1');
    expect(parts.map((p) => p._id)).toEqual(['10', 'p-1']);
    expect(parts[1]).toMatchObject({
      part_index: 1,
      character_id: 4,
      character_group_id: null,
      line_text: '',
    });
  });

  it("stores a new part's text as a Y.Text", () => {
    const doc = makeServerDoc();
    const partId = addPart(doc, 1, '1');

    expect(getPartText(doc, 1, '1', partId)).toBeInstanceOf(Y.Text);
  });

  it('removes a part and renumbers the ones after it 0..n-1', () => {
    const doc = makeServerDoc();
    const p1 = addPart(doc, 1, '1', {}, { newId: counter('p') });
    addPart(doc, 1, '1', {}, { newId: counter('q') });

    removePart(doc, 1, '1', '10');

    const parts = ydocPagesToPlain(doc)['1'][0].parts;
    expect(parts.map((p) => [p._id, p.part_index])).toEqual([
      [p1, 0],
      ['q-1', 1],
    ]);
  });

  it('sets character and group together, and either alone; null becomes 0', () => {
    const doc = makeServerDoc();

    setPartCharacter(doc, 1, '1', '10', null, 6);
    expect(ydocPagesToPlain(doc)['1'][0].parts[0]).toMatchObject({
      character_id: null,
      character_group_id: 6,
    });

    setPartField(doc, 1, '1', '10', 'character_id', 2);
    setPartField(doc, 1, '1', '10', 'character_group_id', null);
    expect(ydocPagesToPlain(doc)['1'][0].parts[0]).toMatchObject({
      character_id: 2,
      character_group_id: null,
    });
  });

  it('throws for an unknown part', () => {
    const doc = makeServerDoc();
    expect(() => removePart(doc, 1, '1', 'nope')).toThrow(DraftWriteError);
    expect(() => setPartField(doc, 1, '1', 'nope', 'character_id', 1)).toThrow(DraftWriteError);
  });
});

describe('setPartText', () => {
  it('writes the minimal edit as a single local update', () => {
    const doc = makeServerDoc();
    const origins = recordUpdates(doc);
    const deltas: unknown[] = [];
    getPartText(doc, 1, '1', '10').observe((event) => deltas.push(event.delta));

    const changed = setPartText(doc, 1, '1', '10', 'Hello brave world');

    expect(changed).toBe(true);
    expect(deltas).toEqual([[{ retain: 6 }, { insert: 'brave ' }]]);
    expect(origins).toEqual([LOCAL_EDIT_ORIGIN]);
  });

  it('does nothing when the text is unchanged', () => {
    const doc = makeServerDoc();
    const origins = recordUpdates(doc);

    expect(setPartText(doc, 1, '1', '10', 'Hello world')).toBe(false);
    expect(origins).toEqual([]);
  });
});

describe('two editors', () => {
  it('both keep the lines they add to the same trailing page', () => {
    const server = makeServerDoc();
    const a = replica(server);
    const b = replica(server);

    addLine(a, 3, { lineType: 1 }, { newId: counter('a') });
    addLine(b, 3, { lineType: 1 }, { newId: counter('b') });
    sync(a, b);

    expect(ids(a, 3).sort()).toEqual(['a-1', 'b-1']);
    expect(ids(b, 3).sort()).toEqual(['a-1', 'b-1']);
  });

  it('address the line they mean even after the other editor inserted before it', () => {
    const server = makeServerDoc();
    const a = replica(server);
    const b = replica(server);

    addLine(a, 1, { lineType: 1, index: 0 }, { newId: counter('a') }); // shifts every index
    sync(a, b);
    setPartText(b, 1, '2', '20', 'Edited by B');
    sync(a, b);

    expect(ydocPagesToPlain(a)['1'].find((l) => l._id === '2')!.parts[0].line_text).toBe(
      'Edited by B'
    );
  });

  it('merge concurrent typing in the same field', () => {
    const server = makeServerDoc();
    const a = replica(server);
    const b = replica(server);

    setPartText(a, 1, '1', '10', 'Oh, Hello world');
    setPartText(b, 1, '1', '10', 'Hello world!');
    sync(a, b);

    expect(ydocPagesToPlain(a)['1'][0].parts[0].line_text).toBe('Oh, Hello world!');
    expect(ydocPagesToPlain(b)['1'][0].parts[0].line_text).toBe('Oh, Hello world!');
  });

  it('converge when one deletes a line the other is editing', () => {
    const server = makeServerDoc();
    const a = replica(server);
    const b = replica(server);

    deleteLine(a, 1, '1');
    setPartText(b, 1, '1', '10', 'Edited');
    sync(a, b);

    expect(ids(a, 1)).toEqual(ids(b, 1));
    expect(ids(a, 1)).toEqual(['2']);
  });
});

describe('snapshotPagesToScriptLines (read adapter)', () => {
  it('presents the draft in the ScriptLine shape existing components consume', () => {
    const doc = makeServerDoc();
    const newId = addLine(doc, 1, { lineType: 2, actId: 1, sceneId: 2 }, { newId: counter() });
    addPart(doc, 1, newId, { characterId: 5 }, { newId: counter('p') });
    setPartText(doc, 1, newId, 'p-1', 'Enter left');

    const pages = snapshotPagesToScriptLines(ydocPagesToPlain(doc));

    const saved = pages['1'][0];
    expect(saved).toMatchObject({
      _id: '1',
      id: 1,
      act_id: 1,
      scene_id: 2,
      page: 1,
      line_type: 1,
      stage_direction_style_id: null,
    });
    expect(saved.line_parts[0]).toMatchObject({
      _id: '10',
      id: 10,
      line_id: 1,
      part_index: 0,
      character_id: 3,
      character_group_id: null,
      line_text: 'Hello world',
    });

    const unsaved = pages['1'][2];
    expect(unsaved.id).toBeNull(); // not in the DB yet
    expect(unsaved._id).toBe('new-1');
    expect(unsaved.line_type).toBe(2);
    expect(unsaved.line_parts[0]).toMatchObject({
      id: null,
      line_id: null,
      line_text: 'Enter left',
    });
  });

  it('carries the page number and keeps the empty trailing page', () => {
    const pages = snapshotPagesToScriptLines(ydocPagesToPlain(makeServerDoc()));

    expect(Object.keys(pages).sort()).toEqual(['1', '2', '3']);
    expect(pages['2'][0].page).toBe(2);
    expect(pages['3']).toEqual([]);
  });
});
