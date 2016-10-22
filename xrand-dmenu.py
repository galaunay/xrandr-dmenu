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
from collections import OrderedDict
from subprocess import Popen, PIPE
try:
    import configparser as configparser
except ImportError:
    import ConfigParser as configparser

ENV = os.environ.copy()
ENV['LC_ALL'] = 'C'
ENC = locale.getpreferredencoding()

def dmenu_cmd(num_lines, prompt="Displays"):
    """
    Parse config.ini if it exists and add options to the dmenu command

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
        self.positions_cmd = OrderedDict()
        self.positions_cmd["Same as"] = "--same-as"
        self.positions_cmd["Left of"] = "--left-of"
        self.positions_cmd["Right of"] = "--right-of"
        self.positions_cmd["Below"] = "--below"
        self.positions_cmd["Above"] = "--above"
        self.positions = self.positions_cmd.keys()
        self.init_values()

    def init_values(self):
        """
        Get display properties using xrandr
        """
        # get data
        conns = ["xrandr", "--query"]
        res = Popen(conns, stdout=PIPE).communicate()[0].decode(ENC)

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
        """
        String representing the display for dmenu.
        """
        text = ""
        if self.active:
            text += "Desactivate "
        else:
            text += "Activate "
        text += self.name + " "
        if self.resolution is not None:
            text += "({})".format(self.resolution)
        return text

    def check_repr(self, repr):
        """
        Check if the given represention match the display.
        """
        # TODO : not bulletproof
        return self.name in repr

    def change_resolution(self, new_resolution):
        """
        Change the display resolution.
        """
        if new_resolution not in self.resolutions:
            raise Exception()
        args = ['xrandr', '--output', self.name, '--mode', new_resolution]
        res = Popen(args, stdout=PIPE).communicate()[0].decode(ENC).split('\n')

    def activate(self, active_displs=None):
        """
        Active the display.
        """
        if self.active:
            raise Exception()
        # Check where to put this new display
        position = self.select_position(active_displs=active_displs)
        # run the command
        args = ['xrandr', '--output', self.name] + position + ['--auto']
        Popen(args, stdout=PIPE).communicate()[0].decode(ENC).split('\n')
        self.active = True

    def select_position(self, active_displs):
        """
        Use dmenu to select where to put the display.
        """
        inputs = []
        commands = {}
        for displ in active_displs:
            for pos in self.positions:
                inputs += ["{} {}".format(pos, displ.name)]
                commands[inputs[-1]] = [self.positions_cmd[pos],
                                        displ.name]
        sel = get_selection("Where ", inputs)
        return commands[sel]

    def deactivate(self):
        """
        """
        if not self.active:
            raise Exception("{} already active".format(self.name))
        #
        args = ['xrandr', '--output', self.name, '--off']
        Popen(args, stdout=PIPE).communicate()[0].decode(ENC).split('\n')
        self.active = False

    def get_options(self):
        opts = []
        if not self.connected:
            raise Exception()
        if self.active:
            opts += ["Deactivate"]
        else:
            opts += ["Activate"]
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
    # select a display
    displs = get_displays()
    connected_displs = [displ for displ in displs if displ.connected]
    active_displs = [displ for displ in displs if displ.active]
    connected_displs_repr = [d.dmenu_repr() for d in connected_displs]
    sel = get_selection("Displays : ", connected_displs_repr)
    displ = [d for d in displs if d.check_repr(sel)][0]
    # What to do with the display (active/ desactivate)
    opts = displ.get_options()
    if len(opts) == 1:
        opt = opts[0]
    else:
        opt = get_selection("{} : ".format(displ.name), opts)
    # Execute action
    if opt == "Activate":
        displ.activate(active_displs=active_displs)
    elif opt == "Deactivate":
        if len(active_displs) == 1:
            print("You don't want to deactivate the last display...")
            return 0
        displ.deactivate()


if __name__ == '__main__':
    run()
