# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys
import os
import gettext
import subprocess
import time

from PyQt4.QtCore import Qt, SIGNAL, QUrl
from PyQt4.QtGui import QWidget, QPushButton, QIcon, QLineEdit, QHBoxLayout, QMessageBox, QGridLayout, QImageReader
from PyQt4.QtWebKit import QWebPage


from PyKDE4.kdeui import KIconLoader
from PyKDE4.nepomuk import Nepomuk
from PyKDE4.soprano import Soprano
from lglobals import DO_NOT_USE_NEPOMUK, PROGRAM_NAME, DEFAULT_ENGINE, PROGRAM_HTML_POWERED, PROGRAM_URL

from cldataformat import cDataFormat
from clsparql import cSparqlBuilder, cResource, NOCR, NOC
from chelper import cWebView, hackQueryParser
from lfunctions import dialogInputBox, dialogList, dialogTextInputBox, lindex, vartype, toVariant, fileExists
from lglobals import INTERNAL_RESOURCE, SLEEP_AFTER_UPDATE, SLEEP_NO_SLEEP, ONTOLOGY_SYMBOL, ONTOLOGY_SYMBOL_CONTACT, ONTOLOGY_MUSIC_ALBUM_COVER, ONTOLOGY_LINK

_ = gettext.gettext


