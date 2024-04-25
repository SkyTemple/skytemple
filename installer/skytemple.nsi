!include LogicLib.nsh

!define PRODUCT_NAME "SkyTemple"

!define FILES_SOURCE_PATH "dist\skytemple"
!define APPEXE "skytemple.exe"
!define PRODUCT_ICON "skytemple.ico"

SetCompressor lzma

RequestExecutionLevel admin

; Modern UI
!include "MUI2.nsh"
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"

; UI pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "license.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "French"
!insertmacro MUI_LANGUAGE "German"
!insertmacro MUI_LANGUAGE "Spanish"
!insertmacro MUI_LANGUAGE "Japanese"
; Modern UI end

Name "${PRODUCT_NAME} - ${PRODUCT_VERSION}"
Icon "skytemple.ico"
OutFile "skytemple-${PRODUCT_VERSION}-x64-install.exe"
InstallDir "$PROGRAMFILES64\${PRODUCT_NAME}"
ShowInstDetails show

Function UninstallPrevious
    ; Check for uninstaller.
    ReadRegStr $R0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "UninstallString"

    ${If} $R0 == ""
        Goto Done
    ${EndIf}

    DetailPrint "Removing previous installation."

    ; Run the uninstaller silently.
    ExecShellWait "open" "$R0" "/S" SW_HIDE
    ; FIXME: For some reason the ExecShellWait above sometimes doesn't wait enough!
    Sleep 10000

    Done:
FunctionEnd

Section "" SecUninstallPrevious

    Call UninstallPrevious

SectionEnd

Section "install"
  DetailPrint "Installing."
  ; the payload of this installer is described in an externally generated list of files
  !include  ${INST_LIST}
  SetOutPath "$INSTDIR\."
  File ${PRODUCT_ICON}

  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}.lnk" "$INSTDIR\${APPEXE}" "" "$INSTDIR\${PRODUCT_ICON}"
  WriteUninstaller $INSTDIR\uninstall.exe
  ; Add ourselves to Add/remove programs
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "DisplayIcon" "$INSTDIR\${PRODUCT_ICON}"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "NoRepair" 1
SectionEnd

;--------------------------------
; Uninstaller
;--------------------------------
Section "Uninstall"
  Delete "$INSTDIR\${PRODUCT_ICON}"
  Delete "$SMPROGRAMS\${PRODUCT_NAME}.lnk"

  Delete $INSTDIR\uninstall.exe

  ; Remove the files (using externally generated file list)
  !include ${UNINST_LIST}

  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
SectionEnd
