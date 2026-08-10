def build_prompt(row):
    return f'''Create Cartup-ready HTML for this product.

PRODUCT NAME:
{row.get("Product Name","")}

EXISTING HIGHLIGHTS:
{row.get("Highlights","")}

EXISTING DESCRIPTION:
{row.get("Description","")}

Return EXACTLY these sections and nothing else:

HIGHLIGHTS_HTML
<ul>
<li>...</li>
</ul>

DESCRIPTION_HTML
<p>...</p>
<p>...</p>

Rules:
- Use only facts supported by the supplied data.
- Never invent specifications, quantity, material, dimensions, compatibility, warranty, or claims.
- Product Type must be the first highlight.
- Highlights use only ul/li.
- Description uses only p tags.
- No markdown, tables, images, or explanation.
- Do not use any preamble like "Here is the HTML" - start directly with HIGHLIGHTS_HTML.
'''
