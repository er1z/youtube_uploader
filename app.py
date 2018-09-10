import subprocess
import sys

import os
from queue import Queue

import wx
import wx.html2
import wx.dataview as dv
from wx.adv import NotificationMessage

from model import DataModel, Row
from oauth import OAuth
from worker import Worker


class MyFileDropTarget(wx.FileDropTarget):

    def __init__(self, new_file_callback):
        wx.FileDropTarget.__init__(self)
        self.new_file_callback = new_file_callback
        self.enabled = True

    def set_enabled(self, enabled=True):
        self.enabled = enabled

    def OnDropFiles(self, x, y, filenames):

        if not self.enabled:
            return False

        for filepath in filenames:
            self.new_file_callback(filepath)

        return True


class App(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        # Create a dataview control
        self.dvc = dv.DataViewCtrl(self,
                                   style=wx.BORDER_THEME
                                         | dv.DV_ROW_LINES
                                         | dv.DV_VERT_RULES
                                         | dv.DV_MULTIPLE
                                   )

        self.model = DataModel([])
        self.dvc.AssociateModel(self.model)

        self.dvc.AppendTextColumn("path", 1, width=170)
        self.dvc.AppendTextColumn("title", 2, width=300, mode=dv.DATAVIEW_CELL_EDITABLE)
        self.dvc.AppendProgressColumn("progress", 3, width=130)
        self.dvc.AppendTextColumn("status", 4, width=300, mode=dv.DATAVIEW_CELL_EDITABLE)

        # set the Sizer property (same as SetSizer)
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.dvc, 1, wx.EXPAND)

        b2 = wx.Button(self, label="Add files")
        self.Bind(wx.EVT_BUTTON, self.OnAddRow, b2)
        self.button_add = b2

        b3 = wx.Button(self, label="Delete selected")
        b3.Enable(False)
        self.Bind(wx.EVT_BUTTON, self.OnDeleteRows, b3)
        self.button_delete = b3

        b5 = wx.Button(self, label="Start upload")
        b5.Enable(False)
        self.Bind(wx.EVT_BUTTON, self.start_upload, b5)
        self.button_upload_start = b5

        b6 = wx.Button(self, label="Stop upload")
        b6.Enable(False)
        self.Bind(wx.EVT_BUTTON, self.stop_upload, b6)
        self.button_upload_stop = b6

        self.in_progress = False
        self.files_in_progress = 0

        btnbox = wx.BoxSizer(wx.HORIZONTAL)
        btnbox.Add(b2, 0, wx.LEFT | wx.RIGHT, 5)
        btnbox.Add(b3, 0, wx.LEFT | wx.RIGHT, 5)
        btnbox.Add(b5, 0, wx.LEFT | wx.RIGHT, 5)
        btnbox.Add(b6, 0, wx.LEFT | wx.RIGHT, 5)
        self.Sizer.Add(btnbox, 0, wx.TOP | wx.BOTTOM, 5)

        # Bind some events so we can see what the DVC sends us
        self.Bind(dv.EVT_DATAVIEW_ITEM_START_EDITING, self.on_before_edit, self.dvc)
        # self.Bind(dv.EVT_DATAVIEW_ITEM_EDITING_DONE, self.OnEditingDone, self.dvc)
        # self.Bind(dv.EVT_DATAVIEW_ITEM_VALUE_CHANGED, self.OnValueChanged, self.dvc)

        self.Bind(dv.EVT_DATAVIEW_ITEM_ACTIVATED, self.RightClick, self.dvc)

        parent.Bind(wx.EVT_CLOSE, self.OnClose)
        self.parent = parent

        # worker stuff
        self.enclosure_queue = Queue()

        self.worker = None
        # drop
        file_drop_target = MyFileDropTarget(self.on_drop)
        self.SetDropTarget(file_drop_target)

        auth = OAuth(self)
        self.oauth = auth
        if not auth.ShowModal():
            self.parent.Close()

    def open(self, filepath):
        if sys.platform.startswith('darwin'):
            subprocess.call(('open', filepath))
        elif os.name == 'nt':  # For Windows
            os.startfile(filepath)
        elif os.name == 'posix':  # For Linux, Mac, etc.
            subprocess.call(('xdg-open', filepath))

    def RightClick(self, evt):
        item = self.model.GetRow(evt.GetItem())
        path = ''
        if evt.GetColumn() == 1:
            path = self.model.GetValueByRow(item, 1)
        elif evt.GetColumn() == 4:
            path = self.model.GetValueByRow(item, 4)

        if path:
            self.open(path)

    def OnDeleteRows(self, evt):
        items = self.dvc.GetSelections()
        rows = [self.model.GetRow(item) for item in items]
        self.model.delete_rows(rows)

        if len(self.model.data) == 0:
            self.button_upload_start.Enable(False)
            self.button_delete.Enable(False)

    def lock_ui(self, lock=True):
        self.in_progress = lock
        self.button_add.Enable(not lock)
        self.button_delete.Enable(not lock)
        self.button_upload_start.Enable(not lock)
        self.button_upload_stop.Enable(lock)

    def start_upload(self, evt):

        if len(self.model.data) == 0:
            return

        self.files_in_progress = len(self.model.data)

        self.lock_ui(True)

        self.enclosure_queue.empty()

        for i in self.model.data:
            self.enclosure_queue.put(i)

        self.worker = Worker(self.enclosure_queue, self, self.oauth.result)
        self.worker.start()

    def on_upload_end(self):

        self.files_in_progress = self.files_in_progress-1

        if self.files_in_progress == 0:
            self.lock_ui(False)
            NotificationMessage("Youtube uploader", message="We're done!", parent=None,
                                flags=wx.ICON_INFORMATION).Show()

    def stop_upload(self, evt):
        self.worker.stop()
        self.lock_ui(False)

    def open_files(self):
        # Create open file dialog
        openFileDialog = wx.FileDialog(self, "Open", "", "",
                                       "Video files (*.mts;*.mp4;*.avi)|*.mts;*.mp4;*.avi",
                                       wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE)

        openFileDialog.ShowModal()

        return openFileDialog.GetPaths()

    def add_path(self, path):

        if self.model.file_exists(path):
            return

        name, extension = os.path.splitext(os.path.basename(path))

        extension = extension.lower()[1:]

        if extension not in ['avi', 'mts', 'mp4']:
            return

        row = Row(path, name)
        self.model.AddRow(row)

    def on_drop(self, file):
        self.add_path(file)

    def OnAddRow(self, evt):
        for i in self.open_files():
            name = os.path.splitext(os.path.basename(i))[0]

            row = Row(i, name, 0, '')
            self.model.AddRow(row)

            self.button_upload_start.Enable(True)
            self.button_delete.Enable(True)

    def on_before_edit(self, evt):
        # todo!
        if self.in_progress:
            evt.SetEditCanceled(True)

    def OnClose(self, e):
        self.parent.Destroy()
