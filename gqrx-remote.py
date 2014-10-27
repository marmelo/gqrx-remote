#!/usr/bin/env python

"""
Remote application that interacts with gqrx using rigctl protocol.
Gqrx partially implements rigctl since version 2.3.

Please refer to:
http://gqrx.dk/
http://gqrx.dk/doc/remote-control
http://sourceforge.net/apps/mediawiki/hamlib/index.php?title=Documentation

Author: Rafael Marmelo <rafael@defying.me>
License: MIT License

Copyright (c) 2014 Rafael Marmelo
"""

import csv
import os.path
import telnetlib
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox


class RigCtl():
    """Basic rigctl client implementation."""

    def __init__(self, hostname='127.0.0.1', port=7356):
        self.hostname = hostname
        self.port = port

    def _request(self, request):
        con = telnetlib.Telnet(self.hostname, self.port)
        con.write(('%s\n' % request).encode('ascii'))
        response = con.read_some().decode('ascii').strip()
        con.write('c\n'.encode('ascii'))
        return response

    def set_frequency(self, frequency):
        return self._request('F %s' % frequency)

    def get_frequency(self):
        return self._request('f')

    def set_mode(self, mode):
        return self._request('M %s' % mode)

    def get_mode(self):
        return self._request('m')

    def get_level(self):
        return self._request('l')


