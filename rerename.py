#!/usr/bin/env python3

import os
import os.path
import re

from tkinter import Tk, Label, Button, Entry, Frame, Listbox, StringVar, Grid, Scrollbar, BooleanVar, Checkbutton
from tkinter import LEFT, RIGHT, BOTH, X, Y, END, VERTICAL
from tkinter.filedialog import askdirectory


master = Tk()
master.title('Regex mass rename')

class RootFrame(Frame):
    def __init__(self, master):
        Frame.__init__(self, master)

        self._value = os.getcwd()
        self._var = StringVar(self)
        self._var.set(self._value)
        self._var.trace('w', self._validate)

        label = Label(self, text="Root:")
        label.pack(side=LEFT)
        self._entry = Entry(self, textvariable=self._var)
        self._entry.pack(side=LEFT, fill=X, expand=True)
        button = Button(self, text="Open", command=self.select_root)
        button.pack(side=LEFT)

    def _validate(self, *_):
        res = self._var.get().strip()
        if os.path.isdir(res):
            self._entry.config(fg='black')
            self._value = res
        else:
            self._entry.config(fg='red')
            self._value = None
        self.event_generate('<<RootUpdate>>', when='tail')

    def select_root(self):
        value = askdirectory()
        if value:
            self._var.set(value)
            self._validate()

    @property
    def value(self):
        return self._value

class RegexFrame(Frame):
    def __init__(self, master):
        Frame.__init__(self, master)

        self._regex_var = StringVar(self)
        self._regex_var.set('.*')
        self._regex_var.trace('w', self._validate)
        self._regex_value = re.compile(self._regex_var.get())

        self._repl_var = StringVar(self)
        self._repl_var.set(r'\0')
        self._repl_var.trace('w', self._validate)
        self._repl_value = r'\g<0>'

        Grid.columnconfigure(self, 1, weight=1)

        regex_label = Label(self, text="Regex:")
        regex_label.grid(column=0, row=0, sticky='w')
        self._regex_entry = Entry(self, textvariable=self._regex_var)
        self._regex_entry.grid(column=1, row=0, sticky='we')

        repl_label = Label(self, text="Replacement:")
        repl_label.grid(column=0, row=1, sticky='w')
        self._repl_entry = Entry(self, textvariable=self._repl_var)
        self._repl_entry.grid(column=1, row=1, sticky='we')

    def _validate(self, *_):
        regex_str = self._regex_var.get()
        if not regex_str.startswith('^'):
            regex_str = '^' + regex_str
        if not regex_str.endswith('$'):
            regex_str += '$'
        try:
            self._regex_value = re.compile(regex_str)
        except re.error:
            self._regex_value = None
            self._regex_entry.config(fg='red')
        else:
            self._regex_entry.config(fg='black')

        repl_str = self._repl_var.get().replace(r'\0', r'\g<0>')
        try:
            if self._regex_value:
                self._regex_value.sub(repl_str, '')
        except re.error:
            self._repl_value = None
            self._repl_entry.config(fg='red')
        else:
            self._repl_value = repl_str
            self._repl_entry.config(fg='black')

        self.event_generate('<<RegexUpdate>>', when='tail')

    @property
    def regex(self):
        return self._regex_value

    @property
    def repl(self):
        return self._repl_value

class OptionsFrame(Frame):
    def __init__(self, master):
        Frame.__init__(self, master)

        self._files_var = BooleanVar()
        self._files_var.set(True)
        files_cb = Checkbutton(self, text="Files", variable=self._files_var)
        files_cb.pack(side=LEFT)
        self._files_var.trace('w', self._options_update)

        self._dirs_var = BooleanVar()
        dirs_cb = Checkbutton(self, text="Dirs", variable=self._dirs_var)
        dirs_cb.pack(side=LEFT)
        self._dirs_var.trace('w', self._options_update)

        self._others_var = BooleanVar()
        others_cb = Checkbutton(self, text="Others", variable=self._others_var)
        others_cb.pack(side=LEFT)
        self._others_var.trace('w', self._options_update)

        self._hide_wrong_type_var = BooleanVar(self)
        hide_wrong_type_cb = Checkbutton(self, text="Hide wrong entries", variable=self._hide_wrong_type_var)
        hide_wrong_type_cb.pack(side=LEFT)
        self._hide_wrong_type_var.trace('w', self._options_update)

        self._hide_mismatches_var = BooleanVar(self)
        hide_mismatches_cb = Checkbutton(self, text="Hide mismatches", variable=self._hide_mismatches_var)
        hide_mismatches_cb.pack(side=LEFT)
        self._hide_mismatches_var.trace('w', self._options_update)

    def _options_update(self, *_):
        self.event_generate('<<OptionsUpdate>>', when='tail')

    @property
    def files(self):
        return self._files_var.get()

    @property
    def dirs(self):
        return self._dirs_var.get()

    def others(self):
        return self._others_var.get()

    @property
    def hide_wrong_type(self):
        return self._hide_wrong_type_var.get()

    @property
    def hide_mismatches(self):
        return self._hide_mismatches_var.get()
    
        
