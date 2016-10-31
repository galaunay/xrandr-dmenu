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


class Display(object):
    """
    Represent a display.
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
        # get xrandr output
        conns = ["xrandr", "--query"]
        lines = Popen(conns, stdout=PIPE).communicate()[0].decode(ENC).split('\n')
        # Get data from it
        regex_display = r"^{} ([^\s]+) (\d+x\d+)?(\+\d+\+\d+)?.*".format(self.name)
        regex_resolution = r"^(\d+x\d+).*$"
        resolutions = []
        for i in range(len(lines)):
            line = lines[i].rstrip().lstrip()
            if line[0:len(self.name)] == self.name:
                match = re.search(regex_display, line)
                state, resolution, _ = match.groups()
                for j in range(i + 1, len(lines)):
                    line = lines[j].rstrip().lstrip()
                    if len(line) == 0:
                        break
                    if line[0] not in ["{}".format(i) for i in range(10)]:
                        break
                    match = re.search(regex_resolution, line)
                    resolutions.append(match.groups()[0])
                break
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
        self.resolutions = resolutions

    def get_possible_actions(self):
        """
        dict representing the possible actions on this display.
        """
        options = {}
        if self.active:
            options["Desactivate {}".format(self.name)] = self.deactivate
            options["Change resolution of {} ({})"
                    .format(self.name, self.resolution)] = self.change_resolution
        else:
            options["Activate {}".format(self.name)] = self.activate
        return options

    def change_resolution(self, active_displs):
        """
        Change the display resolution.
        """
        new_resolution = use_dmenu("new resolution (currently {}) :".format(self.resolution),
                                   self.resolutions)
        args = ['xrandr', '--output', self.name, '--mode', new_resolution]
        Popen(args, stdout=PIPE).communicate()[0].decode(ENC).split('\n')

    def activate(self, active_displs=None):
        """
        Active the display.
        """
        if self.active:
            raise Exception()
        args = ['xrandr', '--output', self.name, '--auto']
        # Check where to put this new display
        if len(active_displs) != 0:
            position = self.select_position(active_displs=active_displs)
            args += position
        # run the command
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
        sel = use_dmenu("Where ", inputs)
        return commands[sel]

    def deactivate(self, active_displs):
        """
        Deactive the display.
        """
        if not self.active:
            raise Exception("{} already active".format(self.name))
        if len(active_displs) == 1:
            raise Exception("You don't want to desactivate the last display")
        # run
        args = ['xrandr', '--output', self.name, '--off']
        Popen(args, stdout=PIPE).communicate()[0].decode(ENC).split('\n')
        self.active = False


def get_displays():
    """
    Return the list of displays.
    """
    # get dispays names
    conns = ["xrandr", "--query"]
    res = Popen(conns, stdout=PIPE).communicate()[0].decode(ENC)
    regex = r"\n([^\s]*) (connected|disconnected).*"
    names = [res[0] for res in re.findall(regex, res)]
    # create display object
    displs = [Display(name) for name in names]
    return displs

def use_dmenu(prompt, inputs):
    """Combine the arg lists and send to dmenu for selection.
    """
    if len(inputs) == 0:
        raise Exception("Empty input list")
    inputs_bytes = "\n".join(inputs).encode(ENC)
    sel = Popen(dmenu_cmd(len(inputs), prompt),
                stdin=PIPE,
                stdout=PIPE).communicate(input=inputs_bytes)[0].decode(ENC)
    sel = inputs[int(sel)]
    if not sel.rstrip():
        sys.exit()
    return sel.rstrip()

def run():
    """
    Run the whole thing.
    """
    # Gather possible actions for each displays
    displs = get_displays()
    connected_displs = [displ for displ in displs if displ.connected]
    active_displs = [displ for displ in displs if displ.active]
    actions = {}
    for displ in connected_displs:
        actions.update(displ.get_possible_actions())
    # Select an action
    sel = use_dmenu("Displays : ", actions.keys())
    print(sel)
    # perform the action
    actions[sel](active_displs=active_displs)

if __name__ == '__main__':
    run()