#
# Nepoogle class
#
class Nepoogle(QWidget):
    cache = []
    cacheViewer = []
    currUri = None
    clearResourceManagerCache = True
    keyModifiers = Qt.NoModifier
    model = None
    navigationData = []
    pendingQuery = False
    queriesIndex = -1
    queryMethod = None
    renderedCache = ''
    renderedRows = 0
    renderSize = 50
    resultData = []
    resultStructure = []
    resultTime = None
    screenHeight = 600
    screenWidth = 800
    sparql = None
    textToFind = ""
    verboseMode = False
    warningsList = []

    iconDelete = KIconLoader().iconPath('edit-delete', KIconLoader.NoGroup)
    iconDocumentInfo = KIconLoader().iconPath('documentinfo', KIconLoader.NoGroup)
    iconDocumentProp = KIconLoader().iconPath('document-properties', KIconLoader.NoGroup)
    iconFileManager = KIconLoader().iconPath('system-file-manager', KIconLoader.NoGroup)
    iconKonqueror = KIconLoader().iconPath('konqueror', KIconLoader.NoGroup)
    iconNavigateFirst = KIconLoader().iconPath('go-first', KIconLoader.NoGroup)
    iconNavigateLast = KIconLoader().iconPath('go-last', KIconLoader.NoGroup)
    iconNavigateNext = KIconLoader().iconPath('go-next', KIconLoader.NoGroup)
    iconNavigatePrevious = KIconLoader().iconPath('go-previous', KIconLoader.NoGroup)
    iconProcessIdle = KIconLoader().iconPath('process-idle', KIconLoader.NoGroup)
    iconSystemRun = KIconLoader().iconPath('system-run', KIconLoader.NoGroup)
    iconSystemSearch = KIconLoader().iconPath('system-search', KIconLoader.NoGroup)

    htmlTableHeader = "<table style=\"text-align:left; width: 100%%;\" " \
                      "border=\"%(border)s\" cellpadding=\"%(cellpadding)s\" cellspacing=\"0\">" \
                      "<tbody>\n"
    htmlTableFooter = "</tbody></table>\n"

    def __init__(self, parent=None, searchString='', verboseMode=False, screenRect=None):
        super(Nepoogle, self).__init__(parent)

        if (screenRect is not None):
            self.screenHeight = screenRect.height()
            self.screenWidth = screenRect.width()

        self.verboseMode = verboseMode

        if DO_NOT_USE_NEPOMUK:
            self.model = Soprano.Client.DBusModel('org.kde.NepomukStorage', '/org/soprano/Server/models/main')

        else:
            self.model = Nepomuk.ResourceManager.instance().mainModel()

        self.setWindowTitle(PROGRAM_NAME)
        self.setWindowIcon(QIcon(KIconLoader().loadIcon('nepomuk',  KIconLoader.NoGroup,  KIconLoader.SizeSmall)))

        self.leSearch = QLineEdit(self)
        self.leSearch.selectOnEntry = True

        self.pbBackward = QPushButton(self)
        self.pbBackward.setIcon(QIcon(KIconLoader().loadIcon('go-previous',  KIconLoader.NoGroup,  KIconLoader.SizeSmall)))
        self.connect(self.pbBackward, SIGNAL("clicked()"), self.goBackward)

        self.pbForward = QPushButton(self)
        self.pbForward.setIcon(QIcon(KIconLoader().loadIcon('go-next',  KIconLoader.NoGroup,  KIconLoader.SizeSmall)))
        self.connect(self.pbForward, SIGNAL("clicked()"), self.goForward)

        self.pbHelp = QPushButton(self)
        self.pbHelp.setIcon(QIcon(KIconLoader().loadIcon('help-contents',  KIconLoader.NoGroup,  KIconLoader.SizeSmall)))
        self.connect(self.pbHelp, SIGNAL("clicked()"), self.showHelp)

        self.hbl = QHBoxLayout()
        self.hbl.setSpacing(1)
        self.hbl.addWidget(self.pbBackward)
        self.hbl.addWidget(self.pbForward)
        self.hbl.addWidget(self.leSearch)
        self.hbl.addWidget(self.pbHelp)

        self.wvOutput = cWebView(self)
        self.connect(self.wvOutput, SIGNAL("linkClicked(const QUrl&)"), self.linkClicked)
        self.connect(self.wvOutput, SIGNAL("loadStarted()"), self.loadStarted)
        self.connect(self.wvOutput, SIGNAL("loadFinished(bool)"), self.loadFinished)
        self.connect(self.wvOutput, SIGNAL("loadProgress(int)"), self.loadProgress)

        # This action has no changes.
        self.actionOpenLink = self.wvOutput.pageAction(QWebPage.OpenLink)
        self.connect(self.actionOpenLink, SIGNAL("triggered(bool)"), self.openLink)

        # DownloadLinkToDisk renamed and used as OpenLinkInNewWindow
        self.actionDownloadLinkToDisk = self.wvOutput.pageAction(QWebPage.DownloadLinkToDisk)
        self.actionDownloadLinkToDisk.setText(_("Open in New Window"))

        # Invisible OpenLinkInNewWindow.
        self.actionOpenLinkInNewWindow = self.wvOutput.pageAction(QWebPage.OpenLinkInNewWindow)
        self.actionOpenLinkInNewWindow.setVisible(False)

        # Invisible OpenImageInNewWindow.
        self.actionOpenImageInNewWindow = self.wvOutput.pageAction(QWebPage.OpenImageInNewWindow)
        self.actionOpenImageInNewWindow.setVisible(False)

        self.connect(self.wvOutput.page(), SIGNAL("downloadRequested(const QNetworkRequest&)"), self.downloadRequested)
        self.connect(self.wvOutput.page(), SIGNAL("unsupportedContent(QNetworkReply*)"), self.unsupportedContent)
        self.wvOutput.page().setForwardUnsupportedContent(True)

        self.grid = QGridLayout()
        self.grid.setSpacing(10)
        self.grid.addLayout(self.hbl, 1, 1)
        self.grid.addWidget(self.wvOutput, 2, 1, 5, 1)

        self.setLayout(self.grid)

        self.resize(int((self.screenWidth) / 2), self.screenHeight - 50)

        if searchString == '':
            self.leSearch.setText('Type search here')

        else:
            self.leSearch.setText(searchString)

        self.leSearch.setSelection(0, 999)
        self.leSearch.setFocus()

        if searchString == '':
            self.execQuery('--help')

    def downloadRequested(self, request):
        url = request.url().toString()
        if url != "":
            if url[:9] == 'nepomuk:/':
                pass

            elif url[:7] == 'query:/':
                url = url[7:]

            elif url[:6] == "file:/":
                subprocess.Popen(["kioclient", "exec", url])
                url = ''

            else:
                url = ''

            if url != '':
                print(url)
                subprocess.Popen([PROGRAM_URL, "--gui", url])

    def unsupportedContent(self, request):
        QMessageBox.warning(self, '%s - %s' % (PROGRAM_NAME, _("warning")), "Option not available yet.")

    def openLink(self, checked):
        url = self.wvOutput.page().currentFrame().requestedUrl()
        if url.toString() != "":
            self.linkClicked(url, True)

    def openLinkInNewWindow(self, checked):
        url = self.wvOutput.page().currentFrame().requestedUrl().toString()
        if url != "":
            print(url)
            if url[:9] == 'nepomuk:/':
                pass

            elif url[:7] == 'query:/':
                url = url[7:]

            elif url[:6] == "file:/":
                subprocess.Popen(["kioclient", "exec", url])
                url = ''

            else:
                url = ''

            if url != '':
                subprocess.Popen([PROGRAM_URL, "--gui", url])

    def loadFinished(self, ok):
        self.repaint()
        if self.pendingQuery:
            self.execQuery()

        self.textToFind = ""

    def loadProgress(self, progress):
        pass

    def loadStarted(self):
        pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.pendingQuery = True
            self.queryMethod = "manual"
            self.wvOutput.setHtml('<html><body><h3>Searching... <img src="file://%s"></h3></body></html>'
                                  % self.iconProcessIdle)

        elif event.key() == Qt.Key_F5:
            self.pendingQuery = True
            self.queryMethod = "refresh"
            self.wvOutput.setHtml('<html><body><h3>Searching... <img src="file://%s"></h3></body></html>'
                                  % self.iconProcessIdle)

        elif event.key() == Qt.Key_F3:
            self.findText(True)

        elif event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_PageUp:
                self.linkClicked(QUrl("navigate:/first"))

            elif event.key() == Qt.Key_PageDown:
                self.linkClicked(QUrl("navigate:/last"))

            elif event.key() == Qt.Key_Left:
                self.linkClicked(QUrl("navigate:/previous"))

            elif event.key() == Qt.Key_Right:
                self.linkClicked(QUrl("navigate:/next"))

            elif event.key() == Qt.Key_Delete:
                uri = self.leSearch.text().strip()
                if uri[:13] == 'nepomuk:/res/':
                    self.linkClicked(QUrl("remove:/" + uri))

            elif event.key() == Qt.Key_F:
                self.findText()

            elif event.key() == Qt.Key_Plus:
                self.addProperty()

        elif event.key() == Qt.Key_Escape:
            self.close()

        self.keyModifiers = event.modifiers()

    def keyReleaseEvent(self, event):
        self.keyModifiers = event.modifiers()

    def findText(self, again=False):
        if (not again or (self.textToFind == "")):
            self.textToFind = dialogInputBox(_("Text to find:"))

        self.wvOutput.findText("", QWebPage.HighlightAllOccurrences)
        if self.wvOutput.findText(self.textToFind, QWebPage.FindWrapsAroundDocument):
            self.wvOutput.findText(self.textToFind, QWebPage.HighlightAllOccurrences)

        else:
            QMessageBox.warning(self, "%s - %s" % (PROGRAM_NAME, _("warning")), _("Text not found."))

    def linkClicked(self, url, forceExec=False):
        url = url.toString()
        print(url)

        if url[:11] == "autocover:/":
            uri = url[11:]

            oDataFormat = cDataFormat("", self.model, self.screenWidth)

            try:
                coverUrl = oDataFormat.gtCoverUrl(mainResource, "")

            except:
                coverUrl = ""

            if coverUrl == "":
                QMessageBox.warning(self, "%s - %s" % (PROGRAM_NAME, _("error")), _("Cover not detected.\n\nYou can drag&drop and image as \"nmm:artwork\" to manually set one."))

        elif url[:8] == 'delete:/':
            reply = QMessageBox.question(self, '%s - delete item' % PROGRAM_NAME, "Do you really want to send to trash this item??\n\n%s" % url[8:], QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                subprocess.Popen(['kioclient', 'move', url[8:], 'trash:/'])
                self.pendingQuery = True
                self.wvOutput.setHtml('<html><body><h3>Searching... <img src="file://%s"></h3></body></html>'
                                      % self.iconProcessIdle)
                if forceExec:
                    self.execQuery()
                    self.pendingQuery = False

        elif url[:6] == 'dolp:/':
            subprocess.Popen(['dolphin', url[6:]])

        elif url[:14] == 'googlesearch:/':
            url = "http://www.google.com:/search?q=%s&ie=UTF-8&oe=UTF-8" % url[14:].replace("?", "%3F")
            subprocess.Popen(["kioclient", "exec", url])

        elif url[:6] == 'konq:/':
            subprocess.Popen(['konqueror', url[6:]])

        elif url[:10] == 'navigate:/':
            if ((self.navigationData == []) or (len(self.navigationData) < 2)):
                return True

            idx = lindex(self.navigationData, self.leSearch.text(), 0)
            if idx is not None:
                navigateTo = url[10:].lower()
                if navigateTo == "first":
                    idx = 0

                elif navigateTo == "previous":
                    if idx > 0:
                        idx -= 1

                elif navigateTo == "next":
                    if idx < len(self.navigationData) - 1:
                        idx += 1

                elif navigateTo == "last":
                    idx = len(self.navigationData) - 1

                self.linkClicked(QUrl(self.navigationData[idx][0]), False)

        elif url[:9] == 'nepomuk:/':
            self.leSearch.setText(url)
            self.pendingQuery = True
            self.wvOutput.setHtml('<html><body><h3>Reading... <img src="file://%s"></h3></body></html>'
                                  % self.iconProcessIdle)
            if forceExec:
                self.execQuery()
                self.pendingQuery = False

        elif url[:6] == 'prop:/':
            subprocess.Popen(['kioclient', 'openProperties', url[6:]])

        elif url[:9] == "propadd:/":
            uri = url[9:]
            self.addProperty(uri)

        elif url[:10] == "propedit:/":
            uri = url[10:].split("&")
            if (len(uri) == 2):
                if self.keyModifiers == Qt.NoModifier:
                    self.addProperty(uri[0], uri[1])

                elif self.keyModifiers == Qt.ShiftModifier:
                    self.editProperty(uri[0], uri[1])

                elif self.keyModifiers == Qt.ControlModifier:
                    self.removeProperty(uri[0], uri[1])

        elif url[:7] == 'query:/':
            urlElements = url[7:].split("'")
            if len(urlElements) >= 3:
                tmpUrl = urlElements[0] + '"'
                for i in range(1, len(urlElements) - 2):
                    tmpUrl += urlElements[i] + "'"
                tmpUrl += urlElements[-2] + '"'

            elif len(urlElements) == 2:
                tmpUrl = urlElements[0] + "'" + urlElements[1] + "'"

            elif len(urlElements) == 1:
                tmpUrl = "'" + urlElements[0] + "'"

            else:
                pass

            self.leSearch.setText(tmpUrl)
            self.pendingQuery = True
            self.wvOutput.setHtml('<html><body><h3>Searching... <img src="file://%s"></h3></body></html>'
                                  % self.iconProcessIdle)
            if forceExec:
                self.execQuery()
                self.pendingQuery = False

        elif url[:9] == "reindex:/":
            subprocess.Popen(["nepomukindexer", url[9:].replace("?", "%3F")])

        elif url[:8] == 'remove:/':
            reply = QMessageBox.question(self, '%s - remove resource' % PROGRAM_NAME, "Really delete this resource?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                resource = Nepomuk.Resource(url[8:])
                resource.remove()
                self.pendingQuery = True
                self.queryMethod = "refresh"
                self.wvOutput.setHtml('<html><body><h3>Searching... <img src="file://%s"></h3></body></html>'
                                      % self.iconProcessIdle)
                if forceExec:
                    self.execQuery()
                    self.pendingQuery = False

        elif url[:8] == 'render:/':
            self.leSearch.readOnly = True
            self.wvOutput.setHtml('<html><body><h3>Rendering... <img src="file://%s"></h3></body></html>'
                                  % self.iconProcessIdle)
            self.wvOutput.repaint()
            self.setCursor(Qt.BusyCursor)
            self.repaint()
            self.wvOutput.setHtml(self.cache[self.queriesIndex].formatAsHtml(url[8:]))

            self.setCursor(Qt.ArrowCursor)
            self.leSearch.readOnly = False
            self.repaint()

        elif url[:5] == 'run:/':
            if url[:12] == 'run:/file://':
                subprocess.Popen(["kioclient", "exec", url[12:]])

            else:
                subprocess.Popen(["kioclient", "exec", url[5:]])

        elif url[:11] == "setrating:/":
            rating = url[11:]
            try:
                rating = int(rating)

            except:
                rating = 0

            self.setRating(None, rating)

        else:
            # In KDE we trust.nepomuk:/res/eee8837d-27ab-43ac-a34a-43d339102c1c
            # Seems like there is a problem with character ?.
            subprocess.Popen(["kioclient", "exec", url.replace("?", "%3F")])

        # Clear always modifiers because the next keypress could happen in other window.
        self.keyModifiers = Qt.NoModifier

    def setRating(self, uri=None, rating=None):
        if (uri is None):
            uri = self.leSearch.text().strip()
            if not uri[:13] == "nepomuk:/res/":
                QMessageBox.warning(self, "%s - %s" % (PROGRAM_NAME, _("error")), _("You can only add properties in the Resource Viewer."))
                return False

        if vartype(uri) == "Resource":
            resource = uri

        else:
            if self.model is None:
                return False

            if INTERNAL_RESOURCE:
                resource = cResource(uri)

            else:
                resource = Nepomuk.Resource(uri)

        if vartype(rating) == "int":
            pass

        elif vartype(rating) in ("str", "unicode"):
            try:
                rating = int(rating)

            except:
                rating = 0

        elif vartype(rating) == "QString":
            try:
                rating = int(rating)

            except:
                rating = 0

        if ((rating is None) or (rating < 0)):
            resource.removeProperty(toVariant(QUrl(resource.ratingUri())))
            rating = None

        else:
            rating = max(min(rating, 10), 0)
            resource.setRating(rating)

        if (vartype(uri) != "Resource"):
            time.sleep(SLEEP_AFTER_UPDATE)
            self.pendingQuery = True
            self.queryMethod = "refresh"
            self.wvOutput.setHtml('<html><body><h3>Searching... <img src="file://%s"></h3></body></html>'
                                  % self.iconProcessIdle)

        return rating

    def addProperty(self, uri=None, ontology="", text=""):
        if (uri is None):
            uri = self.leSearch.text().strip()

        if not uri[:13] == "nepomuk:/res/":
            QMessageBox.warning(self, "%s - %s" % (PROGRAM_NAME, _("error")), _("You can only add properties in the Resource Viewer."))
            return False

        mustRefresh = SLEEP_NO_SLEEP

        if self.model is None:
            return False

        if INTERNAL_RESOURCE:
            resource = cResource(uri)

        else:
            resource = Nepomuk.Resource(uri)

        resourceMainType = NOCR(resource.type())
        if ontology == "":
            query = 'SELECT DISTINCT ?r\n' \
                    'WHERE {\n' \
                    '\t{\n' \
                    '\t\t?r rdfs:domain %s .\n' \
                    '\t} UNION {\n' \
                    '\t\t?r rdfs:range rdfs:Literal .\n' \
                    '\t} UNION {\n' \
                    '\t\t?r rdfs:range xsd:string .\n' \
                    '\t}\n' \
                    '}\n' \
                    % (resourceMainType)

            values = []
            values += ["nao:numericRating"]
            queryResultSet = self.model.executeQuery(query, Soprano.Query.QueryLanguageSparql)
            if queryResultSet.isValid():
                while queryResultSet.next():
                    values += [NOCR(queryResultSet["r"].toString())]

            if values != []:
                parameters = []
                status = "on"
                values.sort()
                for value in values:
                    parameters += [value, value, status]
                    if status == "on":
                        status = "off"

                ontologyResource, labelResource = dialogList(parameters, _("Select an ontology:"))
                if ((ontologyResource is None) or (ontologyResource == "")):
                    return False

        else:
            ontologyResource = ontology
            labelResource = ontology

        if not ((ontologyResource is None) or (ontologyResource == "")):
            if text == "":
                text = dialogInputBox(_("Value to store in \"%s\":") % ontologyResource)

            if text != "":
                if True:
                    print("%s: property %s added" % (uri, ontologyResource))
                    if ontologyResource == "nao:numericRating":
                        self.setRating(resource, text)

                    else:
                        resource.addProperty(QUrl(NOC(ontologyResource, True)), toVariant(text))

                    mustRefresh = SLEEP_AFTER_UPDATE

        else:
            QMessageBox.warning(self, "%s - %s" % (PROGRAM_NAME, _("error")), _("Sorry, I don't know what to do with this resource and custom ontologies are not supported yet."))

        if mustRefresh > SLEEP_NO_SLEEP:
            time.sleep(mustRefresh)
            self.pendingQuery = True
            self.queryMethod = "refresh"
            self.wvOutput.setHtml('<html><body><h3>Searching... <img src="file://%s"></h3></body></html>'
                                  % self.iconProcessIdle)


    def editProperty(self, uri=None, ontology=None):
        if (uri is None):
            uri = self.leSearch.text().strip()

        if not uri[:13] == "nepomuk:/res/":
            QMessageBox.warning(self, "%s - %s" % (PROGRAM_NAME, _("error")), _("You can only add properties in the Resource Viewer."))
            return False

        mustRefresh = SLEEP_NO_SLEEP

        if self.model is None:
            return False

        if INTERNAL_RESOURCE:
            resource = cResource(uri)

        else:
            resource = Nepomuk.Resource(uri)

        try:
            text = resource.property(NOC(ontology))
            if text.isStringList():
                parameters = []
                status = "on"
                # Trying to avoid the two titles bug with this oldItem.
                oldItem = ""
                for item in text.toStringList():
                    item = item
                    if item == oldItem:
                        continue

                    oldItem = item
                    parameters += [item] + [item] + [status]
                    if status == "on":
                        status = "off"

                text, dummyValue = dialogList(parameters, _("Select value to edit:"))
                if text.strip() == "":
                    return False

            else:
                text = resource.property(NOC(ontology)).toString()

            if text[:13] == "nepomuk:/res/":
                QMessageBox.warning(self, "%s - %s" % (PROGRAM_NAME, _("error")), _("You can't edit resources here, click in the resource and edit directly."))
                return False

        except:
            text = None

        if text is not None:
            newText = dialogTextInputBox("Editing \"%s\":" % ontology, text)
            if newText != text:
                resourceReply = QMessageBox.question(self, '%s - edit value' % PROGRAM_NAME, _("Save changes to '%s'?") % (ontology), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if resourceReply == QMessageBox.Yes:
                    print("%s: property %s edited" % (uri, ontology))
                    if ontology == "nao:numericRating":
                        self.setRating(resource, newText)

                    else:
                        ontologyFull = QUrl(NOC(ontology, True))
                        if ontology in ("nie:url"):
                            # Caution!, strip() is mandatory here because only one line is supported.
                            newText = QUrl(newText.strip())
                            if (newText.isValid()):
                                resource.setProperty(ontologyFull, toVariant(newText))

                            else:
                                QMessageBox.warning(self, "%s - %s" % (PROGRAM_NAME, _("error")), _("Invalid url."))
                                return False

                        else:
                            resource.removeProperty(ontologyFull, toVariant(text))
                            resource.addProperty(ontologyFull, toVariant(newText))

                    mustRefresh = SLEEP_AFTER_UPDATE

        if mustRefresh > SLEEP_NO_SLEEP:
            time.sleep(mustRefresh)
            self.pendingQuery = True
            self.queryMethod = "refresh"
            self.wvOutput.setHtml('<html><body><h3>Searching... <img src="file://%s"></h3></body></html>'
                                  % self.iconProcessIdle)

        return True


    def removeProperty(self, uri=None, ontology=None):
        if ((uri is None) or (ontology is None)):
            return False

        mustRefresh = SLEEP_NO_SLEEP

        query = 'SELECT DISTINCT ?v\n' \
                'WHERE {\n' \
                '\t<%s> %s ?v .\n' \
                '}\n' \
                % (uri, ontology)

        values = []
        queryResultSet = self.model.executeQuery(query, Soprano.Query.QueryLanguageSparql)
        if queryResultSet.isValid():
            while queryResultSet.next():
                values += [NOCR(queryResultSet["v"].toString())]

        if values != []:
            resourcesList = []
            for value in values:
                if value[:13] == "nepomuk:/res/":
                    if INTERNAL_RESOURCE:
                        label = cResource(value).genericLabel()

                    else:
                        label = Nepomuk.Resource(value).genericLabel()

                else:
                    label = value

                resourcesList += [[value, label]]

            if (len(values) > 1):
                resourcesList = sorted(resourcesList, key=lambda item: item[1])
                # Convert to 1 dimension.
                parameters = []
                status = "on"
                for param in resourcesList:
                    parameters += [param[0]] + [param[1]] + [status]
                    if status == "on":
                        status = "off"

                value, label = dialogList(parameters, _("Select the value to be removed:"))

            else:
                value = resourcesList[0][0]
                label = resourcesList[0][1]

            if ((value is not None) and (value != "")):
                reply = QMessageBox.question(self, '%s - remove property' % PROGRAM_NAME, "Remove property \"%s\" with value \"%s\"?" % (ontology, label), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    print("%s: property %s removed" % (uri, ontology))
                    if (len(values) == 1):
                        resource = Nepomuk.Resource(uri)
                        resource.removeProperty(QUrl(NOC(ontology)))
                        mustRefresh = SLEEP_AFTER_UPDATE

                    else:
                        resource = Nepomuk.Resource(uri)
                        resource.removeProperty(QUrl(NOC(ontology)), toVariant(value))
                        mustRefresh = SLEEP_AFTER_UPDATE

        if mustRefresh > SLEEP_NO_SLEEP:
            time.sleep(mustRefresh)
            self.pendingQuery = True
            self.queryMethod = "refresh"
            self.wvOutput.setHtml('<html><body><h3>Searching... <img src="file://%s"></h3></body></html>'
                                  % self.iconProcessIdle)


    def dropHandler(self, event):
        supportedImageFormats = QImageReader.supportedImageFormats() + ["nef"]
        mustRefresh = SLEEP_NO_SLEEP

        #Qt::KeyboardModifiers QDropEvent::keyboardModifiers () const
        #Qt::MouseButtons QDropEvent::mouseButtons () const
        #QWidget * QDropEvent::source () const para controlar el d&d sobre si mismo.

        # Query para obtener las propiedades "oficiales".
        # SELECT * WHERE { ?r rdfs:domain %s .}

        # Query para obtener qué puede ser un resource.
        #SELECT * WHERE { ?r rdfs:range %s . }

        uri = self.leSearch.text().strip()
        if not uri[:13] == "nepomuk:/res/":
            QMessageBox.warning(self, "%s - %s" % (PROGRAM_NAME, _("error")), _("You can only drop data in the Resource Viewer."))
            return False

        if event.mimeData().hasUrls():
            imageReply = resourceReply = None
            for i in range(0, len(event.mimeData().urls())):
                url = event.mimeData().urls()[i].toString().strip()
                print("url: %s" % url)

                dropType = None
                if dropType is None:
                    ext = os.path.splitext(url)[1][1:].lower()
                    if (ext != ''):
                        if ext in supportedImageFormats:
                            if ((url[:7] == "http://") or (url[:8] == "https://")):
                                dropType = "url_image"

                            elif fileExists(url):
                                dropType = "image"

                if dropType is None:
                    if url[:13] == "nepomuk:/res/":
                        dropType = "resource"

                if dropType is None:
                    if ((url[:7] == "http://") or (url[:8] == "https://")):
                        dropType = "url"

                if dropType is None:
                    if (url[:10] == "propedit:/"):
                        try:
                            ontValue = url[10:].split("&")[1]

                        except:
                            ontValue = ""

                        self.addProperty(uri, ontValue)
                        continue

                if dropType is None:
                    if (url[:9] == "propadd:/"):
                        self.addProperty(uri)
                        continue

                if dropType == "image":
                    if (i == 0):
                        parameters = [ONTOLOGY_SYMBOL, ONTOLOGY_SYMBOL, "off", ONTOLOGY_SYMBOL_CONTACT, ONTOLOGY_SYMBOL_CONTACT, "off", "nfo:depiction", "nfo:depiction", "on", ONTOLOGY_MUSIC_ALBUM_COVER, ONTOLOGY_MUSIC_ALBUM_COVER, "off"]
                        ontologyImages, labelImages = dialogList(parameters, _("Select an ontology:"))
                        if ((ontologyImages is None) or (ontologyImages == "")):
                            continue

                        if (len(event.mimeData().urls()) > 1):
                            msgImagePronoun = "all images"

                        else:
                            msgImagePronoun = "next image"

                        msgImageUrl = "\n\n" + "\n".join([urlItem.toString() for urlItem in event.mimeData().urls()])
                        imageReply = QMessageBox.question(self, _("%s - add data") % PROGRAM_NAME, _("add %s as %s?%s") % (msgImagePronoun, ontologyImages, msgImageUrl), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

                    if imageReply == QMessageBox.Yes:
                        uriResource = Nepomuk.Resource(uri)
                        uriResource.addProperty(NOC(ontologyImages, True), toVariant(url))
                        mustRefresh = SLEEP_AFTER_UPDATE

                elif dropType in ("url", "url_image"):
                    if dropType == "url_image":
                        parameters = [ONTOLOGY_LINK, ONTOLOGY_LINK, "on", ONTOLOGY_SYMBOL, ONTOLOGY_SYMBOL, "off", ONTOLOGY_SYMBOL_CONTACT, ONTOLOGY_SYMBOL_CONTACT, "off", "nfo:depiction", "nfo:depiction", "off", ONTOLOGY_MUSIC_ALBUM_COVER, ONTOLOGY_MUSIC_ALBUM_COVER, "off"]
                        ontologyUrl, labelUrl = dialogList(parameters, _("Select an ontology:"))
                        if ((ontologyUrl is None) or (ontologyUrl == "")):
                            continue

                        if (len(event.mimeData().urls()) > 1):
                            msgImagePronoun = "all images"

                        else:
                            msgImagePronoun = "next image"

                        msgImageUrl = "\n\n" + "\n".join([urlItem.toString() for urlItem in event.mimeData().urls()])
                        urlReply = QMessageBox.question(self, _("%s - add data") % PROGRAM_NAME, _("add %s as %s?%s") % (msgImagePronoun, ontologyUrl, msgImageUrl), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

                    else:
                        urlReply = QMessageBox.question(self, '%s - add resource' % PROGRAM_NAME, "Add \"%s\" as \"%s\"?" % (url, ONTOLOGY_LINK), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                        ontologyUrl = ONTOLOGY_LINK

                    if urlReply == QMessageBox.Yes:
                        # This code has really low performance so don't use it.
                        #urlResource = Nepomuk.Resource()
                        #urlResource.addType(NOC("nfo:Website", True))
                        #urlResource.setProperty(NOC("nie:url", True), toVariant(QUrl(url)))
                        #uriResource.addProperty(NOC(ontologyUrl, True), toVariant(urlResource.uri()))
                        urlResource = Nepomuk.Resource(QUrl(url), NOC("nfo:RemoteDataObject", True))
                        urlResource.addType(NOC("nfo:Website", True))
                        uriResource = Nepomuk.Resource(uri)
                        uriResource.addProperty(NOC(ontologyUrl, True), toVariant(urlResource))
                        mustRefresh = SLEEP_AFTER_UPDATE

                else:
                    if self.model is None:
                        return False

                    if INTERNAL_RESOURCE:
                        resource = cResource(url)

                    else:
                        resource = Nepomuk.Resource(url)

                    resourceMainType = NOCR(resource.type())
                    resourceGenericLabel = resource.genericLabel()

                    if dropType == "resource":
                        query = 'SELECT DISTINCT ?r\n' \
                                'WHERE {\n' \
                                '\t?r rdfs:range %s .\n' \
                                '}\n' \
                                % (resourceMainType)

                    else:
                        query = 'SELECT DISTINCT ?r\n' \
                                'WHERE {\n' \
                                '\t?r rdfs:domain %s .\n' \
                                '}\n' \
                                % (resourceMainType)

                    values = []
                    queryResultSet = self.model.executeQuery(query, Soprano.Query.QueryLanguageSparql)
                    if queryResultSet.isValid():
                        while queryResultSet.next():
                            values += [NOCR(queryResultSet["r"].toString())]

                    if values != []:
                        parameters = []
                        status = "on"
                        values.sort()
                        for value in values:
                            parameters += [value, value, status]
                            if status == "on":
                                status = "off"

                        ontologyResource, labelResource = dialogList(parameters, _("Select an ontology:"))
                        if ((ontologyResource is None) or (ontologyResource == "")):
                            continue

                        resourceReply = QMessageBox.question(self, '%s - add resource' % PROGRAM_NAME, "Add \"%s\" as \"%s\"?" % (resourceGenericLabel, ontologyResource), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                        if resourceReply == QMessageBox.Yes:
                            print("%s: property %s added" % (uri, ontologyResource))
                            resourceResource = Nepomuk.Resource(uri)
                            resourceResource.addProperty(QUrl(NOC(ontologyResource, True)), toVariant(url))
                            mustRefresh = SLEEP_AFTER_UPDATE

                    else:
                        QMessageBox.warning(self, "%s - %s" % (PROGRAM_NAME, _("error")), _("Sorry, I don't know what to do with this resource and custom ontologies are not supported yet."))

        elif event.mimeData().hasText():
            text = event.mimeData().text()
            if text == "":
                return False

            self.addProperty(uri, "", text)

        if mustRefresh > SLEEP_NO_SLEEP:
            time.sleep(mustRefresh)
            self.pendingQuery = True
            self.queryMethod = "refresh"
            self.wvOutput.setHtml('<html><body><h3>Searching... <img src="file://%s"></h3></body></html>'
                                  % self.iconProcessIdle)

    def goBackward(self):
        refresh = False
        searchText = self.leSearch.text()

        if self.queriesIndex >= 0 and searchText != self.cache[self.queriesIndex].searchString:
            refresh = True

        else:
            if (self.queriesIndex > 0):
                self.queriesIndex -= 1
                refresh = True

        if refresh:
            self.setCursor(Qt.BusyCursor)
            searchString = self.cache[self.queriesIndex].searchString

            self.leSearch.setText(searchString)
            self.pendingQuery = False
            self.wvOutput.setHtml(self.cache[self.queriesIndex].formatAsHtml())
            self.setCursor(Qt.ArrowCursor)
            self.leSearch.readOnly = False
            self.repaint()
            self.navigationData = self.cache[self.queriesIndex].data

    def goForward(self):
        if (self.queriesIndex < (len(self.cache) - 1)):
            self.queriesIndex += 1
            self.setCursor(Qt.BusyCursor)
            searchString = self.cache[self.queriesIndex].searchString

            self.leSearch.setText(searchString)
            self.pendingQuery = False
            self.wvOutput.setHtml(self.cache[self.queriesIndex].formatAsHtml())
            self.setCursor(Qt.ArrowCursor)
            self.leSearch.readOnly = False
            self.repaint()
            self.navigationData = self.cache[self.queriesIndex].data

    def showHelp(self):
        self.leSearch.setText("--help")
        self.pendingQuery = False
        self.wvOutput.setHtml(self.buildHelp(self.sparql))
        self.repaint()

    def buildHelp(self, oSparqlBuilder):
        commands = '<p><b>Commands</b>:\n<ul>\n'
        for command in oSparqlBuilder.commands:
            commands += '<li>%s</li>\n' % command[0]
        commands += '</ul></p>\n'

        shortcuts = '<p><b>Onlologies shorcuts</b>:<ul>\n' + self.htmlTableHeader \
                    % {'border': 0, 'cellpadding': 0}
        for shortcut in oSparqlBuilder.shortcuts:
            info = ''
            fmtOntology = shortcut[0]
            if fmtOntology.find('%') >= 0:
                fmtOntology = fmtOntology.replace('%', '')
                info += ' (using percent encoding)'

            elif fmtOntology.find('!') >= 0:
                fmtOntology = fmtOntology.replace('!', '')
                info += ' (supports duplicated properties)'

            if fmtOntology.find('_') >= 0:
                fmtOntology = fmtOntology.replace('_', '')
                info += ' (using optionals to negate)'

            shortcuts += '<tr><td><b>%(abr)s</b>, <b>%(shortcut)s</b>:</td><td><em>%(ontology)s</em>%(info)s</td></tr>\n' \
                                % {'abr': shortcut[2], 'shortcut': shortcut[1], 'ontology': fmtOntology, 'info': info}

        shortcuts += self.htmlTableFooter + '</ul></p>\n'

        remarks = "<p><b>Remarks</b>:<br \>\n" \
                    "<ul>\n" \
                    "<li>This program was tested on <b>KDE 4.8.4</b>." \
                    "<li>Nepomuk search api is available using e0 or e2 as prefix.</li>\n" \
                    "<li><b>Virtuoso 6.1.4</b> or greater is required to use Nepomuk search api.</li>\n" \
                    "<li>Query syntax is inspired in Google's search syntax.</li>\n" \
                    "<li>Nepoogle do a text search in identifiers, descriptions, tags, fullnames, titles and urls.</li>\n" \
                    "<li>Parenthesis for group queries are not supported.</li>\n" \
                    "<li>You can use regular expressions searching strings.</li>\n" \
                    "<li>Nepoogle's own engine works with Soprano and don't uses Nepomuk to do queries.</li>\n" \
                    "<li>Be cautious, certain ontologies combinations in a same query may offer 0 results.</li>\n" \
                    "</ul></p>\n" \

        commandsList = ''
        for command in oSparqlBuilder.commands:
            if commandsList != '':
                commandsList += ' | ' + command[0]

            else:
                commandsList += command[0]

        shortcutsList = ''
        for shortcut in oSparqlBuilder.shortcuts:
            if shortcutsList != '':
                shortcutsList += ' | ' + shortcut[1]

            else:
                shortcutsList += shortcut[1]

        syntax = "<p><b>The query syntax is</b>:<ul>\n" \
                    "<em>query</em> :== e0 querystring<sup>1)</sup><br />\n"\
                    "<em>query</em> :== e2 querystring<sup>2)</sup><br />\n"\
                    "<br />\n" \
                    "<em>query</em> :== [e1] item [[logop] item]... | command | uri<br />\n"\
                    "<br />\n" \
                    "<em>logop</em> :== and | or<br />\n" \
                    "<em>compop</em> :==  = | < | <= | > | >=<br />\n" \
                    "<em>op</em> :== + | - | compop<br />\n" \
                    "<br />\n" \
                    "<em>item</em> :== [ontology:][op]text | &lt;ontology&gt;&lt;op&gt;&lt;text&gt;<br />\n" \
                    "<br />\n" \
                    "<em>ontology</em> :== [ontitem=]ontitem[->[ontitem=]ontitem]]...<br />\n" \
                    "<em>ontitem</em> :== shortcutontology | shortontology | fullontology<br />\n" \
                    "<em>shortcutontology</em> :== %(shortcuts)s<br />\n" \
                    "<em>shortontology</em> :== prefix:name<br />\n" \
                    "<em>fullontology</em> :== &lt;http://fullurl&gt;<br />\n" \
                    "<br />\n" \
                    "<em>text</em> :== date | number | string | time<br />\n" \
                    "<em>date</em> :== yyyy-mm-dd | month | day | year<br />\n" \
                    "<em>month</em> :== 1..12[m]<br />\n" \
                    "<em>day</em> :== 13..31 | 1..31d<br />\n" \
                    "<em>year</em> :== 31..9999 | 1..9999y<br />\n" \
                    "<em>number</em> :== posnumber | negnumber | fraction<br />\n" \
                    "<em>posnumber</em> :== 0..9<br />\n" \
                    "<em>negnumber</em> :== compop-0..9<br />\n" \
                    "<em>fraction</em> :== posnumber/posnumber | negnumber/posnumber<br />\n" \
                    "<em>string</em> :== chars | \"chars\" | 'chars'<br />\n" \
                    "<em>chars</em> :== any number of utf-8 characters<br />\n" \
                    "<em>time</em> :== hh:mm:ss | hour | minute | seconds<br />\n" \
                    "<em>hour</em> :== 1..24[h]<br />\n" \
                    "<em>minute</em> :== 25..60 | 1..60m<br />\n" \
                    "<em>seconds</em> :== 1..60s<br />\n" \
                    "<br />\n" \
                    "<em>command</em> :== instruction[:string]<br />\n" \
                    "<em>instruction</em> :== %(instructions)s<br />\n" \
                    "<br />\n" \
                    "<sup>1)</sup>e0 uses <a href=\"http://api.kde.org/4.x-api/kdelibs-apidocs/nepomuk-core/html/classNepomuk_1_1Query_1_1QueryParser.html\">Nepomuk::Query::QueryParser()</a> and it has its own query syntax.<br />" \
                    "<sup>2)</sup>e2 uses a hacked version of <a href=\"http://api.kde.org/4.x-api/kdelibs-apidocs/nepomuk-core/html/classNepomuk_1_1Query_1_1QueryParser.html\">Nepomuk::Query::QueryParser()</a> optimized with subqueries.<br />" \
                    "</ul>" \
                    "</p>\n" \
                    % {'shortcuts': shortcutsList, 'instructions': commandsList}

        examples = "<p><b>Examples</b>:\n" \
                    + self.htmlTableHeader % {'border': 1, 'cellpadding': 2} + \
                    "<tr><td><b>query</b></td>\n" \
                        "<td><b>result</b></td></tr>\n" \
                    "<tr><td><em>movie</em></td>\n" \
                        "<td>contains word 'movie'</td></tr>\n" \
                    "<tr><td><em>+movie</em></td>\n" \
                        "<td>equals word 'movie'</td></tr>\n" \
                    "<tr><td><em>-movie</em></td>\n" \
                        "<td>not contains word 'movie'</td></tr>\n" \
                    "<tr><td><em>hastag:-dorama +'takeuchi yuuko' 'hiroshi'</em></td>\n" \
                        "<td>not tagged as 'dorama' and equals 'takeuchi yuuko' and contains 'hiroshi'</td></tr>\n" \
                    "<tr><td><em>movie or hasTag:'takeuchi yuuko'</em></td>\n" \
                        "<td>contains movie or tagged 'takeuchi yuuko'</td></tr>\n" \
                    "<tr><td><em>hasTag:+movie rating:>=5</em></td>\n" \
                        "<td>tagged exactly 'movie' and rating >= 5</td></tr>\n" \
                    "<tr><td><em>url:\"^file:///media\" mimetype:image mimetype:-image/jpeg</em></td>\n" \
                        "<td>all image files, except jpegs, located in /media</td></tr>\n" \
                    "<tr><td><em>mimetype:image/png height:>=1200 width:>=1600</em></td>\n" \
                        "<td>all pngs with a resolution great or equal to 1600x1200</td></tr>\n" \
                    "<tr><td><em>playcount:0 hastag:corea genre:drama actor:+'Yeong-ae Lee' director:Park</em></td>\n" \
                        "<td>not played movie dramas tagged 'corea' with actress 'Yeong-ae Lee' and with director name contains 'Park'</td></tr>\n" \
                    "<tr><td><em>actor:'Zhang Ziyi' and actor:-'Bingbing Fan'</em></td>\n" \
                        "<td>movies with actress 'Zhang Ziyi' but without actress 'Bingbing Fan'</td></tr>\n" \
                    "<tr><td><em>tvshow:Coupling season:2 episode:4</em></td>\n" \
                        "<td>Episode 4 of Season 2 of Coupling</td></tr>\n" \
                    "<tr><td><em>--tags</em></td>\n" \
                        "<td>all tags</td></tr>\n" \
                    "<tr><td><em>--actors:luppi</em></td>\n" \
                        "<td>all actors containing 'luppi'</td></tr>\n" \
                    + self.htmlTableFooter + \
                    "</p>\n"

        output = "<html>\n  <head>\n"\
                    "<style type=\"text/css\">" \
                    "body {%(body_style)s}\n" \
                    "p {%(p_style)s}\n" \
                    "ul {%(ul_style)s}\n" \
                    "li {%(li_style)s}\n" \
                    "tr {%(tr_style)s}\n" \
                    "</style>\n" \
                    "<title>%(title)s</title>\n    " \
                    "<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\">" \
                    "\n  </head>\n<body>\n" \
                    "<p><h3>%(program)s's help</h3></p>\n" \
                    "<p><b>%(program)s</b> is a system to query the <em>Nepomuk's database</em>. <b>%(program)s</b> does not search the file system so that only returns results that are pre-collected in <em>Nepomuk's database</em>.</p>\n" \
                    "<p><b>Warning!:</b> since <b>%(program)s 0.9.4</b> resources can be edited using dialog forms and/or drag&amp;drop but this features are <em>not fully tested and may contain bugs</em>. Please, <em>be cautious</em> using edition capabilities!</p>\n" \
                    "%(examples)s" \
                    "%(remarks)s" \
                    "%(shortcuts)s" \
                    "%(commands)s" \
                    "%(syntax)s" \
                    "For bugs, suggestions or wishes send a mail to kde@aynoa.net\n" \
                    "%(powered)s</body>\n</html>" \
                    % {'title': 'Querying Nepomuk', \
                        'error': sys.exc_info()[1], \
                        'program': os.path.basename(sys.argv[0]), \
                        'powered': PROGRAM_HTML_POWERED, \
                        'remarks': remarks, \
                        'syntax': syntax, \
                        'shortcuts': shortcuts, \
                        'commands': commands, \
                        'examples': examples, \
                        'body_style': "font-size:small", \
                        'p_style': "font-size:small", \
                        'ul_style': "font-size:small", \
                        'li_style': "font-size:small", \
                        'tr_style': "font-size:small;" \
                        }

        return output


    def htmlRenderLink(self, id = 'uri', par1 = '', par2 = ''):
        if id == 'uri':
            title = "title=\"%s\"" % par1
            href = "href=\"%s\"" % par1
            value = par2

        elif id == 'album':
            title = "title=\"album:+\'%s\'\"" % par1
            href = "href=\"query:/album:+\'%s\'\"" % par1
            value = self.htmlLinkSearch

        elif id == 'contact':
            title = "title=\"contact:+\'%s\'\"" % par1
            href = "href=\"query:/contact:+\'%s\'\"" % par1
            value = self.htmlLinkSearch

        elif id == 'navigator':
            return "%s%s%s%s" % (self.htmlLinkNavigateFirst, \
                                    self.htmlLinkNavigatePrevious, \
                                    self.htmlLinkNavigateNext, \
                                    self.htmlLinkNavigateLast)

        elif id == 'ontology':
            title = "title=\"%s:+\'%s\'\"" % (par1, par2)
            href = "href=\"query:/%s:+\'%s\'\"" % (par1, par2)
            value = self.htmlLinkSearch

        elif id == 'performer':
            title = "title=\"performer:+\'%s\'\"" % par1
            href = "href=\"query:/performer:+\'%s\'\"" % par1
            value = self.htmlLinkSearch

        elif id == 'tag':
            title = "title=\"hasTag:+\'%s\'\"" % par1
            href = "href=\"query:/hasTag:+\'%s\'\"" % par1
            value = self.htmlLinkSearch

        # This is an exception.
        elif id == 'unplugged':
            if par1 == '':
                return "<b>[Unplugged<a title=\"uuid:%s\" href=\"prop:/%s\">%s</a>]</b><em>%s</em>" \
                        % (par2[8:].split('/')[0], \
                            par2[8:].split('/')[0], \
                            self.htmlLinkInfo, \
                            '/' + '/'.join(par2[8:].split('/')[1:]) \
                            )

            else:
                return "<b>[Unplugged<a title=\"uuid:%s\" href=\"prop:/%s\">%s</a>]</b><a title=\"%s\" href=\"%s\"><em>%s</em></a>" \
                        % (par2[8:].split('/')[0], \
                            par2[8:].split('/')[0], \
                            self.htmlLinkInfo, \
                            par1, \
                            par1, \
                            '/' + '/'.join(par2[8:].split('/')[1:]) \
                            )

        elif id == 'url':
            title = "title=\"%s\"" % par1
            href = "href=\"%s\"" % par1
            value = par2
            #TODO: añadir un icono que indique que es un enlace externo.

        else:
            return ''

        return "<a %s %s>%s</a>" % (title, href, value)


    def processMacros(self, searchString = ""):
        if searchString.find("--m0:") >= 0:
            searchString = searchString.replace("--m0:", "--playlist genre:-instrumental performer:")

        elif searchString.find("--m1:") >= 0:
            searchString = searchString.replace("--m1:", "--playlist genre:-instrumental nmm:musicAlbum->nmm:albumArtist->nco:fullname:")

        return searchString


    def execQuery(self, searchString = ''):
        self.leSearch.readOnly = True
        self.setCursor(Qt.BusyCursor)
        self.repaint()

        self.renderedRows = 0
        self.renderedCache = ''

        self.resultData = []
        self.resultStructure = []
        self.resultTime = None

        searchEngine = DEFAULT_ENGINE
        if searchString == '':
            searchString = self.leSearch.text().strip()

        #if True:
        try:
            if not DO_NOT_USE_NEPOMUK and self.clearResourceManagerCache:
                Nepomuk.ResourceManager.instance().clearCache()

            self.sparql = cSparqlBuilder()
            if searchString[:9] == 'nepomuk:/':
                self.currUri = searchString
                if self.queryMethod in ("manual", "refresh"):
                    cachedData = None

                else:
                    cachedData = lvalue(self.cacheViewer, searchString, 0, 1)

                if cachedData is None:
                    oDataFormat = cDataFormat(searchString, self.model, self.screenWidth)
                    #output = oDataFormat.formatResourceInfo(searchString, self.sparql.shortcuts, self.sparql.ontologyTypes)
                    output = oDataFormat.formatResourceInfo(searchString, self.sparql.shortcuts, ontologyTypes)

                else:
                    output = cachedData

                if self.queryMethod == "manual":
                    # Cache must be trunked in current position if query changed.
                    if ((self.queriesIndex >= 0) and (self.queriesIndex < len(self.cache))):
                        if self.cache[self.queriesIndex].searchString != searchString:
                            self.cache = self.cache[:self.queriesIndex + 1]

                    if (self.cache == []) or (self.cache[self.queriesIndex].searchString != searchString):
                        self.cache += [oDataFormat]
                        self.queriesIndex += 1

                    else:
                        self.cache[self.queriesIndex] = oDataFormat

                    self.navigationData = []

                if cachedData is None:
                    i = lindex(self.cacheViewer, searchString, 0)
                    if i is None:
                        self.cacheViewer += [[searchString, output.replace("<cached />", " (cached)")]]

                    else:
                        self.cacheViewer[i][1] = output.replace("<cached />", " (cached)")

            elif searchString != '':
                self.currUri = None
                searchString = self.processMacros(searchString)
                if searchString[:3].lower() in ('e0 ', 'e1 ', 'e2 '):
                    searchEngine = int(searchString[1:2])

                else:
                    searchEngine = DEFAULT_ENGINE
                    searchString = "e%d %s" % (searchEngine, searchString)

                externalParameters = []
                if searchEngine == 0:
                    oNQP = Nepomuk.Query.QueryParser()
                    processedSearchString = searchString[3:]
                    for command in ["--playlist", "--playmixed"]:
                        if processedSearchString.find(command) >= 0:
                            externalParameters += [command]
                            processedSearchString = processedSearchString.replace(command, "")

                    query = oNQP.parse(processedSearchString).toSparqlQuery()
                    oNQP = None
                    if (self.verboseMode and sys.stdout.isatty()):
                        # Improve a little bit readability.
                        print(query.replace(" where ", " WHERE ").replace("{", "{\n").replace("}", "\n}").replace("} .", "} .\n").replace("} UNION {", " } UNION {").replace(". ?", ".\n ?").replace("\n ?", "\n  ?").replace("\n} .", "\n } .").replace("} .\n  ?", "} .\n ?"))

                    query = hackQueryParser(query, 'e0')
                    self.resultData, self.resultStructure, self.resultTime = self.sparql.executeQuery(query)

                elif searchEngine == 2:
                    oNQP = Nepomuk.Query.QueryParser()
                    processedSearchString = searchString[3:]
                    for command in ["--playlist", "--playmixed"]:
                        if processedSearchString.find(command) >= 0:
                            externalParameters += [command]
                            processedSearchString = processedSearchString.replace(command, "")

                    query = oNQP.parse(processedSearchString).toSparqlQuery()
                    oNQP = None
                    query = hackQueryParser(query, 'e2')
                    if (self.verboseMode and sys.stdout.isatty()):
                        # Improve a little bit readability.
                        print(query.replace(" where ", " WHERE ").replace("{", "{\n").replace("}", "\n}").replace("} .", "} .\n").replace("} UNION {", " } UNION {").replace(". ?", ".\n ?").replace("\n ?", "\n  ?").replace("\n} .", "\n } .").replace("} .\n  ?", "} .\n ?"))

                    self.resultData, self.resultStructure, self.resultTime = self.sparql.executeQuery(query)

                else:
                    searchString = searchString[3:]
                    self.sparql.stdoutQuery = (self.verboseMode and sys.stdout.isatty())
                    self.sparql.columns = '?x0 AS ?id ' + self.sparql.columns
                    self.resultData, self.resultStructure, self.resultTime = self.sparql.executeQuery(self.sparql.buildQuery(searchString))
                    self.warningsList = self.sparql.warningsList
                    self.sparql.warningsList = []

                oDataFormat = cDataFormat(searchString, self.model, self.screenWidth)
                if ((self.sparql.externalParameters == ['playlist']) or (externalParameters == ['--playlist'])):
                    output = oDataFormat.formatAsHtmlPlaylist('playlist', self.resultData, self.resultStructure, self.resultTime)

                elif ((self.sparql.externalParameters == ['playlist']) or (externalParameters == ['--playmixed'])):
                    output = oDataFormat.formatAsHtmlPlaylist('playmixed', self.resultData, self.resultStructure, self.resultTime)

                else:
                    output = oDataFormat.formatAsHtml(self.resultData, self.resultStructure, self.resultTime)

                # Cache must be trunked in current position if query changed.
                if ((self.queriesIndex >= 0) and (self.queriesIndex + 1 < len(self.cache))):
                    if self.cache[self.queriesIndex].searchString != searchString:
                        self.cache = self.cache[:self.queriesIndex + 1]

                if (self.cache == []) or (self.cache[self.queriesIndex].searchString != searchString):
                    self.cache += [oDataFormat]
                    self.queriesIndex += 1

                else:
                    self.cache[self.queriesIndex] = oDataFormat

                self.navigationData = self.cache[self.queriesIndex].data

            else:
                raise Exception('Please, type something.')

        #try:
        #    pass

        except:
            msgError = "%s" % sys.exc_info()[1]
            if msgError == 'help':
                output = self.buildHelp(self.sparql)

            elif msgError == 'quit':
                quit()

            else:
                output = "<html>\n  <head>\n    <title>%(title)s</title>\n    " \
                            "<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\">" \
                            "\n  </head>\n<body><b>error:</b> %(error)s" \
                            "%(powered)s</body>\n</html>" \
                            % {'title': 'Querying Nepomuk', \
                                'error': sys.exc_info()[1], \
                                'powered': PROGRAM_HTML_POWERED \
                                }

        self.pendingQuery = False
        self.queryMethod = None
        self.wvOutput.setHtml(output)
        self.setCursor(Qt.ArrowCursor)
        self.leSearch.readOnly = False
        self.repaint()

        # Handle possible warnings.
        warningMsg = ""
        for warning in self.warningsList:
            if warningMsg != "":
                warningMsg += "\n\n"

            if warning[0] == "BUG001":
                warningMsg += "There is a know bug using negation without a shortcut.\n" \
                        "Please notice that the results may be inaccurate.\n\n"
                for i in range(1, len(warning)):
                    warningMsg += "Change \"%s\" for something like \"title:%s\" to solve this issue.\n" \
                    % (warning[i], warning[i])

            #else:
                #pass

        self.warningsList = []

        if warningMsg != "":
            QMessageBox.warning(self, "%s - %s" % (PROGRAM_NAME, _("warning")), warningMsg)

