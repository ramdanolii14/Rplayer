// ═══════════════════════════════════════════════════════════════════════
// IDR Spectrum — renderer.js
// Handles: playlist, audio, cover art (embedded → iTunes → MusicBrainz
//          → Deezer → Last.fm), IDR/USD chart, all controls & keyboard
// ═══════════════════════════════════════════════════════════════════════
'use strict'

// ─── State ───────────────────────────────────────────────────────────────
const S = {
  playlist:     [],       // [{path, name, basename, ext, meta}]
  idx:          -1,       // current track index
  playing:      false,
  shuffle:      false,
  repeat:       0,        // 0=off 1=all 2=one
  muted:        false,
  coverCache:   new Map(),
  metaCache:    new Map()
}

// ─── Audio engine ─────────────────────────────────────────────────────────
const audio = new Audio()
audio.volume = 0.8
audio.preload = 'auto'

// ─── DOM refs ─────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id)

const elPlaylist     = $('playlist')
const elEmpty        = $('emptyState')
const elTrackCount   = $('trackCount')
const elBtnPlay      = $('btnPlay')
const elPlayIcon     = $('playIcon')
const elBtnPrev      = $('btnPrev')
const elBtnNext      = $('btnNext')
const elBtnShuffle   = $('btnShuffle')
const elBtnRepeat    = $('btnRepeat')
const elBtnMute      = $('btnMute')
const elVolIcon      = $('volIcon')
const elVolSlider    = $('volSlider')
const elSeekbar      = $('seekbar')
const elSeekFill     = $('seekFill')
const elSeekThumb    = $('seekThumb')
const elTimeCur      = $('timeCur')
const elTimeTot      = $('timeTot')
const elPbTitle      = $('pbTitle')
const elPbArtist     = $('pbArtist')
const elPbMeta       = $('pbMeta')
const elCoverImg     = $('coverImg')
const elCoverPh      = $('coverPlaceholder')
const elCoverLoading = $('coverLoading')

// ═══════════════════════════════════════════════════════════════════════
// WINDOW CONTROLS
// ═══════════════════════════════════════════════════════════════════════
$('btnMin').onclick   = () => window.idrAPI.minimize()
$('btnMax').onclick   = () => window.idrAPI.maximize()
$('btnClose').onclick = () => window.idrAPI.close()

window.idrAPI.onWinState(state => {
  const btn = $('btnMax')
  btn.title = state === 'maximized' ? 'Restore' : 'Maximise'
})

// ═══════════════════════════════════════════════════════════════════════
// OPEN FOLDER
// ═══════════════════════════════════════════════════════════════════════
$('btnOpenFolder').onclick = async () => {
  const folder = await window.idrAPI.openFolder()
  if (!folder) return

  const files = await window.idrAPI.getMusicFiles(folder)
  if (!files.length) return

  // Reset state
  S.playlist   = files.map(f => ({ ...f, meta: null }))
  S.idx        = -1
  S.playing    = false
  S.coverCache.clear()

  audio.pause()
  audio.src = ''
  resetPlayerUI()
  renderPlaylist()

  // Load metadata in background (one by one to avoid hammering IPC)
  loadAllMeta(files)
}

async function loadAllMeta (files) {
  for (let i = 0; i < files.length; i++) {
    const meta = await window.idrAPI.getMetadata(files[i].path)
    S.playlist[i].meta = meta
    updatePlaylistRow(i)
  }
  elTrackCount.textContent = `${files.length} lagu`
}

