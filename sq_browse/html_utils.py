import re
from lxml import etree
from collections import deque


WHITESPACE_AROUND_LINEBREAK = re.compile(r"[ \t]*\n[ \t]*")
FORCED_LINE_BREAK = object()
IGNORE_CSS_CLASSES = ("hidden", "consent", "cookie", "banner", "overlay", "widget", "menu")
IGNORE_ELEMS = {"script", "style", etree.Comment, "meta", "head", "svg", "nav", "figcaption", "aside", "form", "footer"}
BLOCKS = {'address', 'article', 'aside', 'blockquote', 'canvas', 'dd', 'div', 'nav', 'dl', 'dt', 'fieldset',
          'figcaption', 'figure', 'footer', 'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'header', 'hr', 'li', 'main',
          'noscript', 'ol', 'p', 'pre', 'section', 'table', 'tfoot', 'ul', 'video'}
INLINES = {'a', 'abbr', 'acronym', 'b', 'bdo', 'big', 'br', 'button', 'cite', 'code', 'dfn', 'em', 'i', 'img', 'input',
           'kbd', 'label', 'map', 'object', 'output', 'q', 'samp', 'script', 'select', 'small', 'span', 'strong', 'sub',
           'sup', 'textarea', 'time', 'tt', 'var'}
VISIBLE_ELEMS = BLOCKS | INLINES | {"body", "html"}
INDENTS = {"ul", "ol"}


def is_essentially_block(elem):
    """Returns True if the given element acts as a block element.

    Can be true, even if the given element is an inline element. E.g. when it is embedded between two block elements.
    """
    if elem.tag in BLOCKS:
        return True

    no_inline_next = elem.getnext() is None or elem.getnext().tag in BLOCKS
    no_inline_prev = elem.getprevious() is None or elem.getprevious().tag in BLOCKS

    if elem.getparent() is None:
        return True

    if no_inline_next and no_inline_prev and (
            not (elem.getparent().text or "").strip() and is_essentially_block(elem.getparent())):
        return True

    return False


def render_text(s):
    """Return the given string after applying HTML's whitespace rules.

    See https://developer.mozilla.org/en-US/docs/Web/API/Document_Object_Model/Whitespace for further information.
    """
    s = str(s)
    s = WHITESPACE_AROUND_LINEBREAK.sub("\n", s)
    s = s.replace("\r\n", "\n").replace("\t", " ").replace("\n", " ")

    return s


def should_be_ignored(elem):
    """Return True if the element irrelevant or hidden."""
    if elem.tag in IGNORE_ELEMS:
        return True

    css_classes = elem.attrib.get("class", "").split(" ")
    is_hidden_by_attr = "hidden" in elem.attrib
    is_hidden_by_css = getattr(elem, "style", {}).get("visibility", "") == "hidden"
    blacklisted_class = any([css_class in css_classes for css_class in IGNORE_CSS_CLASSES])

    return is_hidden_by_attr or is_hidden_by_css or blacklisted_class


def get_text(elem):
    """Convert lxml element to text."""
    if should_be_ignored(elem):
        return ""

    leading_text_node = elem.text or ""
    context = "block" if any(child.tag in BLOCKS for child in elem) else "inline"

    leading_text_node = render_text(leading_text_node)
    texts = deque([leading_text_node])

    for child in elem:
        if should_be_ignored(child):
            continue

        if child.tag in ("span", "a") and is_essentially_block(child):
            continue

        texts.append(get_text(child))

        if child.tag == "br":
            tail = render_text(child.tail or "").lstrip()
            texts.append(FORCED_LINE_BREAK)
            texts.append(tail)
        elif child.tail:
            texts.append(render_text(child.tail or ""))

    if context == "inline":
        text = "".join(["\n" if t is FORCED_LINE_BREAK else t for t in texts])

        text = re.sub(r" +", " ", text)
        # text = text.strip()

        return text

    if context == "block":
        text = "\n\n".join(["" if t is FORCED_LINE_BREAK else t for t in texts if t is FORCED_LINE_BREAK or t.strip()])

        return text
