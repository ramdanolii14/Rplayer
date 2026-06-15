// preload.js — contextBridge between renderer and main process
'use strict'
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('idrAPI', {
  // Window controls
  minimize:  () => ipcRenderer.send('win-minimize'),
  maximize:  () => ipcRenderer.send('win-maximize'),
  close:     () => ipcRenderer.send('win-close'),
  onWinState: (cb) => ipcRenderer.on('win-state', (_e, state) => cb(state)),

  // Music
  openFolder:    ()           => ipcRenderer.invoke('open-folder'),
  getMusicFiles: (folder)     => ipcRenderer.invoke('get-music-files', folder),
  getMetadata:   (filePath)   => ipcRenderer.invoke('get-metadata', filePath)
})
