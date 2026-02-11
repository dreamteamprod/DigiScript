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

/**
 * Create a reactive object bound to a Y.Map.
 *
 * Returns a plain reactive object whose properties mirror the Y.Map.
 * Remote changes update the reactive object automatically.
 *
 * @param {import('yjs').Map} ymap - The Y.Map to bind
 * @param {string[]} [keys] - Specific keys to observe (default: all)
 * @returns {{ data: object, destroy: Function }}
 */
export function useYMap(ymap, keys = null) {
  const data = Vue.observable({});

  // Initialize from current state
  if (keys) {
    keys.forEach((key) => {
      Vue.set(data, key, ymap.get(key));
    });
  } else {
    ymap.forEach((value, key) => {
      Vue.set(data, key, _unwrapYjsValue(value));
    });
  }

  // Observe Y.Map changes
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
    /**
     * Set a value on the Y.Map (triggers sync to other clients).
     * @param {string} key
     * @param {*} value
     */
    set(key, value) {
      ymap.set(key, value);
    },
    /**
     * Stop observing the Y.Map. Call on component destroy.
     */
    destroy() {
      ymap.unobserve(observer);
    },
  };
}

/**
 * Create a reactive string bound to a Y.Text.
 *
 * Returns a reactive object with a `value` property that mirrors the Y.Text.
 * Remote changes update the reactive value automatically.
 *
 * @param {import('yjs').Text} ytext - The Y.Text to bind
 * @returns {{ data: { value: string }, set: Function, destroy: Function }}
 */
export function useYText(ytext) {
  const data = Vue.observable({ value: ytext.toString() });

  const observer = () => {
    data.value = ytext.toString();
  };

  ytext.observe(observer);

  return {
    data,
    /**
     * Replace the entire text content.
     * @param {string} newValue
     */
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

/**
 * Create a reactive array bound to a Y.Array.
 *
 * Returns a reactive array that mirrors the Y.Array contents.
 * Each element is unwrapped: Y.Map → plain object, Y.Text → string.
 *
 * @param {import('yjs').Array} yarray - The Y.Array to bind
 * @returns {{ data: Array, destroy: Function }}
 */
export function useYArray(yarray) {
  const data = Vue.observable([]);

  // Initialize from current state
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

/**
 * Sync Y.Array contents to a reactive array.
 * @param {import('yjs').Array} yarray
 * @param {Array} target
 */
function _syncArrayData(yarray, target) {
  // Clear and rebuild — simpler than diffing for array changes
  target.splice(0, target.length);
  yarray.forEach((item) => {
    target.push(_unwrapYjsValue(item));
  });
}

/**
 * Unwrap a Yjs shared type to a plain JS value.
 * Y.Map → plain object, Y.Text → string, Y.Array → array.
 * Primitive values pass through unchanged.
 *
 * @param {*} value
 * @returns {*}
 */
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
