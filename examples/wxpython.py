# Example of embedding CEF Python browser using wxPython library.
# This example has a top menu and a browser widget without navigation bar.

# Tested configurations:
# - wxPython 4.0 on Windows/Mac/Linux
# - wxPython 3.0 on Windows/Mac
# - wxPython 2.8 on Linux
# - CEF Python v66.0+

import wx
from cefpython3 import cefpython as cef
import platform
import sys
import os
import win32api

# Platforms
WINDOWS = (platform.system() == "Windows")
LINUX = (platform.system() == "Linux")
MAC = (platform.system() == "Darwin")

if MAC:
    try:
        # noinspection PyUnresolvedReferences
        from AppKit import NSApp
    except ImportError:
        print("[wxpython.py] Error: PyObjC package is missing, "
              "cannot fix Issue #371")
        print("[wxpython.py] To install PyObjC type: "
              "pip install -U pyobjc")
        sys.exit(1)

# Configuration
WIDTH = 900
HEIGHT = 640

# Globals
g_count_windows = 0


def main():
    check_versions()
    sys.excepthook = cef.ExceptHook  # To shutdown all CEF processes on error
    settings = {}
    if MAC:
        # Issue #442 requires enabling message pump on Mac
        # and calling message loop work in a timer both at
        # the same time. This is an incorrect approach
        # and only a temporary fix.
        settings["external_message_pump"] = True
    if WINDOWS:
        # noinspection PyUnresolvedReferences, PyArgumentList
        cef.DpiAware.EnableHighDpiSupport()

    #change UserAgent
    # settings['user_agent'] = "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/532.5 (KHTML, like Gecko) Chrome/4.0.249.0 Safari/532.5"
    # settings['user_agent'] = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.7 (KHTML, like Gecko) Chrome/16.0.912.36 Safari/535.7"

    # switches = {
    #     "enable-media-stream": "",
    #     "proxy-server": "socks5://127.0.0.1:8888",
    #     "disable-gpu": "",
    #     "disable-image-loading",
    # }

    switches = {
        "enable-media-stream": "",
        "proxy-server": "",
        "disable-gpu": "",
        "disable-image-loading": "",
    }

    cef.Initialize(settings=settings, switches=switches)
    # cef.Initialize(settings=settings)
    app = CefApp(False)
    app.MainLoop()
    del app  # Must destroy before calling Shutdown
    if not MAC:
        # On Mac shutdown is called in OnClose
        cef.Shutdown()


def check_versions():
    print("[wxpython.py] CEF Python {ver}".format(ver=cef.__version__))
    print("[wxpython.py] Python {ver} {arch}".format(
            ver=platform.python_version(), arch=platform.architecture()[0]))
    print("[wxpython.py] wxPython {ver}".format(ver=wx.version()))
    # CEF Python version requirement
    assert cef.__version__ >= "66.0", "CEF Python v66.0+ required to run this"


def scale_window_size_for_high_dpi(width, height):
    """Scale window size for high DPI devices. This func can be
    called on all operating systems, but scales only for Windows.
    If scaled value is bigger than the work area on the display
    then it will be reduced."""
    if not WINDOWS:
        print("NOT WINDOWS")
        return width, height
    (_, _, max_width, max_height) = wx.GetClientDisplayRect().Get()
    # noinspection PyUnresolvedReferences
    (width, height) = cef.DpiAware.Scale((width, height))
    if width > max_width:
        width = max_width
    if height > max_height:
        height = max_height
    return width, height


