import re

def clean(v):
    v=v.strip()
    v=re.sub(r'^```(?:html)?\s*','',v,flags=re.I)
    v=re.sub(r'\s*```$','',v)
    v=re.sub(r'^html[ \t]*\n','',v,flags=re.I)
    return v.strip()

def _trim_after_last_closing_tag(v,tag):
    # Claude sometimes appends a trailing note after the code block (e.g.
    # "Note: I dropped X since it wasn't supported by the source data.").
    # Drop anything after the last real closing tag so that prose doesn't
    # end up inside the Excel HTML columns.
    idx=v.lower().rfind(tag)
    return v[:idx+len(tag)] if idx!=-1 else v

def _match_markers(text):
    h=re.search(r'HIGHLIGHTS_HTML\s*:?[ \t]*(.*?)(?=\n\s*DESCRIPTION_HTML\s*:?)',text,re.I|re.S)
    d=re.search(r'DESCRIPTION_HTML\s*:?[ \t]*(.*)$',text,re.I|re.S)
    if h and d: return clean(h.group(1)),clean(d.group(1))
    return None,None

def _match_headings(text):
    # Claude often ignores the literal HIGHLIGHTS_HTML/DESCRIPTION_HTML tokens
    # and instead replies with plain "Highlights"/"Description" headings, each
    # followed by a rendered code block (whose language label "html" shows up
    # as its own line in inner_text()). Match that shape too.
    h=re.search(r'^[ \t]*Highlights[ \t]*$\s*(?:^[ \t]*html[ \t]*$\s*)?(.*?)(?=^[ \t]*Description[ \t]*$|\Z)',text,re.I|re.M|re.S)
    d=re.search(r'^[ \t]*Description[ \t]*$\s*(?:^[ \t]*html[ \t]*$\s*)?(.*)\Z',text,re.I|re.M|re.S)
    if h and d:
        h=_trim_after_last_closing_tag(clean(h.group(1)),'</ul>')
        d=_trim_after_last_closing_tag(clean(d.group(1)),'</p>')
        return h,d
    return None,None

def extract_sections(text):
    text=text.replace("\r\n","\n")
    h,d=_match_markers(text)
    if h is None or d is None:
        h,d=_match_headings(text)
    if h is None or d is None:
        raise ValueError("Could not identify both HTML sections.")
    if "<ul" not in h.lower() or "<li" not in h.lower(): raise ValueError("Invalid highlights HTML.")
    if "<p" not in d.lower(): raise ValueError("Invalid description HTML.")
    return {"highlights_html":h,"description_html":d}
