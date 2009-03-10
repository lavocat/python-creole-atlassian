# -*- coding: utf-8 -*-

import re
import inspect
import warnings
from HTMLParser import HTMLParser
from xml.sax.saxutils import escape
from htmlentitydefs import entitydefs



BLOCK_TAGS = (
    "address", "blockquote", "center", "dir", "div", "dl", "fieldset",
    "form",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "hr", "ins", "isindex", "menu", "noframes", "noscript",
    "ul", "ol", "li", "table",
    "p", "pre",
    "br"
)

#------------------------------------------------------------------------------

# Pass-through all django template blocktags
pass_block_re = r'''
    (?P<pass_block>
        [\s\n]*
        {% \s* (?P<pass_block_start>.+?) \s* .*? \s* %}
        (\n|.)*?
        {% \s* end(?P=pass_block_start) \s* %}
        [\s\n]*
    )'''
pre_block_re = r'''
    ^<pre> \s* $
    (?P<pre_block>
        (\n|.)*?
    )
    ^</pre> \s* $
    [\s\n]*
'''
block_re = re.compile(
    '|'.join([
        pass_block_re,
        pre_block_re,
    ]),
    re.VERBOSE | re.UNICODE | re.MULTILINE
)

#------------------------------------------------------------------------------

inline_django_re = r'''
    (?P<django_tag>
        [\s\n]*
        {% [^\n]+? %}
        [\s\n]*
    )
'''
pre_inline_re = r'''
    <pre>
    (?P<pre_inline>
        (\n|.)*?
    )
    </pre>
'''
inline_re = re.compile(
    '|'.join([
        pre_inline_re,
        inline_django_re,
    ]),
    re.VERBOSE | re.UNICODE
)

#------------------------------------------------------------------------------

headline_tag_re = re.compile(r"h(\d)", re.UNICODE)









class DocNode:
    """
    A node in the document.
    """
    def __init__(self, kind='', parent=None, attrs=[], content=None, \
                                                                    level=None):
        self.kind = kind

        self.children = []
        self.parent = parent
        if self.parent is not None:
            self.parent.children.append(self)

        self.attrs = dict(attrs)
        self.content = content
        self.level = level

    def get_attrs_as_string(self):
        """
        FIXME!
        """
        attr_list = []
        for key, value in self.attrs.iteritems():
            if isinstance(value, unicode):
                value = value.encode("utf-8")
            attr_list.append("%s=%r" % (key, value))
        return " ".join(attr_list).replace("'", '"')

    def __str__(self):
        return "<DocNode %s: %r>" % (self.kind, self.content)

    def __repr__(self):
        return u"<DocNode %s: %r>" % (self.kind, self.content)

    def debug(self):
        print "_"*80
        print "\tDocNode - debug:"
        print "str(): %s" % self
        print "attributes:"
        for i in dir(self):
            if i.startswith("_") or i == "debug":
                continue
            print "%20s: %r" % (i, getattr(self, i, "---"))


class DebugList(list):
    def __init__(self, html2creole):
        self.html2creole = html2creole
        super(DebugList, self).__init__()

    def append(self, item):
#        for stack_frame in inspect.stack(): print stack_frame

        line, method = inspect.stack()[1][2:4]
        msg = "%-8s   append: %-35r (%-15s line:%s)" % (
            self.html2creole.getpos(), item,
            method, line
        )
        warnings.warn(msg)
        list.append(self, item)




strip_html_regex = re.compile(
    r"""
        \s*
        <
            (?P<end>/{0,1})       # end tag e.g.: </end>
            (?P<tag>[^ >]+)       # tag name
            .*?
            (?P<startend>/{0,1})  # closed tag e.g.: <closed />
        >
        \s*
    """,
    re.VERBOSE | re.MULTILINE | re.UNICODE
)

def strip_html(html_code):
    """
    Delete whitespace from html code. Doesn't recordnize preformatted blocks!

    >>> strip_html(u' <p>  one  \\n two  </p>')
    u'<p>one two</p>'

    >>> strip_html(u'<p><strong><i>bold italics</i></strong></p>')
    u'<p><strong><i>bold italics</i></strong></p>'

    >>> strip_html(u'<li>  Force  <br /> \\n linebreak </li>')
    u'<li>Force<br />linebreak</li>'

    >>> strip_html(u'one  <i>two \\n <strong>   \\n  three  \\n  </strong></i>')
    u'one <i>two <strong>three</strong> </i>'

    >>> strip_html(u'<p>a <unknown tag /> foobar  </p>')
    u'<p>a <unknown tag /> foobar</p>'
    
    >>> strip_html(u'<p>a <pre> preformated area </pre> foo </p>')
    u'<p>a<pre>preformated area</pre>foo</p>'
    """
    def strip_tag(match):
        block        = match.group(0)
        end_tag      = match.group("end") in ("/", u"/")
        startend_tag = match.group("startend") in ("/", u"/")
        tag          = match.group("tag")

