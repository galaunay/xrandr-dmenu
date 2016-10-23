# Xrandr-dmenu

Script to manage displays through `xrandr`

## Features

- Activate and desactivate displays
- Change resolution of active displays

## License

MIT

## Credits

Heavily inspired from [nmcli-dmenu](https://github.com/firecat53/nmcli-dmenu).

## Requirements

1. Python 2.7+ or 3.2+
2. Xrandr
3. Dmenu. Basic support is included for [Rofi](https://davedavenport.github.io/rofi), but most Rofi configuration/theming should be done via Xresources.

## Installation

- Set your `dmenu_command` in config.ini if it's not `dmenu` (for example `dmenu_run` or `rofi`). The alternate command should still respect the -l, -p and -i flags.
- To customize dmenu appearance, copy config.ini.example to '~/.config/xrandr-dmenu/config.ini' and edit.
- Set default terminal (xterm, urxvtc, etc.) command in config.ini if desired.
- If using Rofi, you can try some of the command line options in 'config.ini' or set them using the `dmenu_command` setting, but I haven't tested most of them so I'd suggest configuring via .Xresources where possible.
- Copy script somewhere in $PATH

## Usage

- Run script or bind to keystroke combination
