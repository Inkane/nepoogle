# -*- coding: utf-8 -*-
from PyQt4.QtWebKit import QWebView, QWebPage


#
# cWebView class
#
class cWebView(QWebView):

    owner = None

    def __init__(self, *args):
        super(cWebView, self).__init__(*args)
        self.owner = args[0]
        self.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        self.page().setForwardUnsupportedContent(True)

    def dragMoveEvent(self, event):
        if (event.mimeData().hasFormat("text/plain")):
            event.setAccepted(True)

    def dropEvent(self, event):
        self.owner.dropHandler(event)


def hackQueryParser(query='', hackLevel='e2'):

    if query.find("?v7 ") == -1:
        # Don't change queries with only one item.
        return query

    if hackLevel.lower() == 'e2':
        query = query.replace(' ?r <http://www.semanticdesktop.org/ontologies/2007/08/15/nao#userVisible> ?v1 . FILTER(?v1>0) .', '')
        query = query.replace(' UNION { ?r ', ' UNION { ?0 ')
        query = query.replace(' { ?r ', ' { SELECT ?r WHERE { { ?r <http://www.semanticdesktop.org/ontologies/2007/08/15/nao#userVisible> 1 . ?r ')
        query = query.replace(' UNION { ?0 ', ' UNION { ?r ')
        query = query.replace(' } .', '}}} .')
        query = query.replace('.}}} .}}} . }', '. }}} . }')

        # Removing ?_n_f_t_m_ex_ field to avoid duplicates in the result.
        query = "SELECT DISTINCT ?r " + query[query.find("where"):]
        query = query.replace('SELECT DISTINCT ?r where { { { ', 'SELECT DISTINCT ?r WHERE { { ')

    elif hackLevel.lower() == 'e0':
        # Removing ?_n_f_t_m_ex_ field to avoid duplicates in the result.
        query = "SELECT DISTINCT ?r " + query[query.find("where"):]

    return query
