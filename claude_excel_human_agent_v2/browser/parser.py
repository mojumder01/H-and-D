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

def _match_hd_markers(text):
    h=re.search(r'HIGHLIGHTS_HTML\s*:?[ \t]*(.*?)(?=\n\s*DESCRIPTION_HTML\s*:?)',text,re.I|re.S)
    d=re.search(r'DESCRIPTION_HTML\s*:?[ \t]*(.*?)(?=\n\s*WEIGHT_KG\s*:?|\Z)',text,re.I|re.S)
    if h and d: return clean(h.group(1)),clean(d.group(1))
    return None,None

def _match_hd_headings(text):
    # Claude often ignores the literal HIGHLIGHTS_HTML/DESCRIPTION_HTML tokens
    # and instead replies with plain "Highlights"/"Description" headings, each
    # followed by a rendered code block (whose language label "html" shows up
    # as its own line in inner_text()). Match that shape too.
    h=re.search(r'^[ \t]*Highlights[ \t]*$\s*(?:^[ \t]*html[ \t]*$\s*)?(.*?)(?=^[ \t]*Description[ \t]*$|\Z)',text,re.I|re.M|re.S)
    d=re.search(r'^[ \t]*Description[ \t]*$\s*(?:^[ \t]*html[ \t]*$\s*)?(.*?)(?=^[ \t]*Weight(?:\s*\(kg\))?[ \t]*$|\Z)',text,re.I|re.M|re.S)
    if h and d:
        h=_trim_after_last_closing_tag(clean(h.group(1)),'</ul>')
        d=_trim_after_last_closing_tag(clean(d.group(1)),'</p>')
        return h,d
    return None,None

def _extract_hd(text):
    h,d=_match_hd_markers(text)
    if h is None or d is None:
        h,d=_match_hd_headings(text)
    if h is None or d is None:
        raise ValueError("Could not identify both HTML sections.")
    if "<ul" not in h.lower() or "<li" not in h.lower(): raise ValueError("Invalid highlights HTML.")
    if "<p" not in d.lower(): raise ValueError("Invalid description HTML.")
    return h,d

def _norm_weight(v):
    return "unknown" if v.strip().lower()=="unknown" else v.strip()

def _match_weight(text):
    m=re.search(r'WEIGHT_KG\s*:?[ \t]*([0-9]+(?:\.[0-9]+)?|unknown)',text,re.I)
    if m: return _norm_weight(m.group(1))
    # Claude replying with a plain "Weight"/"Weight (kg)" heading instead of
    # the literal marker - either on its own line followed by the value, or
    # inline as "Weight: 0.35". Anchored to a heading line so a stray mention
    # of "weight" inside the Highlights/Description HTML can't false-match.
    m=re.search(r'^[ \t]*Weight(?:\s*\(kg\))?[ \t]*:?[ \t]*$\s*(?:^[ \t]*kg[ \t]*$\s*)?([0-9]+(?:\.[0-9]+)?|unknown)',text,re.I|re.M)
    if m: return _norm_weight(m.group(1))
    m=re.search(r'^[ \t]*Weight(?:\s*\(kg\))?[ \t]*:[ \t]*([0-9]+(?:\.[0-9]+)?|unknown)[ \t]*$',text,re.I|re.M)
    if m: return _norm_weight(m.group(1))
    return None

def extract_fields(text,tasks):
    text=text.replace("\r\n","\n")
    result={}
    if "hd" in tasks:
        h,d=_extract_hd(text)
        result["highlights_html"]=h
        result["description_html"]=d
    if "weight" in tasks:
        w=_match_weight(text)
        if w is None:
            raise ValueError("Could not identify a weight value.")
        result["weight_kg"]=w
    return result
