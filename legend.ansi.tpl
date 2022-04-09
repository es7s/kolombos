%(fmt_logo11)    __         %(fmt_logo12)%(fmt_logo13)__                __%(fmt_r)
%(fmt_logo21)   / /%(fmt_logo22)__%(fmt_logo23)____  / /___  ____ ___  / /_  ____%(fmt_r)
%(fmt_logo31)  / //_/%(fmt_logo32) __ \/ / __ \%(fmt_logo33)/ __ '__ \/ __ \/ __ \%(fmt_r)
%(fmt_logo41) / ,< %(fmt_logo42)/ /_/ / / /_/ %(fmt_logo43)/ / / / / / /_/ / /_/ /%(fmt_r)
%(fmt_logo51)/_/|_|%(fmt_logo52)\____/_/\____%(fmt_logo53)/_/ /_/ /_/\.___/\____/%(fmt_r)
                                   %(fmt_ver1)v%(fmt_ver2)%(ver)%(fmt_r)

%(fmt_header)ESCAPE SEQUENCES%(fmt_r)
%(ex_esq_sgr_reset)SGR reset sequence
%(ex_esq_sgr)SGR sequence, subclass of CSI
%(ex_esq_csi)CSI escape sequence (excluding SGR)
%(ex_esq_nf)nF escape sequence (introducer char can be space)
%(ex_esq)other escape sequences (Fe, Fs, Fp)

%(fmt_header)WHITESPACE CHARS%(fmt_r)
%(ex_space)space
%(exf_space)space %(fmt_comment)(focused)%(fmt_r)
%(ex_lf)line feed
%(ex_cr)carriage return
%(ex_htab)horizontal tab
%(ex_vtab)vertical tab
%(ex_ff)form feed

%(fmt_header)CONTROL CHARACTERS%(fmt_r)
%(ex_backspace)backspace
%(ex_delete)delete
%(ex_ascii_control)other ASCII control chars (01-07, 0e-1f)
%(ex_null)null byte
%(fmt_footer)[chr output  input]%(fmt_r)

%(fmt_header)HEX OUTPUT FORMATS%(fmt_r) (binary mode):
%(ex_bin_ascii_control)01 08 1f%(fmt_r)            ASCII controls (01-08, 0e-1f)
%(ex_bin_ascii_space)20 0a 09%(fmt_r)            ASCII whitespaces (09-0d, 20) (last one is focused)
%(ex_bin_ascii_print)57 54 46%(fmt_r)            ASCII printables (21-7e)
%(ex_bin_utf8_control)80 90 a0 ff%(fmt_r)         UTF-8 controls (80-ff), raw
%(ex_bin_utf8_print)e2 94 80%(fmt_r)            valid UTF-8 character sequence (bytes>1)
%(ex_bin_esq_sgr)1b 5b 34 6d%(fmt_r)         SGR sequence
%(ex_bin_esq_csi)xx xx xx xx%(fmt_r)         CSI sequence