#        print "_"*40
#        print match.groupdict()
#        print "block.......: %r" % block
#        print "end_tag.....:", end_tag
#        print "startend_tag:", startend_tag
#        print "tag.........: %r" % tag

        if tag in BLOCK_TAGS:
            return block.strip()

        space_start = block.startswith(" ")
        space_end = block.endswith(" ")

        result = block.strip()

        if end_tag:
            # It's a normal end tag e.g.: </strong>
            if space_start or space_end:
                result += " "
        elif startend_tag:
            # It's a closed start tag e.g.: <br />

            if space_start: # there was space before the tag
                result = " " + result

            if space_end: # there was space after the tag
                result += " "
        else:
            # a start tag e.g.: <strong>
            if space_start or space_end:
                result = " " + result

        return result

    data = html_code.strip()
    clean_data = " ".join([line.strip() for line in data.split("\n")])
    clean_data = strip_html_regex.sub(strip_tag, clean_data)
    return clean_data



space_re = re.compile(r"^(\s*)(.*?)(\s*)$", re.DOTALL)
def clean_whitespace(txt):
    """
    Special whitespaces cleanup, for django tags and blocktags.

    >>> clean_whitespace(u"\\n\\nfoo bar\\n\\n")
    u'foo bar\\n'

    >>> clean_whitespace(u"   foo bar  \\n  \\n")
    u' foo bar\\n'

    >>> clean_whitespace(u" \\n \\n  foo bar   ")
    u' foo bar '

    >>> clean_whitespace(u"foo   bar")
    u'foo   bar'
    """
    def cleanup(match):
        start, txt, end = match.groups()

        if " " in start:
            start = " "
        else:
            start = ""

        if "\n" in end:
            end = "\n"
        elif " " in end:
            end = " "

        return start + txt + end

    return space_re.sub(cleanup, txt)




class Html2CreoleParser(HTMLParser):
    # placeholder html tag for pre cutout areas:
    _block_placeholder = "blockdata"
    _inline_placeholder = "inlinedata"

    def __init__(self, debug=False):
        HTMLParser.__init__(self)

        self.debugging = debug
        if self.debugging:
            warnings.warn(
                message="Html2Creole debug is on! warn every data append."
            ) 
            self.result = DebugList(self)
        else:
            self.result = []

        self.blockdata = []

        self.root = DocNode("document", None)
        self.cur = self.root

        self.__list_level = 0

    def _pre_cut(self, data, type, placeholder):
        if self.debugging:
            print "append blockdata: %r" % data
        assert isinstance(data, unicode), "blockdata is not unicode"
        self.blockdata.append(data)
        id = len(self.blockdata)-1
        return '<%s type="%s" id="%s" />' % (placeholder, type, id)

    def _pre_pre_inline_cut(self, groups):
        return self._pre_cut(groups["pre_inline"], "pre", self._inline_placeholder)

    def _pre_pre_block_cut(self, groups):
        return self._pre_cut(groups["pre_block"], "pre", self._block_placeholder)

    def _pre_pass_block_cut(self, groups):
        content = groups["pass_block"].strip()
        return self._pre_cut(content, "pass", self._block_placeholder)

    _pre_pass_block_start_cut = _pre_pass_block_cut

    def _pre_django_tag_cut(self, groups):
        content = groups["django_tag"]
        content = clean_whitespace(content)
        return self._pre_cut(content, "django_tag", self._inline_placeholder)

    def _pre_cut_out(self, match):
        groups = match.groupdict()
        for name, text in groups.iteritems():
            if text is not None:
                if self.debugging:
                    print "%15s: %r (%r)" % (name, text, match.group(0))
                method = getattr(self, '_pre_%s_cut' % name)
                return method(groups)

