# By @manuvarkey: https://gitlab.gnome.org/GNOME/gtk/-/issues/175
#
#  This file is part of SkyTemple.
#
#  SkyTemple is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SkyTemple is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SkyTemple.  If not, see <https://www.gnu.org/licenses/>.


import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GObject, Pango


class CustomEditable(Gtk.EventBox, Gtk.CellEditable):
    __gtype_name__ = 'CustomEditable'

    editing_canceled = GObject.property(type=bool,
                                        default=False,
                                        flags=GObject.PARAM_READWRITE)

    def __init__(self):
        Gtk.EventBox.__init__(self)

        self.scrolled = Gtk.ScrolledWindow()
        self.editor = Gtk.TextView()
        self.editor.set_wrap_mode(Gtk.WrapMode.WORD)
        self.editor.set_editable(True)
        self.editor.set_accepts_tab(False)
        self.editor.connect('key-press-event', self.on_key_press_event)
        self.connect("button-press-event", self.on_click_event)
        self.scrolled.add(self.editor)
        self.add(self.scrolled)

    def set_text(self, text):
        self.editor.get_buffer().set_text(text)

    def get_text(self):
        buffer = self.editor.get_buffer()
        [start, end] = buffer.get_bounds()
        text = buffer.get_text(start, end, False)
        return text

    def do_editing_done(self):
        self.remove_widget()

    def do_remove_widget(self):
        pass

    def do_start_editing(self, event):
        self.show_all()
        GLib.timeout_add(50, self.editor.grab_focus)

    def copy_clipboard(self):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.editor.get_buffer().copy_clipboard(clipboard)

    def paste_clipboard(self):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.editor.get_buffer().paste_clipboard(clipboard, None, True)

    def on_key_press_event(self, widget, event):
        '''Catch pressing Enter keys and Tab.

        Shift, Ctrl or Alt combined with Return or Keypad Enter can be used
        for linebreaking. Pressing Return or Keypad Enter alone will finish
        editing.'''

        mask = event.get_state()
        keyname = Gdk.keyval_name(event.get_keyval()[1])

        accel_masks = (Gdk.ModifierType.CONTROL_MASK | \
                       Gdk.ModifierType.SHIFT_MASK | \
                       Gdk.ModifierType.MOD1_MASK)
        enter_keynames = ('Return', 'KP_Enter')
        cancel_keynames = ('Escape',)
        tab_keynames = ('Tab', 'ISO_Left_Tab')

        # Finish editing
        if (keyname in enter_keynames) and not (mask & accel_masks):
            self.props.editing_canceled = False
            self.editing_done()
            return True
        # Cancel editing
        elif keyname in cancel_keynames:
            self.props.editing_canceled = True
            self.editing_done()
            return True
        elif keyname in ('c', 'C') and (mask & Gdk.ModifierType.CONTROL_MASK):
            self.copy_clipboard()
            return True
        elif keyname in ('v', 'V') and (mask & Gdk.ModifierType.CONTROL_MASK):
            self.paste_clipboard()
            return True
        # Finish editing on tab
        elif keyname in tab_keynames:
            self.editing_done()
            return False  # Further propogate event
        # Continue editing
        else:
            self.editor.set_cursor_visible(True)
            return False  # Further propogate event

    def on_click_event(self, button, event):
        """Prevent button click from being cascaded"""
        return True  # Prevent further propogation of event


class CellRendererTextView(Gtk.CellRendererText):
    """Custom cellrenderertext with textview"""

    __gtype_name__ = 'CellRendererTextView'

    full_text = GObject.property(type=str,
                                 default='',
                                 flags=GObject.PARAM_READWRITE)

    def __init__(self):
        Gtk.CellRendererText.__init__(self)

    def do_start_editing(self, event, tree, path, background_area, cell_area, flags):

        if not self.get_property('editable'):
            return

        text = self.props.full_text
        if text == '':
            text = self.props.text

        if text is None:
            text = ''

        editable = CustomEditable()
        editable.connect('editing-done', self.editing_done, tree, path)
        editable.set_text(text)
        editable.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.EXTERNAL)
        return editable

    def editing_done(self, editable, tree, path):
        if editable.props.editing_canceled == False:
            self.emit('edited', path, editable.get_text())
        tree.grab_focus()


