#!/usr/bin/bash
# ------------------------------------------------------------------------------
# es7s/columbo
# (C) 2021-2022 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
COMMONS_PATH="$HOME/.es7s/_common.sh"
# shellcheck source=../core/_common.sh
. "$COMMONS_PATH"
# ------------------------------------------------------------------------------
_main() {
    _header
    _preview
    _table_line '' '' '┬'
    _preprocess | _hexdump | _postprocess
    _footer
}

_table_line() {
    _s $(( ADDR_WIDTH + ${#ADDR_PAD}*2 )) "${1:-"─"}"
    _s 1 "${2:-"┼"}"
    _s $(( HEX_WIDTH + ${#HEX_PAD_LEFT} + ${#HEX_PAD_RIGHT} )) "${1:-"─"}"
    _s 1 "${3:-"┼"}"
    _s $(( PRINT_WIDTH + ${#PRINT_PAD}*2)) "${1:-"─"}"
    printn
}
_header() { _table_line '' '┬' '─' ; }
_footer() { _table_line '' '┴' '┴' ; }
_dupline() { _table_line '-' '│' '│' ; }

_preview() {
    # shellcheck disable=SC2086
    local preview="$( printf %s "$INPUT_RAW" | grep ^ -bT --binary-files=without-match 2>/dev/null )"
    if grep -Ee "Binary file \(standard input\) matches" <<< "$preview" >/dev/null ; then
        return 0
    fi
    cat <<< "$preview" | \
      sed -E -e "s/^\s*([0-9]+):(\t|$)/$(_s $ADDR_WIDTH)\1\t/" \
             -e "s/^.*(.{$ADDR_WIDTH})\t/$ADDR_PAD\1$ADDR_PAD│ /"
}
_preprocess() {
    tr -s "[:space:]" <<< "$INPUT_RAW"
}
_postprocess() {
    sed -E -e "s/\t/│/g" \
           -e "s/^\*$/$(_dupline)/"
}
_hexdump() {
    # shellcheck disable=SC2086
    hexdump -e '1 "'"$ADDR_PAD"'%'$ADDR_WIDTH'_ad'"$ADDR_PAD"'" "\t'"$HEX_PAD_LEFT"'"' \
            -e '16/1 "%03.2x" "'"$HEX_PAD_RIGHT"'\t'"$PRINT_PAD"'"' \
            -e '16/1 "%_p" "'"$PRINT_PAD"'\n"' \
            #-e '1 "'"$(_s $((ADDR_WIDTH + ${#ADDR_PAD}*2)))"'\t'"$HEX_PAD_LEFT"'"' \
            #-e '16/1 "%03.3_u" "'"$HEX_PAD_RIGHT"'\t\n"'
}
# ------------------------------------------------------------------------------
declare SELF="${0##*/}"

declare INPUT_RAW MAX_ADDR ADDR_CHARS
declare -a INPUT_ARR

declare ADDR_WIDTH HEX_WIDTH PRINT_WIDTH
declare ADDR_PAD HEX_PAD_LEFT HEX_PAD_RIGHT PRINT_PAD

# ------------------------------------------------------------------------------
mapfile -t INPUT_ARR
INPUT_RAW="$(_jb $'\n' "${INPUT_ARR[@]}")"
MAX_ADDR=$(wc -c <<< "$INPUT_RAW")
ADDR_CHARS=${#MAX_ADDR}

ADDR_PAD=' '
HEX_PAD_LEFT=''
HEX_PAD_RIGHT=' '
PRINT_PAD=' '
ADDR_WIDTH=$ADDR_CHARS
HEX_WIDTH=48
PRINT_WIDTH=16

_main