#        data = match.group("data")


    def feed(self, raw_data):
        data = unicode(raw_data)
        data = data.strip()

        # cut out <pre>, <tt> areas or django block tag areas
        data = block_re.sub(self._pre_cut_out, data)
        data = inline_re.sub(self._pre_cut_out, data)

        # Delete whitespace from html code
        data = strip_html(data)

        if self.debugging:
            print "_"*79
            print "raw data:"
            print repr(raw_data)
            print " -"*40
            print "cleaned data:"
            print data
            print "-"*79
#            print clean_data.replace(">", ">\n")
#            print "-"*79

        HTMLParser.feed(self, data)

        return self.root


    #-------------------------------------------------------------------------

    def _upto(self, node, kinds):
        """
        Look up the tree to the first occurence
        of one of the listed kinds of nodes or root.
        Start at the node node.
        """
        while node is not None and node.parent is not None:
            node = node.parent
            if node.kind in kinds:
                break

        return node

    def _go_up(self):
        kinds = list(BLOCK_TAGS) + ["document"]
        self.cur = self._upto(self.cur, kinds)

    #-------------------------------------------------------------------------

    def handle_starttag(self, tag, attrs):
        self.debug_msg("starttag", "%r atts: %s" % (tag, attrs))

        headline = headline_tag_re.match(tag)
        if headline:
            self.cur = DocNode(
                "headline", self.cur, level = int(headline.group(1))
            )
            return

        if tag in ("li", "ul", "ol"):
            if tag in ("ul", "ol"):
                self.__list_level += 1
            self.cur = DocNode(tag, self.cur, attrs, level=self.__list_level)
        elif tag == "img":
            # Work-a-round if a image tag is not marked as startendtag:
            # wrong: <img src="/image.jpg"> doesn't work if </img> not exist
            # right: <img src="/image.jpg" />
            DocNode(tag, self.cur, attrs)
        else:
            self.cur = DocNode(tag, self.cur, attrs)

    def handle_data(self, data):
        self.debug_msg("data", "%r" % data)
        DocNode("data", self.cur, content = data)

    def handle_charref(self, name):
        self.debug_msg("charref", "%r" % name)
        DocNode("charref", self.cur, content=name)

    def handle_entityref(self, name):
        self.debug_msg("entityref", "%r" % name)
        DocNode("entityref", self.cur, content=name)

    def handle_startendtag(self, tag, attrs):
        self.debug_msg("startendtag", "%r atts: %s" % (tag, attrs))
        attr_dict = dict(attrs)
        if tag in (self._block_placeholder, self._inline_placeholder):
            id = int(attr_dict["id"])
#            block_type = attr_dict["type"]
            DocNode(
                "%s_%s" % (tag, attr_dict["type"]),
                self.cur,
                content = self.blockdata[id],
#                attrs = attr_dict
            )
        else:
            DocNode(tag, self.cur, attrs)

    def handle_endtag(self, tag):
        self.debug_msg("endtag", "%r" % tag)
        self.debug_msg("get_starttag_text", "%r" % self.get_starttag_text())

        if tag in ("ul", "ol"):
            self.__list_level -= 1

        if tag in BLOCK_TAGS:
            self._go_up()
        else:
            self.cur = self.cur.parent

    #-------------------------------------------------------------------------

    def debug_msg(self, method, txt):
        if not self.debugging:
            return
        print "%-8s %8s: %s" % (self.getpos(), method, txt)

    def debug(self, start_node=None):
        """
        Display the current document tree
        """
        print "_"*80

        if start_node == None:
            start_node = self.root
            print "  document tree:"
        else:
            print "  tree from %s:" % start_node

        print "="*80
        def emit(node, ident=0):
            for child in node.children:
                txt = u"%s%s" % (u" "*ident, child.kind)

                if child.content:
                    txt += ": %r" % child.content

                if child.attrs:
                    txt += " - attrs: %r" % child.attrs

                if child.level != None:
                    txt += " - level: %r" % child.level

                print txt
                emit(child, ident+4)
        emit(start_node)
        print "*"*80













entities_regex = re.compile(r"&([#\w]+);", re.UNICODE)


def deentitfy(text):
    """
    >>> deentitfy("a text with &gt;entity&lt;!")
    'a text with >entity<!'
    """
    def deentitfy(match):
        entity = match.group(1)
        return entitydefs[entity]

    return entities_regex.sub(deentitfy, text)



#------------------------------------------------------------------------------