class GqrxRemote(ttk.Frame):
    """Remote application that interacts with gqrx using rigctl protocol.
    Gqrx partially implements rigctl since version 2.3.
    """

    def __init__(self, root):
        ttk.Frame.__init__(self, root)
        self.config = 'gqrx-bookmarks.csv'
        self.build()
        self.csv_load()

    def build(self):
        """Build and initialize the GUI widgets."""
        self.master.title("Gqrx Remote")
        self.master.minsize(900, 244)
        self.pack(fill=tk.BOTH, expand=1, padx=5, pady=5)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # +------------------------------+------------------------------+
        # |                              | Hostname:    _______________ |
        # |                              | Port:        _______________ |
        # |                              |                              |
        # |                              | Frequency:   _______________ |
        # |        Frequency List        | Mode:        ____________[v] |
        # |                              | Description: _______________ |
        # |                              |                              |
        # |                              |         [add] [delete] [get] |
        # |                              |                              |
        # |                              |  [x] Always on top?   [quit] |
        # +------------------------------+------------------------------+

        # frequency list
        self.tree = ttk.Treeview(self, columns=('frequency', 'mode', 'description'), show="headings")
        self.tree.heading('frequency', text='Frequency', anchor=tk.CENTER)
        self.tree.column('frequency', minwidth=130, width=130, stretch=False, anchor=tk.CENTER)
        self.tree.heading('mode', text='Mode', anchor=tk.CENTER)
        self.tree.column('mode', minwidth=80, width=80, stretch=False, anchor=tk.CENTER)
        self.tree.heading('description', text='Description', anchor=tk.W)
        self.tree.column('description', stretch=True, anchor=tk.W)
        ysb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        ysb.grid(row=0, column=1, sticky=tk.NS)
        xsb = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        xsb.grid(row=1, column=0, sticky=tk.EW)
        self.tree.configure(yscroll=ysb.set, xscroll=xsb.set)
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)
        self.tree.bind('<<TreeviewSelect>>', self.cb_autofill_form)
        self.tree.bind('<Double-Button-1>', self.cb_set_frequency)

        # vertical separator
        ttk.Frame(self).grid(row=0, column=2, rowspan=2, padx=5)

        # right-side container
        self.menu = ttk.Frame(self)
        self.menu.grid(row=0, column=3, rowspan=2, stick=tk.NSEW)
        self.menu.rowconfigure(7, weight=1)

        ttk.Label(self.menu, text="Hostname:").grid(row=0, column=0, sticky=tk.W)
        self.txt_hostname = ttk.Entry(self.menu)
        self.txt_hostname.grid(row=0, column=1, columnspan=3, padx=2, pady=2, sticky=tk.EW)

        ttk.Label(self.menu, text="Port:").grid(row=1, column=0, sticky=tk.W)
        self.txt_port = ttk.Entry(self.menu)
        self.txt_port.grid(row=1, column=1, columnspan=3, padx=2, pady=2, sticky=tk.EW)

        # horizontal separator
        ttk.Frame(self.menu).grid(row=2, column=0, columnspan=3, pady=5)

        ttk.Label(self.menu, text="Frequency:").grid(row=3, column=0, sticky=tk.W)
        self.txt_frequency = ttk.Entry(self.menu)
        self.txt_frequency.grid(row=3, column=1, columnspan=3, padx=2, pady=2, sticky=tk.EW)

        ttk.Label(self.menu, text="Mode:").grid(row=4, column=0, sticky=tk.W)
        self.cbb_mode = ttk.Combobox(self.menu, width=18)
        self.cbb_mode.grid(row=4, column=1, columnspan=3, padx=2, pady=2, sticky=tk.EW)
        self.cbb_mode['values'] = ('', 'OFF', 'RAW', 'AM', 'FM', 'WFM', 'WFM_ST', 'LSB', 'USB', 'CW', 'CWL', 'CWU')

        ttk.Label(self.menu, text="Description:").grid(row=5, column=0, sticky=tk.W)
        self.txt_description = ttk.Entry(self.menu)
        self.txt_description.grid(row=5, column=1, columnspan=3, padx=2, pady=2, sticky=tk.EW)

        self.btn_add = ttk.Button(self.menu, text="Add", width=6, command=self.cb_add)
        self.btn_add.grid(row=6, column=1, padx=2, pady=2)

        self.btn_delete = ttk.Button(self.menu, text="Delete", width=6, command=self.cb_delete)
        self.btn_delete.grid(row=6, column=2, padx=2, pady=2)

        self.btn_load = ttk.Button(self.menu, text="Get", width=6, command=self.cb_get_frequency)
        self.btn_load.grid(row=6, column=3, padx=2, pady=2)

        self.ckb_top = ttk.Checkbutton(self.menu, text="Always on top?", command=self.cb_top)
        self.ckb_top.grid(row=8, column=0, columnspan=2, sticky=tk.E)

        self.btn_quit = ttk.Button(self.menu, text="Quit", command=self.master.destroy)
        self.btn_quit.grid(row=8, column=2, columnspan=2, sticky=tk.SE)

        # set initial status
        self.txt_hostname.insert(0, "127.0.0.1")
        self.txt_port.insert(0, "7356")
        self.cbb_mode.current(0)
        self.ckb_top.invoke()

    def csv_load(self):
        """Read the frequency bookmarks file and populate the tree."""
        if os.path.isfile(self.config):
            with open(self.config, 'r') as file:
                reader = csv.reader(file, delimiter=',')
                for line in reader:
                    line[0] = self._frequency_pp(line[0])
                    self.tree.insert('', tk.END, values=line)

    def csv_save(self):
        """Save current frequencies to disk."""
        with open(self.config, 'w') as file:
            writer = csv.writer(file, delimiter=',')
            for item in self.tree.get_children():
                values = self.tree.item(item).get('values')
                values[0] = self._frequency_pp_parse(values[0])
                writer.writerow(values)

    def cb_top(self):
        """Set window property to be always on top."""
        self.master.attributes("-topmost", 'selected' in self.ckb_top.state())

    def cb_get_frequency(self):
        """Get current gqrx frequency and mode."""
        # clear fields
        self.txt_frequency.delete(0, tk.END)
        self.cbb_mode.delete(0, tk.END)
        self.txt_description.delete(0, tk.END)
        try:
            frequency = self._connect().get_frequency()
            mode = self._connect().get_mode()
            # update fields
            self.txt_frequency.insert(0, self._frequency_pp(frequency))
            self.cbb_mode.insert(0, mode)
        except Exception as err:
            tkinter.messagebox.showerror("Error", "Could not connect to gqrx.\n%s" % err, parent=self)

    def cb_set_frequency(self, event):
        """Set the gqrx frequency and mode."""
        item = self.tree.focus()
        values = self.tree.item(item).get('values')
        try:
            self._connect().set_frequency(values[0].replace(',', ''))
            self._connect().set_mode(values[1])
        except Exception as err:
            tkinter.messagebox.showerror("Error", "Could not set frequency.\n%s" % err, parent=self)

    def cb_autofill_form(self, event):
        """Auto-fill bookmark fields with details of currently selected Treeview entry."""
        item = self.tree.focus()
        values = self.tree.item(item).get('values')
        self.txt_frequency.delete(0, tk.END)
        self.txt_frequency.insert(0, values[0])
        self.cbb_mode.delete(0, tk.END)
        self.cbb_mode.insert(0, values[1])
        self.txt_description.delete(0, tk.END)
        self.txt_description.insert(0, values[2])

    def cb_add(self):
        """Add frequency to tree."""
        # get values
        frequency = self._frequency_pp_parse(self.txt_frequency.get())
        mode = self.cbb_mode.get()
        description = self.txt_description.get()
        # find where to insert (insertion sort)
        idx = tk.END
        for item in self.tree.get_children():
            curr_freq = self._frequency_pp_parse(self.tree.item(item).get('values')[0])
            curr_mode = self.tree.item(item).get('values')[1]
            if frequency < curr_freq:
                idx = self.tree.index(item)
                break
            elif frequency == curr_freq and mode == curr_mode:
                tkinter.messagebox.showerror("Error", "A bookmark with the same frequency and mode already exists.", parent=self)
                return
        # insert
        item = self.tree.insert('', idx, values=[self._frequency_pp(frequency), mode, description])
        self.tree.selection_set(item)
        self.tree.focus(item)
        self.tree.see(item)
        # save
        self.csv_save()

    def cb_delete(self):
        """Delete frequency from tree."""
        item = self.tree.focus()
        if item != '':
            self.tree.delete(item)
            # save
            self.csv_save()

    def _connect(self):
        return RigCtl(self.txt_hostname.get(), self.txt_port.get())

    def _frequency_pp(self, frequency):
        """Add thousands separator."""
        return '{:,}'.format(int(frequency))

    def _frequency_pp_parse(self, frequency):
        """Remove thousands separator."""
        return int(str(frequency).replace(',', ''))


# entry point
if __name__ == "__main__":
    root = tk.Tk()
    app = GqrxRemote(root)
    app.mainloop()
