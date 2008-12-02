# -*- coding: utf-8 -*-

from creole import Parser
from creole2html import HtmlEmitter
from html2creole import Html2CreoleParser, Html2CreoleEmitter



def creole2html(markup_string, debug=False):
    """
    convert creole markup into html code

    >>> creole2html(u'This is **creole //markup//**!')
    u'<p>This is <strong>creole <i>markup</i></strong>!</p>\\n'
    """
    # Create document tree from creole markup
    document = Parser(markup_string).parse()
    if debug:
        document.debug()
    
    # Build html code from document tree
    return HtmlEmitter(document, verbose=debug).emit()



def html2creole(html_string, debug=False):
    """
    convert html code into creole markup

    >>> html2creole(u'<p>This is <strong>creole <i>markup</i></strong>!</p>')
    u'This is **creole //markup//**!'
    """
    # create the document tree from html code
    h2c = Html2CreoleParser(debug)
    document_tree = h2c.feed(html_string)
    if debug:
        h2c.debug()
    
    # create creole markup from the document tree
    emitter = Html2CreoleEmitter(document_tree, debug)
    return emitter.emit()


if __name__ == '__main__':
    import doctest
    doctest.testmod()#verbose=True)