#!/usr/bin/env python3

import os
import os.path
import re
from collections import namedtuple
import traceback
import time
import hashlib
import sys
import shutil

from tkinter import Tk, Label, Button, Entry, Frame, Listbox, StringVar, Grid, Scrollbar, BooleanVar, Checkbutton
from tkinter import LEFT, RIGHT, BOTH, X, Y, END, VERTICAL, RIDGE
from tkinter.filedialog import askdirectory
from tkinter.messagebox import showerror

def repad(widget, attr, margin, spacing, attr2=None, margin2=None):
    if attr2:
        kw2 = {attr2: margin2}
    else:
        kw2 = {}
    children = widget.winfo_children()
    for idx, child in enumerate(children):
        if len(children) == 1:
            child.pack_configure(**kw2, **{attr: margin})
        elif idx == 0:
            child.pack_configure(**kw2, **{attr: (margin, 0)})
        elif (idx+1) == len(children):
            child.pack_configure(**kw2, **{attr: (spacing, margin)})
        else:
            child.pack_configure(**kw2, **{attr: (spacing, 0)})

def Separator(master):
    return Frame(master, relief=RIDGE, width=2, height=2, bd=1)

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

        self._recursive_var = BooleanVar()
        recursive_cb = Checkbutton(self, text='Recursive', variable=self._recursive_var)
        recursive_cb.pack(side=LEFT)
        self._recursive_var.trace('w', self._validate)
        
        open_button = Button(self, text="Open", command=self._select_root)
        open_button.pack(side=LEFT)
        
        refresh_button = Button(self, text="Refresh", command=self._refresh)
        refresh_button.pack(side=LEFT)

        repad(self, 'padx', 0, 5)

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
    def root(self):
        return self._value

    
    @property
    def recursive(self):
        return self._recursive_var.get()


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
        regex_label.grid(column=0, row=0, sticky='w', padx=(0, 5))
        self._regex_entry = Entry(self, textvariable=self._regex_var)
        self._regex_entry.grid(column=1, row=0, sticky='we')

        repl_label = Label(self, text="Replacement:")
        repl_label.grid(column=0, row=1, sticky='w', padx=(0, 5))
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


Options = namedtuple('Options', 'files dirs others hide_wrong_type hide_mismatches overwrite create_missing delete_empty')


class OptionsFrame(Frame):
    def __init__(self, master):
        Frame.__init__(self, master)

        self._vars = {}

        self._add_option('files', 'Files', True)
        self._add_option('dirs', 'Dirs')
        self._add_option('others', 'Others')

        Separator(self).pack(side=LEFT, fill=Y)
        
        self._add_option('hide_wrong_type', 'Hide wrong entries')
        self._add_option('hide_mismatches', 'Hide mismatches')
        
        Separator(self).pack(side=LEFT, fill=Y)

        self._add_option('overwrite', 'Overwrite')
        self._add_option('create_missing', 'Create missing dirs', True)
        self._add_option('delete_empty', 'Delete empty dirs')

        repad(self, 'padx', 0, 5)

    def _add_option(self, name, description, value=False):
        var = BooleanVar()
        self._vars[name] = var
        
        var.set(value)
        var.trace('w', self._options_update)

        cb = Checkbutton(self, text=description, variable=var)
        cb.pack(side=LEFT)

    def _options_update(self, *_):
        self.event_generate('<<OptionsUpdate>>', when='tail')

    @property
    def options(self):
        values = dict(
            (name, var.get()) for (name, var) in self._vars.items()
        )
        return Options(**values)
        

class ListFrame(Frame):
    def __init__(self, master,
                 root, recursive,
                 regex, repl,
                 options):
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
        self._recursive = None
        self._names = None
        self._mapping = None
        self._errors = None
        self._update_root(root, recursive)

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
        self._update_root(event.widget.root, event.widget.recursive)

    def _on_regex_update(self, event):
        self._update_regex(event.widget.regex, event.widget.repl)

    def _on_refresh(self, event):
        self._update_root(self._root, self._recursive)

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

    def _walk(self):
        for root, dirs, files in os.walk(self._root):
            for name in files + dirs:
                path = os.path.join(root, name)
                yield os.path.relpath(path, self._root)

    def _entries(self):
        if self._recursive:
            return self._walk()
        else:
            return os.listdir(self._root)

    def _update_root(self, root, recursive):
        self._root = root
        self._recursive = recursive
        self._left_list.delete(0, END)
        self._names = []
        if self._root:
            for name in sorted(self._entries()):
                path = os.path.join(self._root, name)
                ftype = None
                if os.path.isfile(path):
                    ftype = True
                if os.path.isdir(path):
                    ftype = False
                self._names.append((name, ftype))

        self._update_lists()

    def _insert_name_both(self, name, color, color_right_only=False):
        idx = self._left_list.size()
        self._left_list.insert(END, name)
        if not color_right_only:
            self._left_list.itemconfig(idx, dict(fg=color))
        self._right_list.insert(END, name)
        self._right_list.itemconfig(idx, dict(fg=color))

    def _update_lists(self):
        self._mapping = []
        self._errors = []
        rev_mapping = {}
        self._left_list.delete(0, END)
        self._right_list.delete(0, END)

        if not self._repl:
            self._errors.append('Invalid replacement string')
        
        for name, ftype in self._names:
            enabled = self._is_type_enabled(ftype)
            if enabled or not self._settings.hide_wrong_type:
                if not enabled or not self._regex:
                    self._insert_name_both(name, 'gray')
                elif self._regex and not self._regex.match(name):
                    if not self._settings.hide_mismatches:
                        self._insert_name_both(name, 'gray')
                elif not self._repl:
                    self._insert_name_both(name, 'gray', color_right_only=True)
                else:
                    idx = self._left_list.size()
                    right_name = self._regex.sub(self._repl, name)
                    self._left_list.insert(END, name)
                    self._right_list.insert(END, right_name)

                    if name != right_name:
                        self._mapping.append((name, right_name))

                        right_path = os.path.join(self._root, right_name)
                        if os.path.exists(right_path):
                            error = 'File already exists: %s' % right_name
                        elif right_name in rev_mapping:
                            other_name, other_idx = rev_mapping[right_name]
                            colliding_sources = name, other_name
                            error = 'Name collision: %s <- %s | %s' % (right_name, *colliding_sources)
                            self._right_list.itemconfig(other_idx, dict(fg='red'))
                        else:
                            error = None
                            rev_mapping[right_name] = name, idx

                        if error:
                            self._errors.append(error)
                            self._right_list.itemconfig(idx, dict(fg='red'))

    @property
    def mapping(self):
        if not self._errors:
            return self._mapping

    @property
    def errors(self):
        return self._errors

