#!/usr/bin/env bash
# Launch the emulated energy node. Patches g_epoch_seed (in flash, after the
# ELF is loaded) with the current unix time so telemetry carries real
# timestamps — the emulation harness stands in for SNTP.
# Usage: ./run.sh [--headless]
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ELF="$DIR/../node-f429zi/Debug/node-f429zi.elf"
NM=$(command -v arm-none-eabi-nm || echo /opt/st/stm32cubeide_*/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.*/tools/bin/arm-none-eabi-nm)
NM=$(ls $NM 2>/dev/null | head -1)

ADDR=0x$($NM "$ELF" | awk '$3 == "g_epoch_seed" {print $1}')
[ "$ADDR" != "0x" ] || { echo "g_epoch_seed not found in $ELF"; exit 1; }

EXTRA=()
[ "${1:-}" = "--headless" ] && EXTRA=(--disable-gui --console)

exec renode "${EXTRA[@]}" -e "\$elf=@$ELF; include @$DIR/nucleo_f429zi.resc; sysbus WriteDoubleWord $ADDR $(date +%s); start"
