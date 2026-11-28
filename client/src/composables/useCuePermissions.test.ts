import { beforeEach, describe, expect, it } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { useCuePermissions } from './useCuePermissions';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import { useUserStore } from '@/stores/user';

const types = [1, 2, 3].map((id) => ({
  id,
  show_id: 1,
  prefix: `T${id}`,
  description: null,
  colour: '#fff',
}));

function setup(
  options: { admin?: boolean; cuetypes?: [number, number][]; session?: boolean } = {}
) {
  const { admin = false, cuetypes = [], session = false } = options;
  useShowStore().cueTypes = types;
  useShowStore().currentSession = session ? ({ id: 1 } as never) : null;
  useSystemStore().rbacRoles = [
    { key: 'READ', value: 1 },
    { key: 'WRITE', value: 2 },
  ];
  useUserStore().currentUser = { id: 1, is_admin: admin } as never;
  useUserStore().currentRbac = { cuetypes } as never;
  return useCuePermissions();
}

describe('useCuePermissions', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('lets an admin write every cue type', () => {
    const p = setup({ admin: true });

    expect([...p.writableTypeIds.value].sort()).toEqual([1, 2, 3]);
    expect(p.canAddCues.value).toBe(true);
    expect(p.canWriteType(2)).toBe(true);
  });

  it('lets someone write only the types their role has the write bit for', () => {
    const p = setup({
      cuetypes: [
        [1, 2],
        [2, 1],
        [3, 3],
      ],
    });

    expect([...p.writableTypeIds.value].sort()).toEqual([1, 3]);
    expect(p.canWriteType(1)).toBe(true);
    expect(p.canWriteType(2)).toBe(false);
    expect(p.canWriteType(3)).toBe(true);
  });

  it('cannot add cues without write access to any type', () => {
    const p = setup({ cuetypes: [[1, 1]] });

    expect(p.canAddCues.value).toBe(false);
    expect([...p.writableTypeIds.value]).toEqual([]);
  });

  it('is not fooled by write access to a type this show does not have', () => {
    const p = setup({ cuetypes: [[99, 2]] });

    expect(p.canAddCues.value).toBe(false);
  });

  it('cannot write a missing type', () => {
    const p = setup({ admin: true });

    expect(p.canWriteType(null)).toBe(false);
    expect(p.canWriteType(undefined)).toBe(false);
    expect(p.canWriteType(42)).toBe(false);
  });

  it('follows a session starting and ending', () => {
    const p = setup();
    expect(p.isLiveSession.value).toBe(false);

    useShowStore().currentSession = { id: 7 } as never;
    expect(p.isLiveSession.value).toBe(true);

    useShowStore().currentSession = null;
    expect(p.isLiveSession.value).toBe(false);
  });

  it('follows the cue types changing', () => {
    const p = setup({ admin: true });

    useShowStore().cueTypes = [types[0]];

    expect([...p.writableTypeIds.value]).toEqual([1]);
  });
});
