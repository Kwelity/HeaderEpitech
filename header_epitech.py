import sublime
import sublime_plugin
import os
import re
import datetime


class Comment:
    begin  = None
    middle = None
    end    = None

    def __init__(self):
        pass


class Language:
    name      = None
    extension = None
    comment   = Comment()

    def __init__(self):
        pass


class TransformXmlToLanguages(object):
    __currentNode__   = None
    __languagesList__ = None

    def __init__(self):
        super(TransformXmlToLanguages, self).__init__()
        self.readXml()

    def readXml(self):
        from xml.dom.minidom import parse
        self.doc = parse(sublime.packages_path()+'/HeaderEpitech/languages.xml')

    def getRootElement(self):
        if self.__currentNode__ is None:
            self.__currentNode__ = self.doc.documentElement
        return self.__currentNode__

    def getLanguages(self):
        if self.__languagesList__ is not None:
            return self.__languagesList__
        self.__languagesList__ = []
        for languages in self.getRootElement().getElementsByTagName("language"):
            if languages.nodeType == languages.ELEMENT_NODE:
                l = Language()
                try:
                    l.name      = self.getText(languages.getElementsByTagName("name")[0])
                    l.extension = self.getText(languages.getElementsByTagName("extension")[0])
                    l.comment   = self.getComment(languages.getElementsByTagName("comment")[0])
                except:
                    pass
                self.__languagesList__.append(l)
        return self.__languagesList__

    def getComment(self, node):
        comment = Comment()
        try:
            comment.begin  = self.getText(node.getElementsByTagName("begin")[0])
            comment.middle = self.getText(node.getElementsByTagName("middle")[0])
            comment.end    = self.getText(node.getElementsByTagName("end")[0])
        except:
            print('Un des TAGS suivant est manquants : begin, middle, end')
        return comment

    def getText(self, node):
        return node.childNodes[0].nodeValue


class Header(object):

    __language__ = None
    __header__   = None

    mapHeader = sublime.packages_path()+'/HeaderEpitech/mapHeader.txt'

    description = None
    file_name   = None
    file_path   = None
    name        = None
    fist_name   = None
    login       = None
    create_date = None
    save_date   = None

    def __init__(self, edit, comment, file_info):
        settings = sublime.load_settings('header_epitech.sublime-settings')
        self.description = str(comment)
        self.file_path, self.file_extension = os.path.splitext(str(file_info))
        self.file_name = os.path.basename(str(file_info))
        if not self.file_extension or self.file_extension == ".am":
            if self.file_name == "Makefile" or self.file_name == "Makefile.am":
                self.file_extension = "Makefile"
            else:
                self.file_extension = "Default"

        self.first_name   = str(settings.get("first_name"))
        self.name         = str(settings.get("name"))
        self.login        = str(settings.get("login"))
        self.create_date  = datetime.datetime.now().ctime()
        self.save_date    = self.create_date
        self.__language__ = self.getFileLanguage(edit)
        self.getMap()
        self.generateHeader()

    def getFileLanguage(self, edit):
        ret = None
        x   = TransformXmlToLanguages()
        for language in x.getLanguages():
            if language.extension == self.file_extension:
                ret = language
        if ret is None:
            ret = x.getLanguages()[0]
        return ret

    def getMap(self):
        try:
            self.__header__ = open(self.mapHeader).read()
        except FileNotFoundError:
            # Have to do it again, dunno why.
            self.mapHeader  = sublime.packages_path()+'/HeaderEpitech/mapHeader.txt'
            self.__header__ = open(self.mapHeader).read()

    def generateHeader(self):
        if (self.__language__ is not None):
            for attr in self.__dict__:
                strToReplace = '{$' + attr + '}'
                if (isinstance(self.__dict__.get(attr), str)):
                    self.__header__ = self.__header__.replace(strToReplace, self.__dict__.get(attr))
            self.__header__ = self.__header__.replace('{$comment_begin}', self.__language__.comment.begin)
            self.__header__ = self.__header__.replace('{$comment_middle}', self.__language__.comment.middle)
            self.__header__ = self.__header__.replace('{$comment_end}', self.__language__.comment.end)


class HeaderEpitechModifiedCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        settings      = sublime.load_settings("header_epitech.sublime-settings")
        first_name    = settings.get("first_name")
        name          = settings.get("name")
        modified_date = self.view.find('Last update', 0)
        if modified_date:
            line          = self.view.line(modified_date)
            now           = datetime.datetime.now().ctime()
            string_line   = self.view.substr(line)
            before_pos    = string_line.find('Last update')
            before_string = ''
            if before_pos >= 0:
                before_string = string_line[0:before_pos]
            self.view.replace(edit, line, before_string + 'Last update ' + now + " " + first_name + " " + name)


class HeaderEpitechShowCommandLine(sublime_plugin.WindowCommand):

    def run(self):
        view      = sublime.Window.active_view(sublime.active_window())
        file_name = os.path.splitext(os.path.basename(view.file_name()))[0]
        self.window.show_input_panel("Header description:", file_name if file_name else "", self.on_done, None, None)

    def on_done(self, text):
        try:
            comment = text
            self.window.active_view().run_command("header_epitech", {"comment": comment})
        except ValueError:
            pass


class HeaderEpitechCommand(sublime_plugin.TextCommand):

    def run(self, edit, comment):
        file_path = self.view.file_name()
        header    = Header(edit, comment, file_path)
        self.displayHeader(edit, header)

    def displayHeader(self, edit, header):
        self.view.insert(edit, 0, header.__header__)


class HeaderEpitechEvent(sublime_plugin.EventListener):

    def on_pre_save(self, view):
        settings     = sublime.load_settings("header_epitech.sublime-settings")
        ignore_files = settings.get('ignore_files')
        current_file = os.path.basename(view.file_name())
        for f in ignore_files:
            pattern = re.compile(f)
            if pattern.match(current_file):
                return

        view.run_command('header_epitech_modified')
