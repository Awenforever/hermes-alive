"""Exercise rendered citation syntax, not source truth or channel delivery."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel.markdown_citations import citation_markup,has_inline_citation
from alive_kernel.semantic_rendering import SemanticAtom,SemanticAtomKind


def test():
    url='https://example.invalid/a_long_paper_(version_2).pdf'
    good=(citation_markup(url), '[论文](<'+url+'>)',
        '一个具体发现，见[**论文**](<'+url+'>)。',
        '[研究][source]\n\n[source]: <'+url+'>',
        '> [研究](<'+url+'>)', '[`论文`](<'+url+'>)',
        '[论文](<'+url+'>)\n\n```sh\ncurl '+url+'\n```',
        '[论文](<'+url+'>)\n\n`'+url+'`',
        '<'+url+'>，也可看[论文](<'+url+'>)')
    bad=(url,'论文：'+url,'<'+url+'>',
        '`[论文](<'+url+'>)`','```markdown\n[论文](<'+url+'>)\n```',
        '    [论文](<'+url+'>)', '\\[论文](<'+url+'>)',
        '![论文](<'+url+'>)', '[](<'+url+'>)',
        '[论文](https://example.invalid/other.pdf)',
        '<a href="'+url+'">论文</a>', '['+url+'](<'+url+'>)')
    for text in good:assert has_inline_citation(text,url),repr(text)
    for text in bad:assert not has_inline_citation(text,url),repr(text)
    long_url='https://example.invalid/'+('x'*(4096-len('https://example.invalid/')))
    atom=SemanticAtom('source-link',SemanticAtomKind.LINK,citation_markup(long_url),
        ('synthetic:evidence',),(long_url,))
    assert atom.protected_literals==(long_url,) and has_inline_citation(atom.text,long_url)
    for invalid in ('file:///synthetic/private.txt','https://example.invalid/<>','https://example.invalid/\n'):
        assert not has_inline_citation('A message '+invalid,invalid)
    assert not has_inline_citation('x'*256001,url)
    print('HERMES_ALIVE_MARKDOWN_CITATIONS_OK')


if __name__=='__main__':test()
