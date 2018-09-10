import wx

from app import App


def main():

    handle = wx.App()
    frm = wx.Frame(None, title="Youtube Uploader", size=(700, 500))
    pnl = App(frm)
    frm.Show()

    handle.MainLoop()


# ----------------------------------------------------------------------

if __name__ == '__main__':
    main()
