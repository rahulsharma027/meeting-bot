/* Browser-local conversation snapshots. No credentials or provider calls. */
(() => {
  'use strict';
  let database;
  function open() {
    if (!database) database = new Promise((resolve, reject) => {
      if (!window.indexedDB) { reject(new Error('Browser storage is unavailable.')); return; }
      const request = indexedDB.open('transcriptlens-workspace', 1);
      request.onupgradeneeded = () => {
        const db = request.result;
        db.createObjectStore('turns', { keyPath: 'id' });
        db.createObjectStore('workspace', { keyPath: 'id' });
      };
      request.onsuccess = () => {
        request.result.onversionchange = () => request.result.close();
        resolve(request.result);
      };
      request.onerror = () => reject(request.error);
      request.onblocked = () => reject(new Error('Close other TranscriptLens windows to update storage.'));
    });
    return database;
  }
  async function write(action) {
    const db = await open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(['turns', 'workspace'], 'readwrite');
      tx.oncomplete = () => resolve();
      tx.onabort = () => reject(tx.error || new Error('Could not save the workspace.'));
      tx.onerror = () => {}; // The abort handler reports failures once.
      try { action(tx); } catch (error) { tx.abort(); reject(error); }
    });
  }
  window.TranscriptLensStore = {
    async load() {
      const db = await open();
      return new Promise((resolve, reject) => {
        const tx = db.transaction(['turns', 'workspace'], 'readonly');
        const turns = tx.objectStore('turns').getAll();
        const workspace = tx.objectStore('workspace').get('current');
        tx.oncomplete = () => resolve({ turns: turns.result, workspace: workspace.result || null });
        tx.onabort = () => reject(tx.error);
        tx.onerror = () => {};
      });
    },
    saveWorkspace(workspace) {
      return write(tx => tx.objectStore('workspace').put({ ...workspace, id: 'current' }));
    },
    saveTurn(turn, workspace) {
      return write(tx => {
        tx.objectStore('turns').put(turn);
        tx.objectStore('workspace').put({ ...workspace, id: 'current' });
      });
    },
    clear(workspace) {
      return write(tx => {
        tx.objectStore('turns').clear();
        tx.objectStore('workspace').put({ ...workspace, id: 'current' });
      });
    },
  };
})();