// ═══════════════════════════════════════════════════════════════════════
// PLAYLIST RENDERING
// ═══════════════════════════════════════════════════════════════════════
function renderPlaylist () {
  elEmpty.style.display = 'none'
  elTrackCount.textContent = `${S.playlist.length} lagu`

  // Remove old items (keep emptyState node)
  const existing = elPlaylist.querySelectorAll('.pl-item')
  existing.forEach(el => el.remove())

  S.playlist.forEach((track, i) => {
    const el = document.createElement('div')
    el.className = 'pl-item'
    el.dataset.idx = i
    el.innerHTML = `
      <span class="pl-num">${i + 1}</span>
      <span class="pl-note">♪</span>
      <div class="pl-info">
        <div class="pl-title">${esc(track.meta?.title || track.basename)}</div>
        <div class="pl-artist">${esc(track.meta?.artist || '…')}</div>
      </div>
      <span class="pl-dur">${fmt(track.meta?.duration || 0)}</span>
    `
    el.addEventListener('dblclick', () => playTrack(i))
    el.addEventListener('click',    () => highlightRow(i))
    elPlaylist.appendChild(el)
  })
}

function updatePlaylistRow (i) {
  const el = elPlaylist.querySelector(`[data-idx="${i}"]`)
  if (!el) return
  const meta = S.playlist[i].meta
  if (!meta) return
  el.querySelector('.pl-title').textContent  = meta.title  || S.playlist[i].basename
  el.querySelector('.pl-artist').textContent = meta.artist || 'Unknown Artist'
  el.querySelector('.pl-dur').textContent    = fmt(meta.duration || 0)
}

function highlightRow (i) {
  elPlaylist.querySelectorAll('.pl-item').forEach((el, j) => {
    el.classList.toggle('active', j === i)
  })
}

function markPlaying (i) {
  elPlaylist.querySelectorAll('.pl-item').forEach((el, j) => {
    el.classList.toggle('active',  j === i)
    el.classList.toggle('playing', j === i)
    const note = el.querySelector('.pl-note')
    if (note) note.textContent = j === i ? '▶' : '♪'
  })

  // Scroll into view
  const row = elPlaylist.querySelector(`[data-idx="${i}"]`)
  if (row) row.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
}

// ═══════════════════════════════════════════════════════════════════════
// PLAYBACK
// ═══════════════════════════════════════════════════════════════════════
async function playTrack (i) {
  if (i < 0 || i >= S.playlist.length) return
  S.idx = i

  const track = S.playlist[i]

  // Ensure metadata exists
  if (!track.meta) {
    track.meta = await window.idrAPI.getMetadata(track.path)
    updatePlaylistRow(i)
  }

  // Set audio source — must encode spaces/special chars but not path separators
  const safeUrl = 'file://' + track.path.split('/').map(seg => encodeURIComponent(seg)).join('/')
  audio.src = safeUrl
  audio.play().catch(err => console.error('Audio play error:', err))

  S.playing = true
  markPlaying(i)
  updatePlayIcon()
  updatePlayerInfo(track.meta)
  await loadCoverArt(track.meta)
}

function updatePlayerInfo (meta) {
  elPbTitle.textContent  = meta.title  || 'Unknown'
  elPbArtist.textContent = meta.artist || 'Unknown Artist'

  const parts = []
  if (meta.bitrate)    parts.push(`${meta.bitrate} kbps`)
  if (meta.sampleRate) parts.push(`${(meta.sampleRate / 1000).toFixed(1)} kHz`)
  if (meta.codec)      parts.push(meta.codec.toUpperCase())
  elPbMeta.textContent = parts.join(' · ')
}

function resetPlayerUI () {
  elPbTitle.textContent  = 'Tidak ada lagu'
  elPbArtist.textContent = '—'
  elPbMeta.textContent   = ''
  elTimeCur.textContent  = '0:00'
  elTimeTot.textContent  = '0:00'
  elSeekFill.style.width = '0%'
  elSeekThumb.style.left = '0%'
  showPlaceholder()
  updatePlayIcon()
}

// ─── Audio events ──────────────────────────────────────────────────────
audio.addEventListener('play',  () => { S.playing = true;  updatePlayIcon() })
audio.addEventListener('pause', () => { S.playing = false; updatePlayIcon() })

