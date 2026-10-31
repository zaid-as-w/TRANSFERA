"""TRANSFERA Official Geometric Football Brand Logo Component."""


def get_transfera_logo_svg(size: int = 38) -> str:
    """Return an inline SVG of the geometric TRANSFERA shield & stylized T symbol for light themes."""
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" style="filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.08));">
  <!-- Geometric Hexagonal Football Outer Shield -->
  <polygon points="50,4 92,26 92,74 50,96 8,74 8,26" stroke="#02BFD0" stroke-width="4.5" fill="#FFFFFF" stroke-linejoin="round"/>

  <!-- Subtle Internal Facet / Football Mesh Lines -->
  <polygon points="50,14 82,31 82,69 50,86 18,69 18,31" stroke="rgba(2, 191, 208, 0.25)" stroke-width="1.8" fill="#F8F9FA"/>
  <line x1="50" y1="4" x2="50" y2="14" stroke="#02BFD0" stroke-width="2"/>
  <line x1="92" y1="26" x2="82" y2="31" stroke="#02BFD0" stroke-width="2"/>
  <line x1="92" y1="74" x2="82" y2="69" stroke="#02BFD0" stroke-width="2"/>
  <line x1="50" y1="96" x2="50" y2="86" stroke="#02BFD0" stroke-width="2"/>
  <line x1="8" y1="74" x2="18" y2="69" stroke="#02BFD0" stroke-width="2"/>
  <line x1="8" y1="26" x2="18" y2="31" stroke="#02BFD0" stroke-width="2"/>

  <!-- Stylized Geometric T + Football Motion Chevron -->
  <!-- Top Bar of T -->
  <path d="M26,30 L74,30 L71,38 L55,38 L55,72 L45,72 L45,38 L29,38 Z" fill="#17212B"/>
  <!-- Aqua Accent Corner / Velocity Wings -->
  <polygon points="50,30 50,44 58,38" fill="#02BFD0"/>
  <circle cx="50" cy="79" r="3.5" fill="#02BFD0"/>
</svg>"""


def get_transfera_brand_html(compact: bool = False) -> str:
    """Return branded HTML header with logo, title, and official tagline for clean light theme."""
    logo_svg = get_transfera_logo_svg(size=32 if compact else 42)
    if compact:
        return (
            '<div style="display:flex;align-items:center;gap:0.75rem;">'
            f"{logo_svg}"
            "<div>"
            "<div style=\"font-size:1.15rem;font-weight:800;letter-spacing:1px;color:#17212B;font-family:'Manrope',sans-serif;line-height:1;\">"
            'TRANSFER<span style="color:#02BFD0;">A</span>'
            "</div>"
            '<div style="font-size:0.6rem;font-weight:700;letter-spacing:0.8px;color:#66727D;text-transform:uppercase;margin-top:2px;">'
            "MARKET INTELLIGENCE"
            "</div>"
            "</div>"
            "</div>"
        )
    return (
        '<div style="text-align:center;padding:0.2rem 0 0.6rem 0;">'
        '<div style="display:flex;justify-content:center;margin-bottom:0.5rem;">'
        f"{logo_svg}"
        "</div>"
        "<div style=\"font-size:1.4rem;font-weight:800;letter-spacing:1.5px;color:#17212B;font-family:'Manrope',sans-serif;line-height:1.1;\">"
        'TRANSFER<span style="color:#02BFD0;">A</span>'
        "</div>"
        '<div style="font-size:0.62rem;font-weight:700;letter-spacing:1.2px;color:#02BFD0;text-transform:uppercase;margin-top:0.3rem;">'
        "THE GLOBAL FOOTBALL MARKET INTELLIGENCE"
        "</div>"
        '<div style="font-size:0.58rem;font-weight:600;letter-spacing:1px;color:#8A959E;margin-top:0.2rem;">'
        "THE GLOBAL GAME. DECODED."
        "</div>"
        "</div>"
    )
