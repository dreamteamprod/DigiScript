/**
 * Vue 2.7 ↔ Yjs reactive bindings.
 *
 * These utilities create reactive Vue objects that stay in sync with
 * Yjs shared types (Y.Map, Y.Array, Y.Text). Changes from remote
 * clients are reflected in Vue reactivity, and local changes update
 * the Yjs types.
 *
 * Pattern:
 *   Yjs type → observe → Vue.set() on reactive proxy
 *   User input → update Yjs type → observe fires → other clients see change
 */

import Vue from 'vue';

export function useYMap(ymap, keys = null) {
  const data = Vue.observable({});

  if (keys) {
    keys.forEach((key) => {
      Vue.set(data, key, _unwrapYjsValue(ymap.get(key)));
    });
  } else {
    ymap.forEach((value, key) => {
      Vue.set(data, key, _unwrapYjsValue(value));
    });
  }

  const observer = (event) => {
    event.changes.keys.forEach((change, key) => {
      if (keys && !keys.includes(key)) return;

      if (change.action === 'add' || change.action === 'update') {
        Vue.set(data, key, _unwrapYjsValue(ymap.get(key)));
      } else if (change.action === 'delete') {
        Vue.delete(data, key);
      }
    });
  };

  ymap.observe(observer);

  return {
    data,
    set(key, value) {
      ymap.set(key, value);
    },
    destroy() {
      ymap.unobserve(observer);
    },
  };
}

export function useYText(ytext) {
  const data = Vue.observable({ value: ytext.toString() });

  const observer = () => {
    data.value = ytext.toString();
  };

  ytext.observe(observer);

  return {
    data,
    set(newValue) {
      const doc = ytext.doc;
      if (!doc) return;

      doc.transact(() => {
        ytext.delete(0, ytext.length);
        if (newValue) {
          ytext.insert(0, newValue);
        }
      });
    },
    destroy() {
      ytext.unobserve(observer);
    },
  };
}

export function useYArray(yarray) {
  const data = Vue.observable([]);

  _syncArrayData(yarray, data);

  const observer = () => {
    _syncArrayData(yarray, data);
  };

  yarray.observe(observer);

  return {
    data,
    destroy() {
      yarray.unobserve(observer);
    },
  };
}

function _syncArrayData(yarray, target) {
  // Clear and rebuild — simpler than diffing for array changes
  target.splice(0, target.length);
  yarray.forEach((item) => {
    target.push(_unwrapYjsValue(item));
  });
}

function _unwrapYjsValue(value) {
  if (value == null) return value;

  // Check for Y.Text (has toString and insert methods)
  if (
    typeof value === 'object' &&
    typeof value.insert === 'function' &&
    typeof value.toString === 'function' &&
    value.doc !== undefined
  ) {
    return value.toString();
  }

  // Check for Y.Map (has entries method and _map property)
  if (
    typeof value === 'object' &&
    typeof value.entries === 'function' &&
    typeof value.set === 'function' &&
    value.doc !== undefined
  ) {
    const obj = {};
    value.forEach((v, k) => {
      obj[k] = _unwrapYjsValue(v);
    });
    return obj;
  }

  // Check for Y.Array (has toArray method)
  if (typeof value === 'object' && typeof value.toArray === 'function' && value.doc !== undefined) {
    return value.toArray().map(_unwrapYjsValue);
  }

  return value;
}

export { _unwrapYjsValue };
