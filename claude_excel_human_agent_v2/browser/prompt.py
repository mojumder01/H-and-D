HD_SECTIONS='''HIGHLIGHTS_HTML
<ul>
<li>...</li>
</ul>

DESCRIPTION_HTML
<p>...</p>
<p>...</p>'''

HD_RULES='''- Use only facts supported by the supplied data.
- Never invent specifications, quantity, material, dimensions, compatibility, warranty, or claims.
- Product Type must be the first highlight.
- Highlights use only ul/li.
- Description uses only p tags.'''

WEIGHT_SECTIONS='''WEIGHT_KG
<a single decimal number, e.g. 0.35>'''

WEIGHT_RULES='''- Estimate the product's total shipping weight in kilograms, based on the product type, material, size, and quantity/pack size described.
- If multiple pieces/units are included (e.g. "6 pcs set"), estimate the combined weight of all pieces together.
- Output ONLY a plain decimal number for WEIGHT_KG, rounded to 2 decimal places. Do not include the word "kg", any other unit, or any extra text.
- If there truly isn't enough information to estimate at all, output exactly: unknown'''

def build_prompt(row,tasks):
    sections=[]
    rules=[]
    if "hd" in tasks:
        sections.append(HD_SECTIONS)
        rules.append(HD_RULES)
    if "weight" in tasks:
        sections.append(WEIGHT_SECTIONS)
        rules.append(WEIGHT_RULES)

    return f'''Create Cartup-ready product content for this product.

PRODUCT NAME:
{row.get("Product Name","")}

EXISTING HIGHLIGHTS:
{row.get("Highlights","")}

EXISTING DESCRIPTION:
{row.get("Description","")}

Return EXACTLY these sections and nothing else:

{(chr(10)*2).join(sections)}

Rules:
{chr(10).join(rules)}
- No markdown, tables, or images.
- Do not use any preamble like "Here is the output" - start directly with the first requested section.
'''
