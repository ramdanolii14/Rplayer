; ============================================================
;  IDR Spectrum Player — NSIS Installer Script
;  Requires: NSIS 3.x + nsProcess plugin
;  Output: IDRSpectrum-Setup-${APP_VERSION}.exe
; ============================================================

Unicode True

; ── Defined via makensis /DAPP_VERSION=x.y.z ─────────────────────────────────
!ifndef APP_VERSION
  !define APP_VERSION "1.1.0"
!endif

!define APP_NAME        "IDR Spectrum Player"
!define APP_PUBLISHER   "Ramdan Olii"
!define APP_EXE         "IDRSpectrum.exe"
!define APP_ID          "IDRSpectrumPlayer"
!define INSTALL_DIR     "$PROGRAMFILES64\IDRSpectrum"
!define UNINST_KEY      "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}"
!define DIST_DIR        "..\dist\IDRSpectrum"

; ── NSIS settings ─────────────────────────────────────────────────────────────
Name                "${APP_NAME} ${APP_VERSION}"
OutFile             "..\IDRSpectrum-Setup-${APP_VERSION}.exe"
InstallDir          "${INSTALL_DIR}"
InstallDirRegKey    HKLM "${UNINST_KEY}" "InstallLocation"
RequestExecutionLevel admin
SetCompressor       /SOLID lzma
SetCompressorDictSize 64

; Modern UI
!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "WinVer.nsh"

; ── MUI Pages ─────────────────────────────────────────────────────────────────
!define MUI_ABORTWARNING
!define MUI_ICON    "..\assets\idr_spectrum.ico"
!define MUI_UNICON  "..\assets\idr_spectrum.ico"

!define MUI_WELCOMEPAGE_TITLE   "Selamat datang di ${APP_NAME}"
!define MUI_WELCOMEPAGE_TEXT    "Installer ini akan memasang ${APP_NAME} ${APP_VERSION} di komputer Anda.$\r$\n$\r$\nMusic player dengan spektrum visualizer dan konverter kurs IDR.$\r$\n$\r$\nKlik Next untuk melanjutkan."

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE    "..\LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN          "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT     "Jalankan ${APP_NAME} sekarang"
!define MUI_FINISHPAGE_SHOWREADME   ""
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Indonesian"
!insertmacro MUI_LANGUAGE "English"

; ── Version info (Properties tab di Explorer) ─────────────────────────────────
VIProductVersion                "${APP_VERSION}.0"
VIAddVersionKey "ProductName"   "${APP_NAME}"
VIAddVersionKey "ProductVersion" "${APP_VERSION}"
VIAddVersionKey "CompanyName"   "${APP_PUBLISHER}"
VIAddVersionKey "FileDescription" "${APP_NAME} Installer"
VIAddVersionKey "FileVersion"   "${APP_VERSION}"
VIAddVersionKey "LegalCopyright" "© 2024 ${APP_PUBLISHER}"