audio.addEventListener('timeupdate', () => {
  if (!audio.duration || isNaN(audio.duration)) return
  const pct = (audio.currentTime / audio.duration) * 100
  elSeekFill.style.width = pct + '%'
  elSeekThumb.style.left = pct + '%'
  elTimeCur.textContent  = fmt(audio.currentTime)
})

audio.addEventListener('durationchange', () => {
  elTimeTot.textContent = fmt(audio.duration)
})

audio.addEventListener('ended', onTrackEnd)

audio.addEventListener('error', () => {
  console.error('Audio error for:', S.playlist[S.idx]?.path, audio.error?.message)
})

function onTrackEnd () {
  if (S.repeat === 2) {                          // repeat one
    audio.currentTime = 0
    audio.play()
    return
  }
  const next = nextIndex()
  if (next !== -1) playTrack(next)
  else { S.playing = false; updatePlayIcon() }
}

function nextIndex () {
  const n = S.playlist.length
  if (!n) return -1
  if (S.shuffle) return Math.floor(Math.random() * n)
  const i = S.idx + 1
  if (i < n) return i
  if (S.repeat === 1) return 0
  return -1
}

function prevIndex () {
  if (audio.currentTime > 3) return S.idx   // restart current
  const i = S.idx - 1
  if (i >= 0) return i
  if (S.repeat === 1) return S.playlist.length - 1
  return 0
}

// ─── Control buttons ───────────────────────────────────────────────────
elBtnPlay.addEventListener('click', () => {
  if (S.idx === -1 && S.playlist.length) { playTrack(0); return }
  audio.paused ? audio.play() : audio.pause()
})

elBtnPrev.addEventListener('click', () => {
  const i = prevIndex()
  if (i !== -1) {
    if (i === S.idx) { audio.currentTime = 0 }
    else playTrack(i)
  }
})

elBtnNext.addEventListener('click', () => {
  const i = nextIndex()
  if (i !== -1) playTrack(i)
})

elBtnShuffle.addEventListener('click', () => {
  S.shuffle = !S.shuffle
  elBtnShuffle.classList.toggle('on', S.shuffle)
})

elBtnRepeat.addEventListener('click', () => {
  S.repeat = (S.repeat + 1) % 3
  elBtnRepeat.classList.toggle('on', S.repeat > 0)

  // Swap icon: repeat-all vs repeat-one
  if (S.repeat === 2) {
    elBtnRepeat.innerHTML = `
      <svg viewBox="0 0 24 24" fill="currentColor" width="17" height="17">
        <path d="M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4z"/>
        <text x="10" y="15" font-size="6" font-weight="bold" fill="currentColor">1</text>
      </svg>`
  } else {
    elBtnRepeat.innerHTML = `
      <svg viewBox="0 0 24 24" fill="currentColor" width="17" height="17" id="repeatIcon">
        <path d="M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4z"/>
      </svg>`
  }
})

elBtnMute.addEventListener('click', () => {
  S.muted  = !S.muted
  audio.muted = S.muted
  elBtnMute.classList.toggle('on', S.muted)
  elVolIcon.innerHTML = S.muted
    ? `<path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3 3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4 9.91 6.09 12 8.18V4z"/>`
    : `<path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>`
})

elVolSlider.addEventListener('input', () => {
  audio.volume = elVolSlider.value / 100
  if (audio.volume > 0 && S.muted) {
    S.muted = false
    audio.muted = false
    elBtnMute.classList.remove('on')
  }
})

function updatePlayIcon () {
  elPlayIcon.innerHTML = S.playing
    ? `<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>`  // pause
    : `<path d="M8 5v14l11-7z"/>`                      // play
}

// ─── Seekbar ───────────────────────────────────────────────────────────
let seeking = false

elSeekbar.addEventListener('mousedown', e => {
  seeking = true
  doSeek(e)
})
document.addEventListener('mousemove', e => { if (seeking) doSeek(e) })
document.addEventListener('mouseup',   () => { seeking = false })