class MainFrame(wx.Frame):

    def __init__(self):
        self.browser = None

        # Must ignore X11 errors like 'BadWindow' and others by
        # installing X11 error handlers. This must be done after
        # wx was intialized.
        if LINUX:
            cef.WindowUtils.InstallX11ErrorHandlers()

        global g_count_windows
        g_count_windows += 1

        if WINDOWS:

            dm = win32api.EnumDisplaySettings(None, 0)
            dm.PelsHeight = 768
            dm.PelsWidth = 1366
            dm.BitsPerPel = 32
            dm.DisplayFixedOutput = 0
            win32api.ChangeDisplaySettings(dm, 0)




            # noinspection PyUnresolvedReferences, PyArgumentList
            cef.DpiAware.EnableHighDpiSupport()
            print("[wxpython.py] System DPI settings: %s"
                  % str(cef.DpiAware.GetSystemDpi()))
            # print(cef.DpiAware.Scale((1300, 1200)))
        if hasattr(wx, "GetDisplayPPI"):
            print("[wxpython.py] wx.GetDisplayPPI = %s" % wx.GetDisplayPPI())
        print("[wxpython.py] wx.GetDisplaySize = %s" % wx.GetDisplaySize())

        print("[wxpython.py] MainFrame declared size: %s"
              % str((WIDTH, HEIGHT)))
        size = scale_window_size_for_high_dpi(WIDTH, HEIGHT)
        print("[wxpython.py] MainFrame DPI scaled size: %s" % str(size))

        wx.Frame.__init__(self, parent=None, id=wx.ID_ANY,
                          title='wxPython example', size=size)
        # wxPython will set a smaller size when it is bigger
        # than desktop size.
        print("[wxpython.py] MainFrame actual size: %s" % self.GetSize())

        self.setup_icon()
        self.create_menu()
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        # Set wx.WANTS_CHARS style for the keyboard to work.
        # This style also needs to be set for all parent controls.
        self.browser_panel = wx.Panel(self, style=wx.WANTS_CHARS)
        self.browser_panel.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        self.browser_panel.Bind(wx.EVT_SIZE, self.OnSize)

        if MAC:
            # Make the content view for the window have a layer.
            # This will make all sub-views have layers. This is
            # necessary to ensure correct layer ordering of all
            # child views and their layers. This fixes Window
            # glitchiness during initial loading on Mac (Issue #371).
            NSApp.windows()[0].contentView().setWantsLayer_(True)

        if LINUX:
            # On Linux must show before embedding browser, so that handle
            # is available (Issue #347).
            self.Show()
            # In wxPython 3.0 and wxPython 4.0 on Linux handle is
            # still not yet available, so must delay embedding browser
            # (Issue #349).
            if wx.version().startswith("3.") or wx.version().startswith("4."):
                wx.CallLater(100, self.embed_browser)
            else:
                # This works fine in wxPython 2.8 on Linux
                self.embed_browser()
        else:
            self.embed_browser()
            self.Show()

    def setup_icon(self):
        icon_file = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                 "resources", "wxpython.png")
        # wx.IconFromBitmap is not available on Linux in wxPython 3.0/4.0
        if os.path.exists(icon_file) and hasattr(wx, "IconFromBitmap"):
            icon = wx.IconFromBitmap(wx.Bitmap(icon_file, wx.BITMAP_TYPE_PNG))
            self.SetIcon(icon)

    def create_menu(self):
        filemenu = wx.Menu()
        filemenu.Append(1, "Some option")
        filemenu.Append(2, "Another option")
        menubar = wx.MenuBar()
        menubar.Append(filemenu, "&File")
        self.SetMenuBar(menubar)

    def embed_browser(self):
        window_info = cef.WindowInfo()
        (width, height) = self.browser_panel.GetClientSize().Get()
        assert self.browser_panel.GetHandle(), "Window handle not available"
        window_info.SetAsChild(self.browser_panel.GetHandle(),
                               [0, 0, width, height])

        # cef.SetGlobalClientHandler(RequestHandler())

        # self.browser = cef.CreateBrowserSync(window_info, url="https://www.baidu.com/s?wd=hello%20kitty&rsv_spt=1&rsv_iqid=0xb548f8e100010f06&issp=1&f=8&rsv_bp=0&rsv_idx=2&ie=utf-8&tn=baiduhome_pg&rsv_enter=1&rsv_sug3=13&rsv_sug1=12&rsv_sug7=100&rsv_sug2=0&inputT=4106&rsv_sug4=4106")
        self.browser = cef.CreateBrowserSync(window_info, url="http://cn.screenresolution.org/")
        # self.browser = cef.CreateBrowserSync(window_info, url="about:blank")

        self.browser.SetClientHandler(RequestHandler())

        # google_script_str = ""
        # google_script_str += "<html><head><title>Test</title></head><body bgcolor='white'>"
        # google_script_str += "<script>alert(document.referrer)</script>"
        # google_script_str += "<script async src='http://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js'></script>"
        # google_script_str += "<ins class='adsbygoogle'style='display:inline-block;width:728px;height:90px'data-ad-client='ca-pub-6201639787321531'data-ad-slot='2440155965'></ins>"
        # google_script_str += "<script>(adsbygoogle = window.adsbygoogle || []).push({});</script>"
        # google_script_str += "</body></html>"
        # self.browser.GetFocusedFrame().LoadString(google_script_str, "http://www.baidu.com")
        self.browser.SetClientHandler(FocusHandler())
        self.browser.SetClientHandler(LoadHandler())

        # print(self.browser.GetZoomLevel())
        #         # # self.browser.SetZoomLevel(self.browser.GetZoomLevel() - 99.0)
        #         # self.browser.SetZoomLevel(125%)
        #         # # cef.PyBrowser.SetZoomLevel()
        #         # print(self.browser.GetZoomLevel())

        # self.browser.SetClientHandler(LifespanHandler())

        # self.browser.clientCallbacks["OnContextCreated"] = V8ContextHandler2.OnContextCreated
        # self.browser.SetClientHandler(V8ContextHandler())


        # cef.Request

    def OnSetFocus(self, _):
        if not self.browser:
            return
        if WINDOWS:
            cef.WindowUtils.OnSetFocus(self.browser_panel.GetHandle(),
                                       0, 0, 0)
        self.browser.SetFocus(True)

    def OnSize(self, _):
        if not self.browser:
            return
        if WINDOWS:
            cef.WindowUtils.OnSize(self.browser_panel.GetHandle(),
                                   0, 0, 0)
        elif LINUX:
            (x, y) = (0, 0)
            (width, height) = self.browser_panel.GetSize().Get()
            self.browser.SetBounds(x, y, width, height)
        self.browser.NotifyMoveOrResizeStarted()

    def OnClose(self, event):
        print("[wxpython.py] OnClose called")
        if not self.browser:
            # May already be closing, may be called multiple times on Mac
            return

        if MAC:
            # On Mac things work differently, other steps are required
            self.browser.CloseBrowser()
            self.clear_browser_references()
            self.Destroy()
            global g_count_windows
            g_count_windows -= 1
            if g_count_windows == 0:
                cef.Shutdown()
                wx.GetApp().ExitMainLoop()
                # Call _exit otherwise app exits with code 255 (Issue #162).
                # noinspection PyProtectedMember
                os._exit(0)
        else:
            # Calling browser.CloseBrowser() and/or self.Destroy()
            # in OnClose may cause app crash on some paltforms in
            # some use cases, details in Issue #107.
            self.browser.ParentWindowWillClose()
            event.Skip()
            self.clear_browser_references()

    def clear_browser_references(self):
        # Clear browser references that you keep anywhere in your
        # code. All references must be cleared for CEF to shutdown cleanly.
        self.browser = None


