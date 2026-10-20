#!/bin/sh
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb export step --no-board-body --component-filter "$1" --user-origin 0x0mm -f -o "comp/$1.step" board_abs.kicad_pcb >/dev/null 2>&1 || echo "FAIL $1"