function doSeek (e) {
  if (!audio.duration) return
  const r   = elSeekbar.getBoundingClientRect()
  const pct = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width))
  audio.currentTime      = pct * audio.duration
  elSeekFill.style.width = (pct * 100) + '%'
  elSeekThumb.style.left = (pct * 100) + '%'
}

// ─── Keyboard shortcuts ────────────────────────────────────────────────
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT') return
  switch (e.code) {
    case 'Space':
      e.preventDefault()
      elBtnPlay.click()
      break
    case 'ArrowLeft':
      audio.currentTime = Math.max(0, audio.currentTime - 5)
      break
    case 'ArrowRight':
      audio.currentTime = Math.min(audio.duration || 0, audio.currentTime + 5)
      break
    case 'ArrowUp':
      e.preventDefault()
      elVolSlider.value = Math.min(100, +elVolSlider.value + 5)
      audio.volume = elVolSlider.value / 100
      break
    case 'ArrowDown':
      e.preventDefault()
      elVolSlider.value = Math.max(0, +elVolSlider.value - 5)
      audio.volume = elVolSlider.value / 100
      break
    case 'KeyS': elBtnShuffle.click(); break
    case 'KeyR': elBtnRepeat.click();  break
    case 'KeyM': elBtnMute.click();    break
    case 'Comma':  elBtnPrev.click();  break
    case 'Period': elBtnNext.click();  break
  }
})

// ═══════════════════════════════════════════════════════════════════════
// COVER ART — embedded → iTunes → MusicBrainz/CAA → Deezer → Last.fm
// ═══════════════════════════════════════════════════════════════════════
async function loadCoverArt (meta) {
  const key = `${meta.artist}__${meta.title}`.toLowerCase()

  // 1. Serve from cache
  if (S.coverCache.has(key)) {
    displayCover(S.coverCache.get(key))
    return
  }

  // 2. Embedded cover from metadata (base64 data-URL)
  if (meta.cover) {
    displayCover(meta.cover)
    S.coverCache.set(key, meta.cover)
    return
  }

  // 3. No embedded cover → fetch from internet
  showLoading()
  const url = await fetchCoverOnline(meta.title, meta.artist, meta.album)
  if (url) {
    displayCover(url)
    S.coverCache.set(key, url)
  } else {
    showPlaceholder()
  }
}