class FocusHandler(object):
    def OnGotFocus(self, browser, **_):
        # Temporary fix for focus issues on Linux (Issue #284).
        if LINUX:
            print("[wxpython.py] FocusHandler.OnGotFocus:"
                  " keyboard focus fix (Issue #284)")
            browser.SetFocus(True)

class LoadHandler(object):

    def OnLoadStart(self, browser, frame):
        # change the zoomlevel of browser.
        # print(browser.GetZoomLevel())
        browser.SetZoomLevel(browser.GetZoomLevel() - 99.0)
        # print(browser.GetZoomLevel())

    def OnLoadingStateChange(self, browser, is_loading, **_):
        pass
        # if not is_loading:
        #     cef.PostDelayedTask(cef.TID_UI, 15000, reload_page, browser)
        #     print("www.baidu.com had loaded completely.")


class RequestHandler(object):

    def OnBeforeResourceLoad(self, frame, request, **_):
        # request_ = request.CreateRequest()
        # request_.SetHeaderMap({'Referer':'http://www.zaker.com', 'X-Forwarded-For':'33.93.233.36', 'X-Client-IP':'33.93.233.36'})
        # if frame.IsMain():
            # cef.PostTask(cef.TID_UI, set_header_map, request)
        request.SetHeaderMultimap([('Referer', 'http://www.zaker.com'), ('X-Forwarded-For', '33.93.233.36'),
                                       ('X-Client-IP', '33.93.233.36')])
        # return True

