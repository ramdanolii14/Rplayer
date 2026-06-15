// IDR Spectrum — main.js (Electron main process)
'use strict'

const { app, BrowserWindow, ipcMain, dialog } = require('electron')
const path = require('path')
const fs   = require('fs')

let mainWindow

function createWindow () {
  mainWindow = new BrowserWindow({
    width:     1300,
    height:    800,
    minWidth:  960,
    minHeight: 600,
    frame:     false,                       // custom titlebar
    backgroundColor: '#0d0d0d',
    webPreferences: {
      preload:          path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration:  false,
      webSecurity:      false               // allow file:// audio + cross-origin cover APIs
    }
  })

  mainWindow.loadFile('index.html')

  mainWindow.on('maximize',   () => mainWindow.webContents.send('win-state', 'maximized'))
  mainWindow.on('unmaximize', () => mainWindow.webContents.send('win-state', 'normal'))
  mainWindow.on('enter-full-screen', () => mainWindow.webContents.send('win-state', 'fullscreen'))
  mainWindow.on('leave-full-screen', () => mainWindow.webContents.send('win-state', 'normal'))
}

app.whenReady().then(createWindow)
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit() })
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow() })

// ─── Window controls ───────────────────────────────────────────────────────
ipcMain.on('win-minimize', () => mainWindow.minimize())
ipcMain.on('win-maximize', () => mainWindow.isMaximized() ? mainWindow.unmaximize() : mainWindow.maximize())
ipcMain.on('win-close',    () => mainWindow.close())

// ─── Open folder dialog ────────────────────────────────────────────────────
ipcMain.handle('open-folder', async () => {
  const { canceled, filePaths } = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    title: 'Pilih Folder Musik — IDR Spectrum'
  })
  return canceled ? null : filePaths[0]
})

// ─── Scan folder for audio files ───────────────────────────────────────────
ipcMain.handle('get-music-files', async (_e, folderPath) => {
  const AUDIO_EXT = new Set(['.mp3','.flac','.wav','.ogg','.m4a','.aac','.opus','.wma','.alac','.ape'])
  const files = []

  function scan (dir) {
    let entries
    try { entries = fs.readdirSync(dir, { withFileTypes: true }) }
    catch { return }

    for (const e of entries) {
      const full = path.join(dir, e.name)
      if (e.isDirectory()) {
        scan(full)
      } else if (AUDIO_EXT.has(path.extname(e.name).toLowerCase())) {
        files.push({
          path:     full,
          name:     e.name,
          basename: path.basename(e.name, path.extname(e.name)),
          ext:      path.extname(e.name).toLowerCase()
        })
      }
    }
  }

  scan(folderPath)
  return files.sort((a, b) => a.name.localeCompare(b.name, 'id'))
})

// ─── Parse audio metadata ──────────────────────────────────────────────────
ipcMain.handle('get-metadata', async (_e, filePath) => {
  try {
    // music-metadata v10+ is ESM-only — use dynamic import
    const mm = await import('music-metadata')
    const { common, format } = await mm.parseFile(filePath, { duration: true })

    // Embedded cover → base64 data-URL
    let cover = null
    if (common.picture?.length) {
      const pic    = common.picture[0]
      const b64    = Buffer.from(pic.data).toString('base64')
      const mime   = pic.format?.startsWith('image/') ? pic.format : `image/${pic.format || 'jpeg'}`
      cover        = `data:${mime};base64,${b64}`
    }

    return {
      title:      common.title      || path.basename(filePath, path.extname(filePath)),
      artist:     common.artist     || common.albumartist || 'Unknown Artist',
      album:      common.album      || 'Unknown Album',
      year:       common.year       || null,
      genre:      common.genre?.[0] || null,
      duration:   format.duration   || 0,
      sampleRate: format.sampleRate || null,
      bitrate:    format.bitrate    ? Math.round(format.bitrate / 1000) : null,
      codec:      format.codec      || null,
      cover
    }
  } catch {
    return {
      title:    path.basename(filePath, path.extname(filePath)),
      artist:   'Unknown Artist',
      album:    'Unknown Album',
      duration: 0,
      cover:    null
    }
  }
})
