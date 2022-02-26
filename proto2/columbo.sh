#!/usr/bin/bash
#   ~~~ ~~~ ~~~ ~~~ ~~~ ~~~ D E P R E C A T E D ~~~ ~~~ ~~~  ~~~ ~~~ ~~~
# ------------------------------------------------------------------------------
# es7s/columbo [hexdump wrapper]
# (C) 2021-2022 A. Shavykin <0.delameter@gmail.com>
# ------------------------------------------------------------------------------
cd "$(dirname "$(readlink -f "$0")")" || exit 127
# shellcheck source=../core/_commons.sh
[[ -z "$ES7S_COMMONS_LOADED" ]] && [[ -f "$ES7S_COMMONS_PATH" ]]  && source  "$ES7S_COMMONS_PATH"
[[ -z "$ES7S_COMMONS_LOADED" ]] && [[ -f "../core/_commons.sh" ]] && source "../core/_commons.sh"
[[ -z "$ES7S_COMMONS_LOADED" ]] && printf "%s\n" "ERROR: es7s/commons internal library not found" \
                                   "Reinstall es7s or provider valid path in \$ES7S_COMMONS_PATH" && exit 88
# ------------------------------------------------------------------------------
# echo "   ______      __                __"
# echo "  / ____/___  / /_  ______ ___  / /_  ____"
# echo " / /   / __ \/ / / / / __ '__ \/ __ \/ __ \ "
# echo "/ /___/ /_/ / / /_/ / / / / / / /_/ / /_/ /"
# echo "\____/\____/_/\__,_/_/ /_/ /_/_.___/\____/"

_main() {
    INPUT_RAW="$(_hexdump)"
    _header
    _preprocess | _postprocess
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
_header() { _table_line '' '┬' '┬' ; }
_footer() { _table_line '' '┴' '┴' ; }
_dupline() { _table_line '-' '│' '│' ; }

_preprocess() {
    #tr -s "[:space:]" <<< "$INPUT_RAW" #| sed -z '$ s/\n$//'
    #cat <<< "$INPUT_RAW"
    sed -Ee "s/^(\s*).+/\1:/" <<< "$INPUT_RAW" | tr " " "@"
}
_postprocess() {
    cat
   : # sed -E -e "s/\t/│/g" \
     #      -e "s/^\*$/$(_dupline)/"
}
_hexdump() {
    # shellcheck disable=SC2086
    hexdump -e '1 "'"$ADDR_PAD"'%'$ADDR_WIDTH'_ad'"$ADDR_PAD"'" "\t'"$HEX_PAD_LEFT"'"' \
            -e '16/1 "%03.2x" "'"$HEX_PAD_RIGHT"'\t'"$PRINT_PAD"'"' \
            -e '16/1 "%_p" "'"$PRINT_PAD"'\n"' \
            -e '1 "'"$(_s $((ADDR_WIDTH + ${#ADDR_PAD}*2)))"'\t'"$HEX_PAD_LEFT"'"' \
            -e '16/1 "%03.3_u" "'"$HEX_PAD_RIGHT"'\t\n"'
}
# ------------------------------------------------------------------------------
declare SELF="${0##*/}"
declare INPUT_RAW MAX_ADDR ADDR_CHARS
declare -a INPUT_ARR

declare ADDR_WIDTH HEX_WIDTH PRINT_WIDTH
declare ADDR_PAD HEX_PAD_LEFT HEX_PAD_RIGHT PRINT_PAD

# ------------------------------------------------------------------------------
#read -d "\0" -r INPUT_RAW
#MAX_ADDR=$(wc -c <<< "$INPUT_RAW")
#ADDR_CHARS=1 #${#MAX_ADDR}

ADDR_PAD=' '
HEX_PAD_LEFT=''
HEX_PAD_RIGHT=' '
PRINT_PAD=' '
ADDR_WIDTH=12
HEX_WIDTH=48
PRINT_WIDTH=16

_main