class ListFrame(Frame):
    def __init__(self, master, root, regex, repl):
        Frame.__init__(self, master)

        self._left_list = Listbox(self)
        self._left_list.pack(side=LEFT, fill=BOTH, expand=True)
        
        self._right_list = Listbox(self)
        self._right_list.pack(side=LEFT, fill=BOTH, expand=True)
        self._right_scroll = Scrollbar(self._right_list, orient=VERTICAL)
        self._right_list.config(yscrollcommand=self._right_scroll.set)
        self._right_scroll.config(command=self._right_list.yview)

        self._scrollbar = Scrollbar(self, orient=VERTICAL, command=self._scroll_scrollbar)
        self._scrollbar.pack(side=RIGHT, fill=Y)
        self._left_list.config(yscrollcommand=self._scroll_left)
        self._right_list.config(yscrollcommand=self._scroll_right)

        self._regex = regex
        self._repl = repl
        self._update_root(root)

        master.bind('<<RootUpdate>>', self._on_root_update)
        master.bind('<<RegexUpdate>>', self._on_regex_update)
        master.bind('<<OptionsUpdate>>', self._on_options_update)

    def _scroll_left(self, sfrom, sto):
        self._scrollbar.set(sfrom, sto)
        self._right_list.yview('moveto', sfrom)

    def _scroll_right(self, sfrom, sto):
        self._scrollbar.set(sfrom, sto)
        self._left_list.yview('moveto', sfrom)

    def _scroll_scrollbar(self, *args):
        self._left_list.yview(*args)
        self._right_list.yview(*args)

    def _on_root_update(self, event):
        self._update_root(event.widget.value)

    def _on_regex_update(self, event):
        self._update_regex(event.widget.regex, event.widget.repl)

    def _on_options_update(self, event):
        self._update_root(self._root)

    def _update_regex(self, regex, repl):
        self._regex = regex
        self._repl = repl

        names = self._left_list.get(0, END)
        for idx, name in enumerate(names):
            if self._regex and self._regex.match(name):
                self._left_list.itemconfig(idx, dict(fg='black'))
            else:
                self._left_list.itemconfig(idx, dict(fg='gray'))
        self._update_right(names)

    def _update_root(self, root):
        self._root = root
        self._left_list.delete(0, END)
        names = sorted(os.listdir(root))
        for name in names:
            idx = self._left_list.size()
            self._left_list.insert(END, name)
            if not (self._regex and self._regex.match(name)):
                self._left_list.itemconfig(idx, dict(fg='gray'))
        self._update_right(names)

    def _update_right(self, names):
        self._right_list.delete(0, END)
        for name in names:
            if self._regex and self._repl and self._regex.match(name):
                right_name = self._regex.sub(self._repl, name)
                self._right_list.insert(END, right_name)
            else:
                idx = self._right_list.size()
                self._right_list.insert(END, name)
                self._right_list.itemconfig(idx, dict(fg='gray'))
            

root_frame = RootFrame(master)
root_frame.pack(fill=X)

regex_frame = RegexFrame(master)
regex_frame.pack(fill=X)

options_frame = OptionsFrame(master)
options_frame.pack(fill=X)

list_frame = ListFrame(master, root_frame.value, regex_frame.regex, regex_frame.repl)
list_frame.pack(fill=BOTH, expand=True)

master.mainloop()