; ── Install Section ───────────────────────────────────────────────────────────
Section "MainSection" SEC01
    SetOutPath "$INSTDIR"
    SetOverwrite on

    ; Copy semua file dari dist/IDRSpectrum
    File /r "${DIST_DIR}\*"

    ; ── Start Menu shortcut ───────────────────────────────────────────────────
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut  "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
                    "$INSTDIR\${APP_EXE}" \
                    "" \
                    "$INSTDIR\${APP_EXE}" 0 \
                    SW_SHOWNORMAL \
                    "" \
                    "${APP_NAME} — Music Player"
    CreateShortcut  "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" \
                    "$INSTDIR\Uninstall.exe"

    ; ── Desktop shortcut ──────────────────────────────────────────────────────
    CreateShortcut  "$DESKTOP\${APP_NAME}.lnk" \
                    "$INSTDIR\${APP_EXE}" \
                    "" \
                    "$INSTDIR\${APP_EXE}" 0

    ; ── Tulis Uninstaller ─────────────────────────────────────────────────────
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; ── Registry — Apps & Features (Settings > Apps) ─────────────────────────
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0

    WriteRegStr   HKLM "${UNINST_KEY}" "DisplayName"      "${APP_NAME}"
    WriteRegStr   HKLM "${UNINST_KEY}" "DisplayVersion"   "${APP_VERSION}"
    WriteRegStr   HKLM "${UNINST_KEY}" "Publisher"        "${APP_PUBLISHER}"
    WriteRegStr   HKLM "${UNINST_KEY}" "InstallLocation"  "$INSTDIR"
    WriteRegStr   HKLM "${UNINST_KEY}" "UninstallString"  '"$INSTDIR\Uninstall.exe"'
    WriteRegStr   HKLM "${UNINST_KEY}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
    WriteRegStr   HKLM "${UNINST_KEY}" "DisplayIcon"      "$INSTDIR\${APP_EXE}"
    WriteRegStr   HKLM "${UNINST_KEY}" "URLInfoAbout"     "https://github.com/ramdanolii14/Rplayer"
    WriteRegDWORD HKLM "${UNINST_KEY}" "NoModify"         1
    WriteRegDWORD HKLM "${UNINST_KEY}" "NoRepair"         1
    WriteRegDWORD HKLM "${UNINST_KEY}" "EstimatedSize"    "$0"

    ; ── File association: .mp3, .flac, .ogg, .wav, .m4a, .opus, .aac ─────────
    !macro AssocAudio EXT
        WriteRegStr HKCR ".${EXT}\OpenWithProgids" "${APP_ID}.audio" ""
        WriteRegStr HKCR "${APP_ID}.audio" "" "Audio File"
        WriteRegStr HKCR "${APP_ID}.audio\DefaultIcon" "" "$INSTDIR\${APP_EXE},0"
        WriteRegStr HKCR "${APP_ID}.audio\shell\open\command" "" '"$INSTDIR\${APP_EXE}" "%1"'
    !macroend

    !insertmacro AssocAudio "mp3"
    !insertmacro AssocAudio "flac"
    !insertmacro AssocAudio "ogg"
    !insertmacro AssocAudio "wav"
    !insertmacro AssocAudio "m4a"
    !insertmacro AssocAudio "opus"
    !insertmacro AssocAudio "aac"

    ; Notify Windows tentang perubahan file association
    System::Call 'shell32.dll::SHChangeNotify(i, i, i, i) v (0x08000000, 0, 0, 0)'

SectionEnd

; ── Uninstall Section ─────────────────────────────────────────────────────────
Section "Uninstall"
    ; Hapus file aplikasi
    RMDir /r "$INSTDIR"

    ; Hapus Start Menu
    RMDir /r "$SMPROGRAMS\${APP_NAME}"

    ; Hapus Desktop shortcut
    Delete "$DESKTOP\${APP_NAME}.lnk"

    ; Hapus registry uninstall key
    DeleteRegKey HKLM "${UNINST_KEY}"

    ; Hapus file association (hanya jika masih milik app ini)
    !macro UnassocAudio EXT
        DeleteRegValue HKCR ".${EXT}\OpenWithProgids" "${APP_ID}.audio"
    !macroend
    !insertmacro UnassocAudio "mp3"
    !insertmacro UnassocAudio "flac"
    !insertmacro UnassocAudio "ogg"
    !insertmacro UnassocAudio "wav"
    !insertmacro UnassocAudio "m4a"
    !insertmacro UnassocAudio "opus"
    !insertmacro UnassocAudio "aac"
    DeleteRegKey HKCR "${APP_ID}.audio"

    System::Call 'shell32.dll::SHChangeNotify(i, i, i, i) v (0x08000000, 0, 0, 0)'

    ; Hapus config user (opsional — tanya dulu)
    MessageBox MB_YESNO|MB_ICONQUESTION \
        "Hapus juga data/config aplikasi (playlist, preferensi)?$\r$\n$APPDATA\.config\idr-spectrum" \
        IDNO skip_userdata
        RMDir /r "$APPDATA\.config\idr-spectrum"
    skip_userdata:

SectionEnd
