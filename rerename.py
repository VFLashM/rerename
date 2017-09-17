#!/usr/bin/env python3

import os
import os.path
import re
from collections import namedtuple
import traceback
import time
import hashlib
import sys

from tkinter import Tk, Label, Button, Entry, Frame, Listbox, StringVar, Grid, Scrollbar, BooleanVar, Checkbutton
from tkinter import LEFT, RIGHT, BOTH, X, Y, END, VERTICAL
from tkinter.filedialog import askdirectory
from tkinter.messagebox import showerror

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
        
        open_button = Button(self, text="Open", command=self._select_root)
        open_button.pack(side=LEFT)
        
        refresh_button = Button(self, text="Refresh", command=self._refresh)
        refresh_button.pack(side=LEFT)

    def _refresh(self):
        self.event_generate('<<Refresh>>', when='tail')

    def _validate(self, *_):
        res = self._var.get().strip()
        if os.path.isdir(res):
            self._entry.config(fg='black')
            self._value = res
        else:
            self._entry.config(fg='red')
            self._value = None
        self.event_generate('<<RootUpdate>>', when='tail')

    def _select_root(self):
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


Options = namedtuple('Options', 'files dirs others hide_wrong_type hide_mismatches overwrite')


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

        self._overwrite_var = BooleanVar()
        overwrite_cb = Checkbutton(self, text="Overwrite", variable=self._overwrite_var)
        overwrite_cb.pack(side=LEFT)
        self._overwrite_var.trace('w', self._options_update)

    def _options_update(self, *_):
        self.event_generate('<<OptionsUpdate>>', when='tail')

    @property
    def options(self):
        return Options(
            files=self._files_var.get(),
            dirs=self._dirs_var.get(),
            others=self._others_var.get(),
            hide_wrong_type=self._hide_wrong_type_var.get(),
            hide_mismatches=self._hide_mismatches_var.get(),
            overwrite=self._overwrite_var.get(),
        )
        

class ListFrame(Frame):
    def __init__(self, master, root, regex, repl, options):
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
        self._settings = options
        self._root = None
        self._names = None
        self._mapping = None
        self._update_root(root)

        master.bind('<<RootUpdate>>', self._on_root_update)
        master.bind('<<RegexUpdate>>', self._on_regex_update)
        master.bind('<<OptionsUpdate>>', self._on_options_update)
        master.bind('<<Refresh>>', self._on_refresh)

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

    def _on_refresh(self, event):
        self._update_root(self._root)

    def _on_options_update(self, event):
        self._settings = event.widget.options
        self._update_lists()

    def _update_regex(self, regex, repl):
        self._regex = regex
        self._repl = repl
        self._update_lists()

    def _is_type_enabled(self, ftype):
        if ftype is True:
            return self._settings.files
        elif ftype is False:
            return self._settings.dirs
        else:
            return self._settings.others

    def _update_root(self, root):
        self._root = root
        self._left_list.delete(0, END)
        self._names = []
        for name in sorted(os.listdir(root)):
            path = os.path.join(self._root, name)
            ftype = None
            if os.path.isfile(path):
                ftype = True
            if os.path.isdir(path):
                ftype = False
            self._names.append((name, ftype))

        self._update_lists()

    def _insert_name_both(self, name, color):
        idx = self._left_list.size()
        self._left_list.insert(END, name)
        self._left_list.itemconfig(idx, dict(fg=color))
        self._right_list.insert(END, name)
        self._right_list.itemconfig(idx, dict(fg=color))

    def _update_lists(self):
        self._mapping = []
        self._left_list.delete(0, END)
        self._right_list.delete(0, END)
        
        for name, ftype in self._names:
            enabled = self._is_type_enabled(ftype)
            if enabled or not self._settings.hide_wrong_type:
                if not enabled or not self._regex:
                    self._insert_name_both(name, 'gray')
                elif self._regex and not self._regex.match(name):
                    if not self._settings.hide_mismatches:
                        self._insert_name_both(name, 'red')
                else:
                    right_name = self._regex.sub(self._repl, name)
                    self._left_list.insert(END, name)
                    self._right_list.insert(END, right_name)
                    self._mapping.append((name, right_name))

    @property
    def mapping(self):
        return self._mapping

def md5(val):
    m = hashlib.md5()
    m.update(val.encode('utf8'))
    return m.hexdigest()

def rename(root, mapping, overwrite):
    renamed = []
    temp = []
    for name_from, name_to in mapping:
        path_from = os.path.join(root, name_from)
        path_to = os.path.join(root, name_to)
        try:
            try:
                if os.path.exists(path_to):
                    raise FileExistsError(path_to)
                os.rename(path_from, path_to)
            except FileExistsError:
                if not overwrite:
                    raise
                path_tmp = '%s.%s.%s.%s' % (path_to, os.getpid(), int(time.time()), md5(path_from))
                os.rename(path_to, path_tmp)
                renamed.append((path_to, path_tmp))
                temp.append(path_tmp)
                os.rename(path_from, path_to)
        except Exception as e:
            for done_from, done_to in reversed(renamed):
                os.rename(done_to, done_from)
            raise
        else:
            renamed.append((path_from, path_to))
    for path in temp:
        os.remove(path)

def show_error(self, et, ev, tb):
    for line in traceback.format_exception(et, ev, tb):
        sys.stderr.write(line)
    
    err = traceback.format_exception_only(et, ev)
    showerror('Exception', ''.join(err))

def main():
    Tk.report_callback_exception = show_error
    master = Tk()
    master.title('Regex mass rename')                    

    root_frame = RootFrame(master)
    root_frame.pack(fill=X)

    regex_frame = RegexFrame(master)
    regex_frame.pack(fill=X)

    options_frame = OptionsFrame(master)
    options_frame.pack(fill=X)

    list_frame = ListFrame(master,
                           root_frame.value,
                           regex_frame.regex, regex_frame.repl,
                           options_frame.options)
    list_frame.pack(fill=BOTH, expand=True)

    def perform_rename(*args):
        rename(root_frame.value, list_frame.mapping, options_frame.options.overwrite)
        master.event_generate('<<Refresh>>', when='tail')

    rename_button = Button(master, text='Rename', command=perform_rename)
    rename_button.pack()

    master.mainloop()


if __name__ == '__main__':
    main()
