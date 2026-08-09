import re
def clean(v):
    v=v.strip()
    v=re.sub(r'^```(?:html)?\s*','',v,flags=re.I)
    v=re.sub(r'\s*```$','',v)
    return v.strip()
def extract_sections(text):
    text=text.replace("\r\n","\n")
    h=re.search(r'HIGHLIGHTS_HTML\s*:?[ \t]*(.*?)(?=\n\s*DESCRIPTION_HTML\s*:?)',text,re.I|re.S)
    d=re.search(r'DESCRIPTION_HTML\s*:?[ \t]*(.*)$',text,re.I|re.S)
    if not h or not d: raise ValueError("Could not identify both HTML sections.")
    h=clean(h.group(1)); d=clean(d.group(1))
    if "<ul" not in h.lower() or "<li" not in h.lower(): raise ValueError("Invalid highlights HTML.")
    if "<p" not in d.lower(): raise ValueError("Invalid description HTML.")
    return {"highlights_html":h,"description_html":d}
