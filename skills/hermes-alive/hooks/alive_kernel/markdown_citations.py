"""Validate a bound citation's Markdown presentation without rewriting prose.

This establishes a usable labelled link, not factual support, delivery or URL
safety. The host separately owns those boundaries. No IO or model call occurs.
"""
from urllib.parse import urlsplit

from markdown_it import MarkdownIt


INLINE_CITATION_POLICY = 'canonical_source_inline_v2'


def citation_markup(url):
    """Exact destination with a neutral label; the author may choose another label."""
    if not isinstance(url,str) or not url or len(url)>4096 or any(c in url for c in '<>\r\n'):
        raise ValueError('source destination cannot be represented as an inline citation')
    if urlsplit(url).scheme not in ('http','https'):
        raise ValueError('source citation requires a public HTTP destination')
    return '[来源](<'+url+'>)'


def has_inline_citation(text, url):
    """Require a real labelled link, not markup quoted in code or a raw URL.

    CommonMark parsing distinguishes a link from escaped text, fences, image
    syntax and malformed brackets. Reference-style links and formatted labels
    are also valid. The original canonical URL is never shortened or replaced.
    """
    if not isinstance(text,str) or not 0<len(text)<=256000:
        return False
    try:
        citation_markup(url)
        parser=MarkdownIt('commonmark',{'html':False,'linkify':False})
        target=parser.normalizeLink(url)
        found=False
        for block in parser.parse(text):
            if block.type!='inline':continue
            matching=False;label=[];auto=False
            for token in block.children or ():
                if token.type=='link_open':
                    matching=token.attrGet('href')==target
                    auto=token.markup=='autolink' or token.info=='auto'
                    label=[]
                elif token.type=='link_close':
                    if matching:
                        visible=''.join(label).strip()
                        if not auto and visible and visible not in (url,parser.normalizeLinkText(url)):
                            found=True
                    matching=False;label=[]
                elif token.type in ('text','code_inline'):
                    if matching:label.append(token.content)
                elif matching and token.type in ('softbreak','hardbreak'):
                    label.append(' ')
        return found
    except (ValueError,TypeError):
        return False