async function fetchCoverOnline (title, artist, album) {
  const clean = s => (s || '')
    .replace(/\([^)]*\)/g, '')
    .replace(/\[[^\]]*\]/g, '')
    .replace(/feat\./gi, '')
    .replace(/ft\./gi, '')
    .trim()

  const t = clean(title)
  const a = clean(artist)

  // ── Source 1: iTunes Search API (free, no key) ──────────────────────
  try {
    const q   = encodeURIComponent(`${a} ${t}`.trim())
    const res = await fetchWithTimeout(
      `https://itunes.apple.com/search?term=${q}&media=music&limit=5&country=id`,
      5000
    )
    if (res.ok) {
      const js = await res.json()
      if (js.results?.length) {
        const art = js.results[0].artworkUrl100
        if (art) return art
                          .replace('100x100bb', '600x600bb')
                          .replace('/100x100/', '/600x600/')
      }
    }
  } catch { /* next */ }

  // ── Source 2: MusicBrainz recording → CoverArtArchive ────────────────
  try {
    const q   = encodeURIComponent(`recording:"${t}" AND artist:"${a}"`)
    const res = await fetchWithTimeout(
      `https://musicbrainz.org/ws/2/recording/?query=${q}&limit=5&fmt=json`,
      6000,
      { 'User-Agent': 'IDRSpectrum/1.1 (ramdanolii1410@gmail.com)' }
    )
    if (res.ok) {
      const js = await res.json()
      const recordings = js.recordings || []
      for (const rec of recordings) {
        for (const rel of (rec.releases || [])) {
          if (!rel.id) continue
          const head = await fetchWithTimeout(
            `https://coverartarchive.org/release/${rel.id}/front`,
            3000,
            {},
            'HEAD'
          ).catch(() => null)
          if (head && (head.ok || head.status === 307)) {
            return `https://coverartarchive.org/release/${rel.id}/front`
          }
        }
      }
    }
  } catch { /* next */ }

  // ── Source 3: Deezer public search (no key needed) ───────────────────
  try {
    const q   = encodeURIComponent(`${a} ${t}`.trim())
    const res = await fetchWithTimeout(
      `https://api.deezer.com/search?q=${q}&limit=1`,
      5000
    )
    if (res.ok) {
      const js = await res.json()
      const cover = js.data?.[0]?.album?.cover_xl
                 || js.data?.[0]?.album?.cover_big
                 || js.data?.[0]?.album?.cover_medium
      if (cover) return cover
    }
  } catch { /* next */ }

  // ── Source 4: Last.fm (free API key bundled — public read-only) ───────
  // Using a public demo key: 7b76648e4aeacbbdb35c5f3d9f8b9af4
  try {
    const LFMK = '7b76648e4aeacbbdb35c5f3d9f8b9af4'
    const res  = await fetchWithTimeout(
      `https://ws.audioscrobbler.com/2.0/?method=track.getInfo&api_key=${LFMK}&artist=${encodeURIComponent(a)}&track=${encodeURIComponent(t)}&format=json`,
      5000
    )
    if (res.ok) {
      const js = await res.json()
      const imgs = js.track?.album?.image || []
      // Last.fm image sizes: small medium large extralarge mega
      const big = imgs.find(img => img.size === 'extralarge' || img.size === 'mega')
      if (big?.['#text']) return big['#text']
    }
  } catch { /* give up */ }

  // ── Source 5: album fallback via iTunes ──────────────────────────────
  if (album && album !== 'Unknown Album') {
    try {
      const q   = encodeURIComponent(`${a} ${clean(album)}`.trim())
      const res = await fetchWithTimeout(
        `https://itunes.apple.com/search?term=${q}&media=music&entity=album&limit=3`,
        5000
      )
      if (res.ok) {
        const js = await res.json()
        if (js.results?.length) {
          const art = js.results[0].artworkUrl100
          if (art) return art.replace('100x100bb', '600x600bb')
        }
      }
    } catch { /* give up */ }
  }

  return null
}

function fetchWithTimeout (url, ms, headers = {}, method = 'GET') {
  const ctrl = new AbortController()
  const tid  = setTimeout(() => ctrl.abort(), ms)
  return fetch(url, {
    method,
    headers,
    signal: ctrl.signal
  }).finally(() => clearTimeout(tid))
}

// ─── Cover display helpers ─────────────────────────────────────────────
function displayCover (src) {
  elCoverImg.onload = () => {
    elCoverPh.style.display      = 'none'
    elCoverLoading.classList.remove('visible')
    elCoverImg.style.display     = 'block'
    elCoverImg.classList.add('loaded')
  }
  elCoverImg.onerror = () => showPlaceholder()
  elCoverImg.src = src
}

function showLoading () {
  elCoverPh.style.display = 'none'
  elCoverImg.style.display = 'none'
  elCoverImg.classList.remove('loaded')
  elCoverLoading.classList.add('visible')
}

function showPlaceholder () {
  elCoverLoading.classList.remove('visible')
  elCoverImg.style.display = 'none'
  elCoverImg.classList.remove('loaded')
  elCoverPh.style.display = 'flex'
}