def md5(val):
    m = hashlib.md5()
    m.update(val.encode('utf8'))
    return m.hexdigest()

class Renamer(object):

    def __init__(self, root):
        self._root = root
        self._renamed = None
        self._temp = None

    def _rename(self, path_from, path_to):
        os.rename(path_from, path_to)
        self._renamed.append((path_from, path_to))

    def _delete(self, path):
        tmp = '%s.%s.%s' % (path, os.getpid(), str(time.time()).replace('.', '_'))
        self._rename(path, tmp)
        self._temp.append(tmp)

    def _ensure_parent_exists(self, path):
        parent = os.path.dirname(path)
        if not os.path.exists(parent):
            self._ensure_parent_exists(parent)
            os.mkdir(parent)
        self._created.append(path)

    @staticmethod
    def _ends_with_slash(path):
        return path.endswith('/') or path.endswith('\\')

    def _rename_mapping(self, mapping, overwrite, create_missing, delete_empty):
        for name_from, name_to in mapping:
            path_from = os.path.join(self._root, name_from)
            path_to = os.path.join(self._root, name_to)
            dir_mapping = False
            
            if self._ends_with_slash(name_from):
                path_from = path_from[:-1]
                dir_mapping = True

            if self._ends_with_slash(name_to):
                path_to = path_to[:-1]
                dir_mapping = True

            if dir_mapping and not os.path.isdir(path_from):
                raise NotADirectoryError(path_from)

            if path_from == path_to:
                continue
            
            if not name_to:
                raise ValueError(name_to)
            if name_to in self._destinations:
                raise ValueError(name_to)
            self._destinations.add(name_to)

            try:
                if os.path.exists(path_to):
                    raise FileExistsError(path_to)
                if create_missing:
                    self._ensure_parent_exists(path_to)
                self._rename(path_from, path_to)
            except FileExistsError:
                if os.path.isdir(path_from):
                    if not os.path.isdir(path_to):
                        raise NotADirectoryError(path_to)
                    sub_mapping = ((os.path.join(name_from, name), os.path.join(name_to, name)) for name in os.listdir(path_from))
                    self._rename_mapping(sub_mapping, overwrite, create_missing, delete_empty)
                    self._delete(path_from)
                elif not overwrite:
                    raise
                else:
                    if os.path.isdir(path_to):
                        raise IsADirectoryError(path_to)
                    self._delete(path_to)
                    self._rename(path_from, path_to)

    def rename_mapping(self, mapping, overwrite, create_missing, delete_empty):
        self._renamed = []
        self._created = []
        self._temp = []
        self._destinations = set()
        
        try:
            self._rename_mapping(mapping, overwrite, create_missing, delete_empty)
        except:
            for done_from, done_to in reversed(self._renamed):
                os.rename(done_to, done_from)
            for path in reversed(self._created):
                os.rmdir(path)
            raise
        
        for path in reversed(self._temp):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

        parents = []
        for path_from, path_to in reversed(self._renamed):
            parents.append(os.path.dirname(path_from))
        processed_parents = set()
        for parent in parents:
            if parent not in processed_parents:
                if os.path.isdir(parent) and not os.listdir(parent):
                    os.rmdir(parent)
                processed_parents.add(parent)
            
        self._renamed = None
        self._created = None
        self._temp = None
        self._destinations = None

def rename(root, mapping, overwrite=False, create_missing=False, delete_empty=False):
    Renamer(root).rename_mapping(mapping, overwrite, create_missing, delete_empty)

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
                           root_frame.root, root_frame.recursive,
                           regex_frame.regex, regex_frame.repl,
                           options_frame.options)
    list_frame.pack(fill=BOTH, expand=True)

    def perform_rename(*args):
        errors = list_frame.errors
        if len(errors) > 20:
            errors = errors[:20] + ['...']
        if errors:
            showerror('Error', '\n'.join(errors))
        elif not list_frame.mapping:
            showerror('Error', 'Nothing to rename')
        else:
            rename(root_frame.value, list_frame.mapping, options_frame.options.overwrite)
            master.event_generate('<<Refresh>>', when='tail')

    rename_button = Button(master, text='Rename', command=perform_rename)
    rename_button.pack()

    repad(master, 'pady', 5, 5, 'padx', 5)

    master.mainloop()


if __name__ == '__main__':
    main()
