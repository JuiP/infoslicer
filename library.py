# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gtk
from threading import Timer
from datetime import datetime
from gettext import gettext as _

from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.toggletoolbutton import ToggleToolButton
from sugar.activity.activity import ActivityToolbox
from sugar.graphics.toolcombobox import ToolComboBox
from sugar.graphics.icon import Icon
import sugar.graphics.style as style

import net
import book
from GUI_Components.Compound_Widgets.toolbar import WidgetItem
from GUI_Components.Compound_Widgets.bookview import BookView
from GUI_Components.Compound_Widgets.Reading_View import Reading_View
from Processing.Package_Creator import Package_Creator

class View(gtk.EventBox):
    def sync(self):
        self.wiki.sync()
        self.custom.sync()

    def __init__(self, set_edit_sensitive):
        gtk.EventBox.__init__(self)
        self._set_edit_sensitive = set_edit_sensitive

        # books

        books = gtk.VBox()
        books.set_size_request(gtk.gdk.screen_width()/4, -1)
        self.wiki = BookView(book.wiki,
                _('Wiki'), _('Wiki articles'), False)
        books.pack_start(self.wiki)
        self.custom = BookView(book.custom,
                _('Custom'), _('Custom articles'), True)
        books.pack_start(self.custom)

        # stubs for empty articles

        def create_stub(icon_name, head_text, tail_text):
            head_label = gtk.Label(head_text)
            head_label_a = gtk.Alignment(0.5, 1, 0, 0)
            head_label_a.add(head_label)
            icon = Icon(icon_name=icon_name,
                    icon_size=gtk.ICON_SIZE_LARGE_TOOLBAR)
            tail_label = gtk.Label(tail_text)
            tail_label_a = gtk.Alignment(0.5, 0, 0, 0)
            tail_label_a.add(tail_label)
            stub = gtk.VBox()
            stub.pack_start(head_label_a)
            stub.pack_start(icon, False)
            stub.pack_start(tail_label_a)
            return stub

        wiki_stub = create_stub('white-search',
                _('To download Wiki article\ntype "Article name" and click'),
                _('button on top "Library" panel'))
        custom_stub = create_stub('add',
                _('To create custom article click'),
                _('button on left "Custom" panel'))

        # articles viewers

        wiki_widget = Reading_View()
        wiki = gtk.Notebook()
        wiki.props.show_border = False
        wiki.props.show_tabs = False
        wiki.append_page(wiki_widget)
        wiki.append_page(wiki_stub)

        custom_widget = Reading_View()
        custom = gtk.Notebook()
        custom.props.show_border = False
        custom.props.show_tabs = False
        custom.append_page(custom_widget)
        custom.append_page(custom_stub)
        custom.set_size_request(gtk.gdk.screen_width()/4*3/2, -1)

        # workspace

        articles = gtk.HBox()
        articles.pack_start(wiki)
        articles.pack_start(gtk.VSeparator(), False)
        articles.pack_start(custom, False)

        self.progress = gtk.Label()
        self.progress.set_size_request(-1, style.SMALL_ICON_SIZE+4)
        progress_box = gtk.VBox()
        progress_box.pack_start(articles)
        progress_box.pack_start(gtk.HSeparator(), False)
        progress_box.pack_start(self.progress, False)

        workspace = gtk.HBox()
        workspace.pack_start(books, False)
        workspace.pack_start(gtk.VSeparator(), False)
        workspace.pack_start(progress_box)
        workspace.show_all()

        self.add(workspace)

        # init components

        book.wiki.connect('article-selected', self._article_selected_cb,
                wiki, wiki_widget)
        book.wiki.connect('article-deleted', self._article_deleted_cb, wiki)
        book.custom.connect('article-selected', self._article_selected_cb,
                custom, custom_widget)
        book.custom.connect('article-deleted', self._article_deleted_cb, custom)

        self._edit_sensitive = 0
        self._set_edit_sensitive(False)

        if not book.wiki.article:
            wiki.set_current_page(1)
        else:
            self._article_selected_cb(None, book.wiki.article,
                    wiki, wiki_widget)

        if not book.custom.article:
            custom.set_current_page(1)
        else:
            self._article_selected_cb(None, book.custom.article,
                    custom, custom_widget)

    def _article_selected_cb(self, book, article, notebook, article_widget):
        notebook.set_current_page(0)
        article_widget.textbox.set_article(article)

        self._edit_sensitive += 1
        if self._edit_sensitive == 2:
            self._set_edit_sensitive(True)

    def _article_deleted_cb(self, abook, article, notebook):
        if abook.map:
            return
        notebook.set_current_page(1)
        self._edit_sensitive -= 1
        self._set_edit_sensitive(False)

class Toolbar(gtk.Toolbar):
    def __init__(self, library):
        gtk.Toolbar.__init__(self)
        self.library = library

        self.wikimenu = ToolComboBox(label_text=_('Get article from:'))
        for i in sorted(WIKI.keys()):
            self.wikimenu.combo.append_item(WIKI[i], i)
        self.wikimenu.combo.set_active(0)
        self.insert(self.wikimenu, -1)
        self.wikimenu.show()

        self.searchentry = gtk.Entry()
        self.searchentry.set_size_request(int(gtk.gdk.screen_width() / 4), -1)
        self.searchentry.set_text(_("Article name"))
        self.searchentry.select_region(0, -1)
        self.searchentry.connect('activate', self._search_activate_cb)
        searchentry_item = WidgetItem(self.searchentry)
        self.insert(searchentry_item, -1)
        searchentry_item.show()

        self.searchbutton = ToolButton('white-search',
                tooltip=_('Find article'))
        self.searchbutton.connect('clicked', self._search_clicked_cb)
        self.insert(self.searchbutton, -1)
        self.searchbutton.show()

        separator = gtk.SeparatorToolItem()
        self.insert(separator, -1)
        separator.show()

        publish = ToolButton('filesave', tooltip=_('Publish selected articles'))
        publish.connect("clicked", self._publish_clicked_cb)
        self.insert(publish, -1)
        publish.show()

        self.connect('map', self._map_cb)

    def _publish_clicked_cb(self):
        book.custom.sync()
        Package_Creator(book.custom.article,
                datetime.strftime(datetime.now(), '%F %T'))

    def _map_cb(self, widget):
        self.searchentry.grab_focus()

    def _search_activate_cb(self, widget):
        self.searchbutton.emit("clicked")

    def _search_clicked_cb(self, widget):
        title = self.searchentry.get_text()
        wiki = self.wikimenu.combo.props.value

        if not title:
            return

        if book.wiki.find('%s (from %s)' % (title, wiki))[0]:
            self.library.progress.set_label(_('"%s" article already exists') % title)
            Timer(10, self._clear_progress).start()
        else:
            Timer(0, self._download, [title, wiki]).start()

    def _download(self, title, wiki):
        net.download_wiki_article(title, wiki, self.library.progress)
        Timer(10, self._clear_progress).start()

    def _clear_progress(self):
        self.library.progress.set_label('')

WIKI = { _("English Wikipedia")         : "en.wikipedia.org", 
         _("Simple English Wikipedia")  : "simple.wikipedia.org", 
         _("German Wikipedia")          : "de.wikipedia.org" }