// ═══════════════════════════════════════════════════════════════════════
// IDR / USD CHART
// Historical mock data — IDR per 1 USD, 1990–2024
// Sumber: simulasi berdasarkan data publik Bank Indonesia / FRED
// ═══════════════════════════════════════════════════════════════════════
function buildChart () {
  const labels = [
    '1990','1991','1992','1993','1994','1995','1996',
    "Sep'97","Jan'98","Jun'98","Des'98",
    '2000','2001','2002','2003','2004','2005','2006','2007',
    '2008','2009','2010','2011','2012','2013',
    '2014','2015','2016','2017','2018','2019',
    '2020','2021','2022','2023','2024'
  ]

  // IDR per USD (end-of-period approximation)
  const idrValues = [
    1843,  1950,  2063,  2110,  2200,  2308,  2383,
    3748,  9700, 16650,  8025,
    9595, 10400,  9012,  8465,  8940,
    9830,  9159,  9419, 10950, 10356,
    8991,  9068,  9670, 10461,
   12440, 13795, 13436, 13548, 14481, 14244,
   14105, 14269, 15731, 15591, 16261
  ]

  // Flat mock target line at 18 000
  const target18k = labels.map(() => 18000)

  const ctx = $('idrChart').getContext('2d')

  // Gradient fill under the IDR line
  function makeGradient (chart) {
    const { ctx: c, chartArea } = chart
    if (!chartArea) return 'rgba(196,167,90,0)'
    const g = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
    g.addColorStop(0,   'rgba(196,167,90,0.35)')
    g.addColorStop(0.6, 'rgba(196,167,90,0.08)')
    g.addColorStop(1,   'rgba(196,167,90,0)')
    return g
  }

  // Mark crisis points in red
  const pointColors = idrValues.map((_, i) => {
    // Sep'97, Jan'98, Jun'98, Des'98 → indices 7-10
    return (i >= 7 && i <= 10) ? '#d95f5f' : '#c4a75a'
  })
  const pointSizes = idrValues.map((_, i) => (i >= 7 && i <= 10) ? 6 : 2.5)

  new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'IDR/USD',
          data: idrValues,
          borderColor: '#c4a75a',
          borderWidth: 2,
          backgroundColor: ctx => makeGradient(ctx.chart),
          fill: true,
          tension: 0.35,
          pointRadius: pointSizes,
          pointBackgroundColor: pointColors,
          pointBorderColor: 'transparent',
          pointHoverRadius: 6,
          pointHoverBackgroundColor: '#d9bf7a'
        },
        {
          label: 'Mock Rp 18.000',
          data: target18k,
          borderColor: 'rgba(217, 95, 95, 0.5)',
          borderWidth: 1.5,
          borderDash: [6, 5],
          pointRadius: 0,
          fill: false,
          tension: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 1800, easing: 'easeInOutQuart' },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1a1a1a',
          borderColor: '#2c2c2c',
          borderWidth: 1,
          titleColor: '#8a8070',
          bodyColor: '#f0ece4',
          titleFont: { size: 11 },
          bodyFont:  { size: 12, weight: 'bold' },
          padding: 10,
          callbacks: {
            title: items => items[0].label,
            label: item => {
              if (item.datasetIndex === 1)
                return '  Target mock: Rp 18.000'
              const val = item.parsed.y.toLocaleString('id-ID')
              const diff = item.parsed.y - 1843
              const pct  = ((diff / 1843) * 100).toFixed(0)
              return [
                `  Kurs: Rp ${val} / USD`,
                `  vs 1990: ${diff > 0 ? '+' : ''}${pct}%`
              ]
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(44,44,44,0.7)', drawBorder: false },
          ticks: {
            color: '#4a4540',
            font:  { size: 9.5 },
            maxRotation: 50,
            autoSkip: true,
            maxTicksLimit: 16
          }
        },
        y: {
          grid: { color: 'rgba(44,44,44,0.7)', drawBorder: false },
          ticks: {
            color: '#4a4540',
            font:  { size: 9.5 },
            callback: v => v >= 1000 ? `Rp ${(v/1000).toFixed(0)}K` : `Rp ${v}`
          },
          min: 0,
          max: 20000,
          suggestedMax: 20000
        }
      }
    }
  })
}

// ═══════════════════════════════════════════════════════════════════════
// UTILS
// ═══════════════════════════════════════════════════════════════════════
function fmt (sec) {
  if (!sec || isNaN(sec) || !isFinite(sec)) return '0:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function esc (s) {
  return String(s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

// ═══════════════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════════════
buildChart()
