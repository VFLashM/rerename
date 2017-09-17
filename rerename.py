#!/usr/bin/env python3

import os
import os.path
import re

from tkinter import Tk, Label, Button, Entry, Frame, Listbox, StringVar
from tkinter import LEFT, RIGHT, BOTH, X, END
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

        
class ListFrame(Frame):
    def __init__(self, master, root, regex):
        Frame.__init__(self, master)

        self._left_list = Listbox(self)
        self._left_list.pack(side=LEFT, fill=BOTH, expand=True)
        self._right_list = Listbox(self)
        self._right_list.pack(side=LEFT, fill=BOTH, expand=True)

        self._re = regex
        self._update_root(root)

    def _upadte_regex(self, regex):
        
        pass

    def _update_root(self, root):
        self._left_list.delete(0, END)
        for name in sorted(os.listdir(root)):
            self._left_list.insert(END, name)
        self._update_right()

    def _update_right(self):
        self._right_list.delete(0, END)
        names = self._left_list.get(0, END)
        for name in names:
            #self._re.sub()
            self._right_list.insert(END, name)
            

root_frame = RootFrame(master)
root_frame.pack(fill=X)


list_frame = ListFrame(master, root_frame.value, None)
list_frame.pack(fill=BOTH, expand=True)

master.mainloop()