RAISE_UNKNOWN_NODES = 1
HTML_MACRO_UNKNOWN_NODES = 2
ESCAPE_UNKNOWN_NODES = 3

class Html2CreoleEmitter(object):

    def __init__(self, document_tree, unknown_emit=ESCAPE_UNKNOWN_NODES, 
                                                                debug=False):
        self.root = document_tree
        
        if unknown_emit == RAISE_UNKNOWN_NODES:
            self.unknown_emit = self.raise_unknown_node
        elif unknown_emit == HTML_MACRO_UNKNOWN_NODES:
            self.unknown_emit = self.use_html_macro
        elif unknown_emit == ESCAPE_UNKNOWN_NODES:
            self.unknown_emit = self.escape_unknown_nodes
        else:
            raise AssertionError("wrong keyword argument 'unknown_emit'!")
            
        self.debugging = debug
        self.__inner_list = ""
        self.__mask_linebreak = False

    #--------------------------------------------------------------------------
    
    def raise_unknown_node(self, node):
        """
        Raise NotImplementedError on unknown tags.
        """
        raise NotImplementedError(
            "Node from type '%s' is not implemented!" % node.kind
        )
    
    def use_html_macro(self, node):
        """
        Use the <<html>> macro to mask unknown tags.
        """
        #node.debug()
        attrs = node.get_attrs_as_string()
        if attrs:
            attrs = " "+attrs
        
        tag_data = {
            "tag": node.kind,
            "attrs": attrs,
        }
        
        content = self.emit_children(node)
        if not content:
            # single tag
            return u"<<html>><%(tag)s%(attrs)s /><</html>>" % tag_data
            
        start_tag = u"<<html>><%(tag)s%(attrs)s><</html>>" % tag_data
        end_tag = u"<<html>></%(tag)s><</html>>" % tag_data
        
        return start_tag + content + end_tag
    
    def escape_unknown_nodes(self, node):
        """
        All unknown tags should be escaped.
        """
        #node.debug()
        attrs = node.get_attrs_as_string()
        if attrs:
            attrs = " "+attrs
        
        tag_data = {
            "tag": node.kind,
            "attrs": attrs,
        }
        
        content = self.emit_children(node)
        if not content:
            # single tag
            return escape(u"<%(tag)s%(attrs)s />" % tag_data)
            
        start_tag = escape(u"<%(tag)s%(attrs)s>" % tag_data)
        end_tag = escape(u"</%(tag)s>" % tag_data)
        
        return start_tag + content + end_tag
    
    #--------------------------------------------------------------------------

    def _escape_linebreaks(self, text):
        text = text.split("\n")
        lines = [line.strip() for line in text]
        return "\\\\".join(lines)

    #--------------------------------------------------------------------------

    def blockdata_pre_emit(self, node):
        """ pre block -> with newline at the end """
        return u"{{{%s}}}\n" % deentitfy(node.content)
    def inlinedata_pre_emit(self, node):
        """ a pre inline block -> no newline at the end """
        return u"{{{%s}}}" % deentitfy(node.content)

    def blockdata_pass_emit(self, node):
        return u"%s\n\n" % node.content
        return node.content

    def inlinedata_django_tag_emit(self, node):
        return node.content

    #--------------------------------------------------------------------------

    def data_emit(self, node):
        #~ node.debug()
        return node.content

    def entityref_emit(self, node):
        return unicode(entitydefs[node.content])

    #--------------------------------------------------------------------------

    def p_emit(self, node):
        return u"%s\n\n" % self.emit_children(node)

    def br_emit(self, node):
        if self.__inner_list != "":
            return u"\\\\"
        else:
            return u"\n"

    def headline_emit(self, node):
        return u"%s %s\n" % (u"="*node.level, self.emit_children(node))

    #--------------------------------------------------------------------------

    def _typeface(self, node, key):
        return key + self.emit_children(node) + key

    def strong_emit(self, node):
        return self._typeface(node, key="**")
    b_emit = strong_emit
    big_emit = strong_emit

    def i_emit(self, node):
        return self._typeface(node, key="//")
    em_emit = i_emit
    
    def tt_emit(self, node):
        return self._typeface(node, key="##")
    def sup_emit(self, node):
        return self._typeface(node, key="^^")
    def sub_emit(self, node):
        return self._typeface(node, key=",,")
    def u_emit(self, node):
        return self._typeface(node, key="__")
    def small_emit(self, node):
        return self._typeface(node, key="--")
    def del_emit(self, node):
        return self._typeface(node, key="~~")
    strike_emit = del_emit 

    #--------------------------------------------------------------------------

    def hr_emit(self, node):
        return u"----\n\n"

    def a_emit(self, node):
        link_text = self.emit_children(node)
        url = node.attrs["href"]
        if link_text == url:
            return u"[[%s]]" % url
        else:
            return u"[[%s|%s]]" % (url, link_text)

    def img_emit(self, node):
        return u"{{%(src)s|%(alt)s}}" % node.attrs

    #--------------------------------------------------------------------------

    def li_emit(self, node):
        content = self.emit_children(node)
        return u"\n%s %s" % (self.__inner_list, content)

    def _list_emit(self, node, list_type):

        if self.__inner_list == "": # Srart a new list
            self.__inner_list = list_type
        else:
            start = False
            self.__inner_list += list_type

        content = u"%s" % self.emit_children(node)

        self.__inner_list = self.__inner_list[:-1]

        if self.__inner_list == "": # Srart a new list
            return content.strip() + "\n\n"
        else:
            return content

    def ul_emit(self, node):
        return self._list_emit(node, list_type="*")

    def ol_emit(self, node):
        return self._list_emit(node, list_type="#")

    #--------------------------------------------------------------------------

    def _format_table(self, table_content):
        """
        Format a table block, so every cell has the same width.
        """
        # Split and preformat every table cell
        cells = []
        for line in table_content.strip().splitlines():
            line_cells = []
            for cell in line.split("|"):
                cell = cell.strip()
                if cell != "":
                    if cell.startswith("="):
                        cell += " " # Headline
                    else:
                        cell = " %s " % cell # normal cell
                line_cells.append(cell)
            cells.append(line_cells)

        # Build a list of max len for every column
        widths = [max(map(len, col)) for col in zip(*cells)]

        # Join every line with ljust
        lines = []
        for row in cells:
            cells = [cell.ljust(width) for cell, width in zip(row, widths)]
            lines.append("|".join(cells))

        return "\n".join(lines)

    def table_emit(self, node):
        table_content = self.emit_children(node)

        # Optimize the table output
        result = self._format_table(table_content)

        return u"%s\n" % result

    def tr_emit(self, node):
        return u"%s|\n" % self.emit_children(node)

    def th_emit(self, node):
        content = self.emit_children(node)
        content = self._escape_linebreaks(content)
        return u"|= %s" % content

    def td_emit(self, node):
        content = self.emit_children(node)
        content = self._escape_linebreaks(content)
        return u"| %s" % content

    #--------------------------------------------------------------------------

    def document_emit(self, node):
        return self.emit_children(node)

    def emit_children(self, node):
        """Emit all the children of a node."""
        result = []
        for child in node.children:
            content = self.emit_node(child)
            assert isinstance(content, unicode)
            result.append(content)
        return u"".join(result)
        #~ return u''.join([self.emit_node(child) for child in node.children])

    def emit_node(self, node):
        """Emit a single node."""
        self.debug_msg("emit_node", "%s: %r" % (node.kind, node.content))

        method_name = "%s_emit" % node.kind
        emit_method = getattr(self, method_name, self.unknown_emit)

        content = emit_method(node)
        if not isinstance(content, unicode):
            raise AssertionError(
                "Method '%s' returns no unicode (returns: %r)" % (
                    method_name, content
                )
            )
        return content

    def emit(self):
        """Emit the document represented by self.root DOM tree."""
        result = self.emit_node(self.root)
        return result.strip() # FIXME

    #-------------------------------------------------------------------------

    def debug_msg(self, method, txt):
        if not self.debugging:
            return
        print "%13s: %s" % (method, txt)






if __name__ == '__main__':
    import doctest
    doctest.testmod()
    print "doc test done."

#    import sys;sys.exit()

    data = """
<p>111 <x>foo</x> 222<br />
333<x foo1="bar1">foobar</x>444</p>

<p>555<x />666</p>"""

#    print data.strip()
    h2c = Html2CreoleParser(
        debug=True
    )
    document_tree = h2c.feed(data)
    h2c.debug()

    e = Html2CreoleEmitter(document_tree,
        debug=True
    )
    content = e.emit()
    print "*"*79
    print content
    print "*"*79
    print content.replace(" ", ".").replace("\n", "\\n\n")