# class LifespanHandler(object):
#
#     def _OnAfterCreated(self, browser):
#
#         print(browser.GetZoomLevel())
#         # browser.SetZoomLevel(self.browser.GetZoomLevel() - 99.0)
#         browser.SetZoomLevel(99.0)
#         print(browser.GetZoomLevel())


# class V8ContextHandler2(object):
#
#     def OnContextCreated(browser, frame):
#         browser.ExecuteJavascript("""Object.defineProperty(window.screen, 'height', {"
#              "    get: function() {"
#               "        return 600;"
#               "    }"
#               "});"
#              "Object.defineProperty(window.screen, 'width', {"
#              "    get: function() {"
#              "        return 800;"
#              "    }"
#              "});""")
#
#         # cef.PostTask(cef.TID_RENDERER, change_screen_solution, browser)



def reload_page(browser):
    google_script_str = ""
    google_script_str += "<html><head><title>Test</title></head><body bgcolor='white'>"
    google_script_str += "<script>alert(document.referrer)</script>"
    google_script_str += "<script async src='http://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js'></script>"
    google_script_str += "<ins class='adsbygoogle'style='display:inline-block;width:728px;height:90px'data-ad-client='ca-pub-6201639787321531'data-ad-slot='2440155965'></ins>"
    google_script_str += "<script>(adsbygoogle = window.adsbygoogle || []).push({});</script>"
    google_script_str += "</body></html>"
    browser.GetFocusedFrame().LoadString(google_script_str, "http://www.baidu.com")

    # browser.Reload()

def change_screen_solution(browser):
    browser.ExecuteJavascript("""Object.defineProperty(window.screen, 'height', {"
     "    get: function() {"
      "        return 600;"
      "    }"
      "});"
     "Object.defineProperty(window.screen, 'width', {"
     "    get: function() {"
     "        return 800;"
     "    }"
     "});""")

# def set_header_map(request):
#     print(request)
#     print("SetHeaderMap begin!")
#
#     # request.SetHeaderMap({'Referer': 'http://www.zaker.com', 'X-Forwarded-For': '33.93.233.36', 'X-Client-IP': '33.93.233.36'})
#     request.SetHeaderMultimap([('Referer', 'http://www.zaker.com'), ('X-Forwarded-For', '33.93.233.36'), ('X-Client-IP', '33.93.233.36')])
#     print(request)
#     print("SetHeaderMap end!")


class CefApp(wx.App):

    def __init__(self, redirect):
        self.timer = None
        self.timer_id = 1
        self.is_initialized = False
        super(CefApp, self).__init__(redirect=redirect)

    def OnPreInit(self):
        super(CefApp, self).OnPreInit()
        # On Mac with wxPython 4.0 the OnInit() event never gets
        # called. Doing wx window creation in OnPreInit() seems to
        # resolve the problem (Issue #350).
        if MAC and wx.version().startswith("4."):
            print("[wxpython.py] OnPreInit: initialize here"
                  " (wxPython 4.0 fix)")
            self.initialize()

    def OnInit(self):
        self.initialize()
        return True

    def initialize(self):
        if self.is_initialized:
            return
        self.is_initialized = True
        self.create_timer()
        frame = MainFrame()
        self.SetTopWindow(frame)
        frame.Show()

    def create_timer(self):
        # See also "Making a render loop":
        # http://wiki.wxwidgets.org/Making_a_render_loop
        # Another way would be to use EVT_IDLE in MainFrame.
        self.timer = wx.Timer(self, self.timer_id)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.timer.Start(10)  # 10ms timer

    def on_timer(self, _):
        cef.MessageLoopWork()

    def OnExit(self):
        self.timer.Stop()
        return 0


if __name__ == '__main__':
    main()
