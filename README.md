<div align="center">
   <img src="https://user-images.githubusercontent.com/50381946/235438786-588f0045-dd2a-47e0-8da2-3215ec5b6202.png" width="96" height="96"><br>
   <img src="https://user-images.githubusercontent.com/50381946/219900506-491a3fc0-2e84-4782-ae3d-da4ae9825664.png" width="400" height="64">
</div>

<div align="center">
  <img src="https://img.shields.io/badge/python-3.7-3776AB?logo=python&logoColor=white&labelColor=333333">
  <a href="https://pypi.org/project/kolombos/"><img alt="PyPI" src="https://img.shields.io/pypi/v/kolombos"></a>
  <a href="https://pepy.tech/project/kolombos/">
    <img alt="Downloads" src="https://pepy.tech/badge/kolombos">
  </a>
</div>
<h1> </h1>


CLI application for visualising usually invisible characters and bytes:

- whitespace characters;
- ASCII control characters;
- ANSI escape sequences;
- UTF-8 encoded characters;
- binary data.

## Installation

### Via `pipx`

    pipx install kolombos

### Without `pipx`

#### System-wide install (`sudo`)

    python -m pip install kolombos

#### User install (no `sudo`)

    python -m pip install --user kolombos
    export PATH="${PATH}:${HOME}/.local/bin/"

## Usage

Application can be useful for a variety of tasks, e.g. browsing unknown data formats, searching for patterns or debugging combinations of SGR sequences.

```
USAGE                                                                                                                                                   
  kolombos [[--text] | --binary] [<options>] [--demo | <file>]     
  
INPUT
  <file>                  file to read from; if empty or "-", read stdin
                          instead; ignored if --demo is present
  -M, --demo              show output examples and exit; see --legend for the
                          description
OPERATING MODE
  -t, --text              open file in text mode [this is a default]
  -b, --binary            open file in binary mode
  -l, --legend            show annotation symbol list and exit
  -v, --version           show app version and exit
  -h, --help              show this help message and exit 

[...]
```

### Text mode and binary mode

`kolombos` can work in two primary modes: text and binary. The differences between them are line-by-line input reading in text mode vs. fixed size byte chunk reading in binary mode, and extended output in binary mode, which consists of text representation (similar to text mode) and hexademical byte values.

<p align="center"><img src="https://user-images.githubusercontent.com/50381946/211690178-d71a1e97-e9e5-43e9-a77d-500fc2740855.png"></p>

As you can see, some of the settings are shared between both modes, while the others are unique for one or another.

```
GENERIC OPTIONS
  -f, --buffer <size>     read buffer size, in bytes [default: 4096]
  -L, --max-lines <num>   stop after reading <num> lines [default: no limit]
  -B, --max-bytes <num>   stop after reading <num> bytes [default: no limit]
  -D, --debug             enable debug mode; can be used from 1 to 4 times,
                          each level increases verbosity (-D|DD|DDD|DDDD)
  --color-markers         apply SGR marker format to themselves

TEXT MODE OPTIONS
  -m, --marker <details>  marker details: 0 is none, 1 is brief, 2 is full
                          [default: 0]
  --no-separators         do not print ⢸separators⡇ around escape sequences
  --no-line-numbers       do not print line numbers

BINARY MODE OPTIONS
  -w, --columns <num>     format output as <num>-columns wide table [default: auto]
  -d, --decode            decode valid UTF-8 sequences, print as unicode chars
  --decimal-offsets       output offsets in decimal format [default: hex format]
  --no-offsets            do not print offsets

[...]
```

### Character classes

There are 6 different _character classes_, and each of those can be displayed normally, highlighted (or _focused_) or ignored.

