#!/usr/bin/env python
"""xrandr dmenu script.

Add dmenu formatting options and default terminal if desired to
~/.config/xrandr-dmenu/config.ini

"""
import itertools
import locale
import os
import shlex
import sys
import re
from os.path import expanduser
from subprocess import Popen, PIPE
try:
    import configparser as configparser
except ImportError:
    import ConfigParser as configparser

ENV = os.environ.copy()
ENV['LC_ALL'] = 'C'
ENC = locale.getpreferredencoding()

def dmenu_cmd(num_lines, prompt="Displays"):
    """Parse config.ini if it exists and add options to the dmenu command

    Args: args - num_lines: number of lines to display
                 prompt: prompt to show
    Returns: command invocation (as a list of strings) for
                dmenu -l <num_lines> -p <prompt> -i ...

    """
    dmenu_command = "dmenu"
    conf = configparser.ConfigParser()
    conf.read(expanduser("~/.config/xrandr-dmenu/config.ini"))
    try:
        args = conf.items('dmenu')
    except configparser.NoSectionError:
        conf = False
    if not conf:
        res = [dmenu_command, "-i", "-l", str(num_lines), "-p", str(prompt)]
    else:
        args_dict = dict(args)
        dmenu_args = []
        if "dmenu_command" in args_dict:
            command = shlex.split(args_dict["dmenu_command"])
            dmenu_command = command[0]
            dmenu_args = command[1:]
            del args_dict["dmenu_command"]
        if "p" in args_dict and prompt == "Displays":
            prompt = args_dict["p"]
            del args_dict["p"]
        elif "p" in args_dict:
            del args_dict["p"]
        if "rofi" in dmenu_command:
            lines = "-i -dmenu -lines"
        else:
            lines = "-i -l"
        if "pinentry" in args_dict:
            del args_dict["pinentry"]
        extras = (["-" + str(k), str(v)] for (k, v) in args_dict.items())
        res = [dmenu_command, str(num_lines), "-p", str(prompt)]
        res.extend(dmenu_args)
        res += list(itertools.chain.from_iterable(extras))
        res[1:1] = lines.split()
    return res

class display(object):
    """
    """
    def __init__(self, name):
        self.name = name
        self.connected = None
        self.active = None
        self.resolution = None
        self.resolutions = []
        self.position = None
        __ordered_dict__
        self.positions_cmd = {"Same": "--same-as",
                              "Left of": "--left-of",
                              "Right of": "--right-of",
                              "Below": "--below",
                              "Above": "--above"}
        self.positions = self.positions_cmd.keys()
        self.init_values()

    def init_values(self):
        # get data
        conns = ["xrandr", "--query"]
        res = Popen(conns, stdout=PIPE).communicate()[0].decode(ENC)
        displs = []
        regex = r"\n{} ([^\s]+) (\d+x\d+)?(\+\d+\+\d+)?.*".format(self.name)
        match = re.search(regex, res)
        state, resolution, position = match.groups()
        # store
        if state == "connected":
            self.connected = True
        else:
            self.connected = False
        if resolution is None:
            self.active = False
        else:
            self.active = True
        self.resolution = resolution
        self.resolutions.append(resolution)

    def dmenu_repr(self):
        text = self.name
        if self.active:
            text += "*\t{} {}".format(self.resolution, self.position)
        return text

    def check_repr(self, repr):
        return repr[0:len(self.name)] == self.name

    def change_resolution(self, new_resolution):
        if new_resolution not in self.resolutions:
            raise Exception()
        args = ['xrandr', '--output', self.name, '--mode', new_resolution]
        res = Popen(args, stdout=PIPE).communicate()[0].decode(ENC).split('\n')

    def activate(self, position=None, active_displ=None):
        """
        """
        if self.active:
            raise Exception()
        #
        args = ['xrandr', '--output', self.name, '--auto']
        if position is self.positions and active_displ is not None:
            args += [self.positions_cmd[position], '{}'.format(active_displ.name)]
        res = Popen(args, stdout=PIPE).communicate()[0].decode(ENC).split('\n')
        self.active = True

    def deactivate(self):
        """
        """
        if not self.active:
            raise Exception("{} already active".format(self.name))
        #
        args = ['xrandr', '--output', self.name, '--off']
        res = Popen(args, stdout=PIPE).communicate()[0].decode(ENC).split('\n')
        self.active = False

    def get_options(self):
        opts = []
        if not self.connected:
            raise Exception()
        if self.active:
            opts += ["Deactivate"]
        else:
            opts += self.positions
        return opts

    def execute_option(self, opt):
        if opt == "Deactivate":
            self.deactivate()
        elif opt in self.positions:
            self.activate(opt)

def get_displays():
    """
    """
    # get dispays names
    conns = ["xrandr", "--query"]
    res = Popen(conns, stdout=PIPE).communicate()[0].decode(ENC)
    regex = r"\n([^\s]*) (connected|disconnected).*"
    names = [res[0] for res in re.findall(regex, res)]
    # create display object
    displs = [display(name) for name in names]
    return displs

def get_selection(prompt, inputs):
    """Combine the arg lists and send to dmenu for selection.
    """
    inputs_bytes = "\n".join(inputs).encode(ENC)
    sel = Popen(dmenu_cmd(len(inputs), prompt),
                stdin=PIPE,
                stdout=PIPE).communicate(input=inputs_bytes)[0].decode(ENC)
    if not sel.rstrip():
        sys.exit()
    return sel.rstrip()

def run():
    # Get display
    displs = get_displays()
    connected_displs = [displ for displ in displs if displ.connected]
    active_displs = [displ for displ in displs if displ.active]
    connected_displs_repr = [d.dmenu_repr() for d in connected_displs]
    sel = get_selection("Displays : ", connected_displs_repr)
    displ = [d for d in displs if d.check_repr(sel)][0]
    # get action on deisplay
    opts = displ.get_options()
    if len(opts) == 1:
        opt = opts[0]
    else:
        opt = get_selection("{} : ".format(displ.name), opts)
    # execute action
    if opt in displ.positions:
        displ.activate(position=opt, active_displ=active_displs[0])
    elif opt == "Deactivate":
        if len(active_displs) == 1:
            print("You don't want to deactivate the last display...")
            return 0
        displ.deactivate()


if __name__ == '__main__':
    run()
