import wx.dataview as dv


class Row:
    def __init__(self, path, title, progress=0, status='', completed=False):
        self.path = path
        self.title = title
        self.progress = progress
        self.status = status
        self.completed = completed


class DataModel(dv.DataViewIndexListModel):
    def __init__(self, data):
        dv.DataViewIndexListModel.__init__(self, len(data))
        self.data = data

    def GetValueByRow(self, row, col):
        if col == 1:
            return self.data[row].path
        elif col == 2:
            return self.data[row].title
        elif col == 3:
            return self.data[row].progress
        elif col == 4:
            return self.data[row].status

    def SetValueByRow(self, value, row, col):

        if col == 2:
            self.data[row].title = value

        return True

    def GetColumnCount(self):
        return 4

    def GetColumnType(self, col):
        return "string"

    def GetCount(self):
        return len(self.data)

    def GetAttrByRow(self, row, col, attr):
        if col == 1 or (col == 4 and self.data[row].completed):
            attr.SetColour('blue')
            attr.SetBold(True)
            return True
        return False

    def delete_rows(self, rows):
        # make a copy since we'll be sorting(mutating) the list
        rows = list(rows)
        # use reverse order so the indexes don't change as we remove items
        rows.sort(reverse=True)

        for row in rows:
            # remove it from our data structure
            del self.data[row]
            # notify the view(s) using this model that it has been removed
            self.RowDeleted(row)

    def file_exists(self, path):
        for row in self.data:
            if row.path == path:
                return True

        return False

    def AddRow(self, value):
        self.data.append(value)
        self.RowAppended()