| output | character class | byte ranges | focus flag | ignore flag | examples | 
| :---: | :------------- | :---: | :---: | :---: | :--- |
| ![cc1](https://user-images.githubusercontent.com/50381946/211689929-14e93463-d5a6-4003-9f9c-4663a1d147b2.png) | **whitespace** | `09-0d`<br>`20` | <code><b>-s</b></code> | <code><b>-S</b></code> | space, line feed, carriage return | 
| ![cc2](https://user-images.githubusercontent.com/50381946/211689948-81656bec-04ca-4575-aa8f-45d633d2a73b.png) | **control char** | `01-08`<br>`0e-1f` | <code><b>-c</b></code> | <code><b>-C</b></code> | null byte, backspace, delete |
| ![cc3](https://user-images.githubusercontent.com/50381946/211690013-92d8e952-8ef8-4cdc-9365-1e3e8dd436fa.png) | **printable char** | `21-7e` | <code><b>-p</b></code> | <code><b>-P</b></code> | ASCII alphanumeric and punctuation characters: A-Z, a-z, 0-9, (), [] | 
| ![cc4](https://user-images.githubusercontent.com/50381946/211690015-a0f7b3b1-c773-4d3c-963d-a35c643670a7.png) | **escape sequence** | `1b[..]` | <code><b>-e</b></code> | <code><b>-E</b></code> | ANSI escape sequences controlling cursor position, color, font styling, and other terminal options | 
| ![cc5](https://user-images.githubusercontent.com/50381946/211690016-e47ef065-c0d7-4647-989a-af5188d00ef6.png) | **UTF-8 sequence** | _various_ | <code><b>-u</b></code> | <code><b>-U</b></code> | valid UTF-8 byte sequences that can be decoded into Unicode characters |
| ![cc6](https://user-images.githubusercontent.com/50381946/211690017-4bfa43d7-f978-4267-a21a-005e40ce858d.png) | **binary data** | `80-ff` | <code><b>-i</b></code> | <code><b>-I</b></code> | standalone non-(7 bit)-ASCII bytes |

## Examples

### Control and whitespace characters

Let's take a look at one of the files from somebody's home directory &mdash; `.psql_history`. At the first sight it's a regular text file:

<p align="center"><img src="https://user-images.githubusercontent.com/50381946/211690258-2cd1c2ce-f254-4988-84e9-3f2584d607b4.png"></p>

But what if we look a bit more deeper into it?

<p align="center"><img src="https://user-images.githubusercontent.com/50381946/211690261-2897e4cd-1b24-4407-a11f-b5398b69088f.png"></p>

`kolombos` shows us hidden until now characters &mdash; not only spaces and line breaks, but even more: some control characters, namely `01` **START OF HEADING** ASCII bytes, which `postgresql` uses to store multiline queries.

Red symbol is an example of _marker_ &mdash; special sigil that indicates invisibile character in the input. Sigils were selected with a focus on dissimilarity and noticeability, which helps to detect them as soon as possible. Control char and escape sequence markers also provide some details about original input byte(s); there are three different levels of these details in text mode.

- Level 0 is no details, just the marker itself.
- Level 1 is medium details (this is a default) &mdash; one extra character for control chars and varying amount for escape sequences. For most of the control characters the second char corresponds to their caret notation, e.g. `ⱯA` should be read as **^A** <sup><a href="https://en.wikipedia.org/wiki/C0_and_C1_control_codes#SOH">[wiki]</a></sup>.
- Level 2 is maximuim amount of verbosity. For control chars it's their 2-digit hexademical value. Also note `-c` option in the last example below &mdash; which tells the application to highlight control characters and make them even more noticable.

<p align="center"><img src="https://user-images.githubusercontent.com/50381946/211690263-d10ecd0e-6390-4ecf-a2e2-e1f99d1893d6.png"></p>

Some of the control characters has unique sigils &mdash; for example, null byte (see [Legend](#legend)).

A few more examples of option combinations. First one is `--focus-space` flag, or `-s`, which can be useful for a situations where whitespaces are the points of interest, but input is a mess of different character classes.

Second example is a result of running the app with `--ignore-space` and `--ignore-printable` options; as you can see, now almost nothing is in the way of observing our precious control characters (if that's what you were after, that is):

<p align="center"><img src="https://user-images.githubusercontent.com/50381946/211690266-45a61611-4b65-45a2-bb5a-fcb95cede039.png"></p>


### ANSI escape sequecnces

Escape sequences and their overlapping combinations were the main reason for me to develop this application. For those who doesn't know much about them here's some comprehensive materials: [[one]](https://en.wikipedia.org/wiki/ANSI_escape_code) [[two]](https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797).

`kolombos` can distiguish a few types of escape sequences, but most interesting and frequent type is _SGR sequence_, which consists of escape control character `1b`, square bracket `[`, one or more digit params separated by `;` and `m` character (_terminator_). Let me illustrate.

SGR sequences are used for terminal text coloring and formatting. Consider this command with the following output:

<p align="center"><img src="https://user-images.githubusercontent.com/50381946/211690488-39dbb65f-98cb-4473-854f-6422b7005479.png"></p>

`kolombos` can show us what exactly is happening out there:

<p align="center"><img src="https://user-images.githubusercontent.com/50381946/211690491-e9508abc-d2d3-48e1-8a30-d4a519f42d93.png"></p>

There are 3 different types of markers in the example above:

- `ǝ` is a sigil for regular SGR sequence (which for example sets the color of the following text to red);
- `θ` is a _reset_ SGR sequence (`ESC[0m`) which completely disables all previously set colors and effects;
- `Ͻ` is _CSI sequence_ (more common sequence class which includes SGRs) &mdash; they also begin with `ESC[`, but have different terminator characters; in general, they control cursor position.
- Other types are listed in [Legend](#legend) section.

For this example binary more would be more convenient.

<p align="center"><img src="https://user-images.githubusercontent.com/50381946/211690493-8fa5f092-3a02-4f83-85de-93c0d6c9d9b2.png"></p>

As a rule of a thumb, the only <u>underlined</u> bytes in `kolombo`'s output are the bytes that correspond to escape sequences' params, introducers or terminators (but not the `1b`|`ESC` character itself, though).

Now it's clear where and which sequences are located:

- `ǝ[35m` &mdash; SGR that sets text color to _magenta_;
- `Ͻ[K` &mdash; CSI that erases all characters from cursor to the end of the current line;
- `θ[m` &mdash; SGR that resets, or disables all formatting;
- `ǝ[01;91m` &mdash; SGR that sets text style to _bold_ and text color to _bright red_, etc.

There is an option of highlighting SGR sequences with their own colors: `--color-markers`, which is disabled by default. In this particular case, even more clear picture can be seen after launching the app with `-P` option (`--ignore-printable`):

<p align="center"><img src="https://user-images.githubusercontent.com/50381946/211690495-f12b6340-faf0-478b-b423-76e3c29f08c2.png"></p>

Also notice that in binary mode each byte of input corresponds strictly to one hex value and one text representation character. That means that option `-m` is always equal to 2 (maximum verbosity) and cannot be changed.


### UTF-8 and binary data

There is no limitation for input bytes range in `kolombos` text mode &mdash; binary data will be displayed with the replacement character -- `Ḇ`:

<p align="center"><img src="https://user-images.githubusercontent.com/50381946/211690642-a12558e2-c8c9-4571-84a7-ed6f808adef3.png"></p>

But it's better and faster to work with binary data in binary mode. Valid UTF-8 sequences and escape sequences can be seen even in completely random byte data:

<p align="center"><img alt="ss11" src="https://user-images.githubusercontent.com/50381946/211690667-5998f67d-0210-498c-b4ac-37f463d907d5.png"></p>

UTF-8 sequences in text mode are automatically decoded and displayed as Unicode characters. In binary mode for faster data processing they are displayed as boxes by default, but still can be decoded with `-d`|`--decode` option (note the same requirement as for escape sequence markers &mdash; hex value length must always correspond to text representation length):

<p align="center"><img alt="ss12" src="https://user-images.githubusercontent.com/50381946/211690706-e3068c34-749f-425b-b5b9-59c5f8ba3a13.png"></p>


## Legend

<p align="center"><img alt="ss13v3" src="https://user-images.githubusercontent.com/50381946/211690757-e76df8a2-f7f6-4845-b35d-d6032b0dedb7.png"></p>

Even more information can be seen after running `kolombos --legend`.


## Changelog


### v1.5.4
- FIX: reverted default column amount in `--demo` mode

### v1.5.3
- FIX: errors while processing SGR with subparams (e.g. `4:3;`)

### v1.5.2
- UPDATE: icon redraw

### v1.5.1
- FIX: packaging assets

### v1.5
- NEW: `--demo` mode

### v1.4.1
- Temporarily injected `pytermor` v2.1

### v1.4
- REFACTOR: base colors
- REFACTOR: extended legend 
- DOCS:  update README and screenshots 

### v1.3
- Swap -D and -d (debug/decode)
- Make '--marker 0' default (was 1)
- Update legend
- Upgrade `pytermor` to 2.1

### v1.2.1
- Minor update.

### v1.2
- Separators additional styling.
- Separators auto-hide from `-m0`.
- `--no-sep[arators]` launch option.
- `run` dev script for quick launch of repo versions.
- Updated output format of SGR color prefixes.
- SGR labels are now getting colored instead of marker details (if `-m0` is set).
- Updated legend.

### v1.1
- Additional separators around escape seqs (in text mode) for better readability.

### v1.0.2
- Added logos.
- Fixed pipy README images.

### v1.0.1
- First public version.
