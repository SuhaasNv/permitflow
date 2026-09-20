#!/usr/bin/env python3
"""Generate the v0.4.0 prototype artboards (Design canvas, .dc.html) from the design tokens.

Usage: python3 build.py <out_dir>   (writes <out_dir>/project/*.dc.html and canvas.json)

Every screen is generated from the same helpers so the eleven artboards share one look:
the as-built PermitFlow tokens (docs/04-design/DESIGN_SYSTEM.md), Public Sans, one primary
action per screen, badges with a dot, no KPI grid, the shipped app shell. Edit this file,
never the output. Revised after the design critique of 20 Sep 2026 (UI_DESIGN.md, pass 3).
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from html import escape
from pathlib import Path

# Tokens (DESIGN_SYSTEM.md)
BG, SURFACE, SURFACE2 = "#F3F4F6", "#FFFFFF", "#F9FAFB"
LINE, LINE_STRONG = "#D9DEE5", "#AEB6C2"
TEXT, TEXT2, TEXT3 = "#1B2430", "#465060", "#616C7A"
PRIMARY, PRIMARY_HOVER, PRIMARY_SOFT, PRIMARY_LINE = "#A8192A", "#8A1422", "#FBEDEE", "#EFB8BE"
INK = "#1B2430"
FOCUS = "#175CD3"
NEUTRAL_SOFT = "#F2F4F7"
TONES = {
    "success": ("#067647", "#ECFDF3", "#A6E9C4"),
    "warning": ("#9A4A00", "#FFF6E5", "#F5CF86"),
    "error": ("#B42318", "#FEF3F2", "#F4B7B1"),
    "info": ("#175CD3", "#EEF4FF", "#B2CCFA"),
    "neutral": ("#475467", "#F2F4F7", "#D0D5DD"),
    "primary": (PRIMARY, PRIMARY_SOFT, PRIMARY_LINE),
}
SANS = "'Public Sans', system-ui, sans-serif"
MONO = "'IBM Plex Mono', ui-monospace, monospace"


def st(**kw: str | int | float) -> str:
    """Inline style from keyword arguments (underscores become hyphens)."""
    return "; ".join(f"{k.replace('_', '-')}: {v}" for k, v in kw.items() if v is not None)


def div(style: str, inner: str = "", tag: str = "div", **attrs: str) -> str:
    a = " ".join(f'{k.replace("_", "-")}="{escape(str(v), quote=True)}"' for k, v in attrs.items())
    return f'<{tag} style="{style}"{(" " + a) if a else ""}>{inner}</{tag}>'


def text(s: str, size: int = 15, line: int = 22, weight: int = 400, color: str = TEXT, extra: str = "", tag: str = "div") -> str:
    return div(st(font_size=f"{size}px", line_height=f"{line}px", font_weight=weight, color=color, margin=0) + (f"; {extra}" if extra else ""), escape(s), tag)


def mono(s: str, size: int = 13, color: str = TEXT) -> str:
    return div(st(font_family=MONO, font_size=f"{size}px", line_height="18px", color=color), escape(s), "span")


def icon(path: str, size: int = 16, color: str = "currentColor", stroke: float = 2) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" '
        f'style="flex-shrink: 0"><path d="{path}"></path></svg>'
    )


IC = {
    "check": "M20 6 9 17l-5-5",
    "flag": "M4 22V4h12l-1 4h5v10h-6l1-4H4",
    "camera": "M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2zM12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
    "upload": "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12",
    "bell": "M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0",
    "lock": "M19 11H5a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7a2 2 0 0 0-2-2zM7 11V7a5 5 0 0 1 10 0v4",
    "file": "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6",
    "home": "m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM9 22V12h6v10",
    "folder": "M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z",
    "queue": "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
    "chart": "M22 12h-4l-3 9L9 3l-3 9H2",
    "activity": "M12 20V10M18 20V4M6 20v-4",
    "users": "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75",
    "menu": "M3 12h18M3 6h18M3 18h18",
    "chevron": "m9 18 6-6-6-6",
    "info": "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 16v-4M12 8h.01",
    "wifi-off": "M1 1l22 22M16.7 11.4A10 10 0 0 0 12 10c-2 0-3.8.6-5.4 1.6M5 12.6a15.6 15.6 0 0 1 3.4-2.2M8.5 16.4a6 6 0 0 1 7 0M12 20h.01",
    "clock": "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 6v6l4 2",
    "eye": "M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
    "back": "m15 18-6-6 6-6",
    "search": "M21 21l-4.3-4.3M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0z",
}


# Primitives ---------------------------------------------------------------------------

def badge(label: str, tone: str, size: str = "md") -> str:
    fg, soft, line = TONES[tone]
    h = 28 if size == "lg" else 24
    fs = 13 if size == "lg" else 12
    dot = div(st(width="6px", height="6px", border_radius="999px", background=fg, flex_shrink=0), "", "span")
    return div(
        st(display="inline-flex", align_items="center", gap="6px", height=f"{h}px", padding="0 10px", border_radius="12px",
           background=soft, border=f"1px solid {line}", color=fg, font_size=f"{fs}px", font_weight=600, line_height="16px", white_space="nowrap"),
        dot + escape(label), "span")


def tag(label: str, kind: str = "neutral", icon_path: str | None = None) -> str:
    tones = {"neutral": ("#475467", "#F2F4F7", "#D0D5DD"), "changed": TONES["info"], "editable": TONES["warning"]}
    fg, soft, line = tones[kind]
    ic = icon(icon_path, 12, fg) if icon_path else ""
    return div(st(display="inline-flex", align_items="center", gap="4px", height="22px", padding="0 8px", border_radius="4px",
                  background=soft, border=f"1px solid {line}", color=fg, font_size="12px", font_weight=500, line_height="16px", white_space="nowrap"),
               ic + escape(label), "span")


def button(label: str, variant: str = "secondary", disabled_reason: str | None = None, size: str = "md", href: str | None = None, icon_path: str | None = None, full: bool = False) -> str:
    h = {"sm": 36, "md": 40, "lg": 44}[size]
    base = st(display="inline-flex", align_items="center", justify_content="center", gap="8px", height=f"{h}px", padding="0 16px",
              border_radius="6px", font_family=SANS, font_size="14px", font_weight=600, line_height="20px", cursor="pointer",
              white_space="nowrap", text_decoration="none", box_sizing="border-box", width="100%" if full else "auto")
    if disabled_reason is not None and variant == "ghost":
        look = st(background="transparent", color=TEXT3, border="1px solid transparent", cursor="not-allowed")
    elif disabled_reason is not None:
        look = st(background=NEUTRAL_SOFT, color=TEXT3, border="1px solid #D0D5DD", cursor="not-allowed")
    elif variant == "primary":
        look = st(background=PRIMARY, color="#FFFFFF", border=f"1px solid {PRIMARY}")
    elif variant == "ghost":
        look = st(background="transparent", color=TEXT2, border="1px solid transparent")
    else:
        look = st(background="#FFFFFF", color=TEXT, border=f"1px solid {LINE_STRONG}", box_shadow="0 1px 0 rgba(27,36,48,0.04)")
    inner = (icon(icon_path, 16) if icon_path else "") + escape(label)
    attrs: dict[str, str] = {}
    if disabled_reason is not None:
        attrs["title"] = disabled_reason
        attrs["aria-disabled"] = "true"
    if href:
        attrs["href"] = href
        return div(base + "; " + look, inner, "a", **attrs)
    attrs["type"] = "button"
    return div(base + "; " + look, inner, "button", **attrs)


def chip(label: str, on: bool, count: str = "", href: str | None = None, done: bool = False) -> str:
    """Filter or section chip: neutral-soft when selected, never primary-soft (pass 2 rule)."""
    inner = (icon(IC["check"], 12, TONES["success"][0]) if done else "") + escape(label) + (div(st(font_family=MONO, font_size="12px", color=TEXT3), count, "span") if count else "")
    style = st(display="inline-flex", align_items="center", gap="6px", height="36px", padding="0 12px", border_radius="6px",
               border=f"1px solid {TEXT if on else LINE_STRONG}", background=NEUTRAL_SOFT if on else SURFACE, color=TEXT if on else TEXT2,
               font_size="13px", font_weight=600 if on else 500, text_decoration="none", cursor="pointer", font_family=SANS)
    if href:
        return div(style, inner, "a", href=href, aria_current="true" if on else "false")
    return div(style, inner, "button", type="button", aria_pressed="true" if on else "false")


def surface(inner: str, pad: str = "20px", extra: str = "") -> str:
    return div(st(background=SURFACE, border=f"1px solid {LINE}", border_radius="10px", padding=pad, box_sizing="border-box") + (f"; {extra}" if extra else ""), inner)


def card_header(title: str, right: str = "", kicker: str = "") -> str:
    left = (text(kicker, 12, 16, 600, TEXT3, "text-transform: uppercase; letter-spacing: 0.08em") if kicker else "") + text(title, 16, 24, 600)
    return div(st(display="flex", align_items="center", justify_content="space-between", gap="16px", padding="14px 20px", border_bottom=f"1px solid {LINE}"),
               div(st(display="flex", flex_direction="column", gap="2px"), left) + div(st(display="flex", gap="8px", align_items="center"), right))


def panel(title: str, body: str, right: str = "", kicker: str = "", pad: str = "20px") -> str:
    return div(st(background=SURFACE, border=f"1px solid {LINE}", border_radius="10px", overflow="hidden"),
               card_header(title, right, kicker) + div(st(padding=pad), body))


def alert(tone: str, lead: str, body: str = "", icon_key: str = "info", action: str = "") -> str:
    fg, soft, line = TONES[tone]
    content = div(st(display="flex", flex_direction="column", gap="2px", flex_grow=1),
                  text(lead, 14, 20, 600, fg) + (text(body, 14, 20, 400, TEXT2) if body else ""))
    return div(st(display="flex", gap="12px", align_items="flex-start", padding="12px 16px", border_radius="6px", background=soft, border=f"1px solid {line}"),
               div(st(padding_top="2px", color=fg), icon(IC[icon_key], 16)) + content + action, role="status")


def def_list(rows: list[tuple[str, str]]) -> str:
    """Label left in text-2, value right-aligned and tabular, hairline between (the as-built document-checks panel)."""
    return div(st(display="flex", flex_direction="column"), "".join(
        div(st(display="flex", justify_content="space-between", gap="16px", padding="8px 0", border_bottom=f"1px solid {LINE}" if i < len(rows) - 1 else "none"),
            text(k, 14, 20, 400, TEXT2) + text(v, 14, 20, 600, TEXT, "font-variant-numeric: tabular-nums; text-align: right"))
        for i, (k, v) in enumerate(rows)), "dl")


def facts_row(rows: list[tuple[str, str]]) -> str:
    """The as-built key facts strip: lowercase labels, one row, full width."""
    return div(st(display="flex", gap="32px", flex_wrap="wrap", padding="14px 20px", background=SURFACE, border=f"1px solid {LINE}", border_radius="10px"),
               "".join(div(st(display="flex", flex_direction="column", gap="2px", min_width="0"), text(k, 12, 16, 400, TEXT3) + text(v, 14, 20, 600)) for k, v in rows))


def table(headers: list[str], rows: list[list[str]], widths: list[str] | None = None, font: int = 13, numeric: set[int] | None = None) -> str:
    numeric = numeric or set()

    def cell(c: str, i: int, head: bool = False) -> str:
        w = f"width: {widths[i]}; " if widths and i < len(widths) else ""
        align = "right" if i in numeric else "left"
        if head:
            return div(w + st(padding="10px 16px", text_align=align, font_size="12px", line_height="16px", font_weight=600, color=TEXT3,
                              text_transform="uppercase", letter_spacing="0.04em", background=SURFACE2, border_bottom=f"1px solid {LINE}"), escape(c), "th", scope="col")
        return div(w + st(padding="14px 16px", font_size=f"{font}px", line_height="20px", color=TEXT, border_bottom=f"1px solid {LINE}", vertical_align="top", text_align=align, font_variant_numeric="tabular-nums"), c, "td")
    thead = div("", div("", "".join(cell(h, i, True) for i, h in enumerate(headers)), "tr"), "thead")
    tbody = div("", "".join(div("", "".join(cell(c, i) for i, c in enumerate(r)), "tr") for r in rows), "tbody")
    return div(st(width="100%", border_collapse="collapse", font_family=SANS), thead + tbody, "table")


def bar(fraction: float, tone: str = "info", height: int = 6, width: str = "100%") -> str:
    fg = TONES[tone][0]
    return div(st(width=width, height=f"{height}px", background=NEUTRAL_SOFT, border_radius="999px", overflow="hidden"),
               div(st(width=f"{max(0, min(100, fraction * 100)):.0f}%", height="100%", background=fg, border_radius="999px"), ""))


def timeline(items: list[dict[str, str]]) -> str:
    out = []
    for i, it in enumerate(items):
        fg = TONES[it.get("tone", "neutral")][0]
        last = i == len(items) - 1
        rail = div(st(display="flex", flex_direction="column", align_items="center", width="16px", flex_shrink=0),
                   div(st(width="10px", height="10px", border_radius="999px", background=fg, margin_top="6px", flex_shrink=0), "")
                   + ("" if last else div(st(width="2px", flex_grow=1, background=LINE, margin_top="4px"), "")))
        body = div(st(display="flex", flex_direction="column", gap="4px", padding_bottom="0px" if last else "16px", flex_grow=1, min_width=0),
                   text(it["title"], 14, 20, 600)
                   + (text(it["body"], 14, 20, 400, TEXT2) if it.get("body") else "")
                   + it.get("extra", "")
                   + text(it.get("meta", ""), 12, 16, 400, TEXT3))
        out.append(div(st(display="flex", gap="12px"), rail + body))
    return div(st(display="flex", flex_direction="column"), "".join(out))


def folded_round(label: str) -> str:
    return div(st(display="flex", align_items="center", gap="8px", padding="8px 0", color=TEXT2, font_size="13px", font_weight=600, border="none", background="transparent", cursor="pointer", font_family=SANS),
               icon(IC["chevron"], 14) + escape(label), "button", type="button", aria_expanded="false")


def attachment_row(name: str, size: str, kind: str = "image", removable: bool = False, phone: bool = False) -> str:
    thumb = div(st(width="40px", height="40px", border_radius="6px", background="#E5E9EF", display="flex", align_items="center", justify_content="center", color=TEXT3, flex_shrink=0),
                icon(IC["camera" if kind == "image" else "file"], 18))
    right = button("Remove" if removable else "Open", "ghost", size="lg" if phone else "sm")
    return div(st(display="flex", align_items="center", gap="12px", padding="8px 10px", border=f"1px solid {LINE}", border_radius="6px", background=SURFACE),
               thumb + div(st(display="flex", flex_direction="column", gap="2px", flex_grow=1, min_width=0), text(name, 13, 18, 500, TEXT, "overflow: hidden; text-overflow: ellipsis; white-space: nowrap") + text(size, 12, 16, 400, TEXT3)) + right)


def radio_group(name: str, options: list[str], selected: str) -> str:
    rows = []
    for o in options:
        on = o == selected
        dot = div(st(width="18px", height="18px", border_radius="999px", border=f"2px solid {TEXT if on else LINE_STRONG}", display="flex", align_items="center", justify_content="center", flex_shrink=0),
                  div(st(width="8px", height="8px", border_radius="999px", background=TEXT), "") if on else "", "span")
        rows.append(div(st(display="flex", align_items="center", gap="10px", min_height="40px", cursor="pointer", font_size="14px", font_weight=600 if on else 500, color=TEXT if on else TEXT2), dot + escape(o), "label"))
    return div(st(display="flex", flex_direction="column", gap="2px"), text(name, 13, 18, 600) + div(st(display="flex", flex_direction="column"), "".join(rows)), role="radiogroup", aria_label=name)


def dialog(title: str, body: str, primary_label: str, danger: bool = False, note_field: str | None = None, list_items: list[str] | None = None, extra: str = "", sheet: bool = False) -> str:
    items = ""
    if list_items:
        items = div(st(display="flex", flex_direction="column", gap="6px", padding="12px 14px", background=SURFACE2, border=f"1px solid {LINE}", border_radius="6px"),
                    "".join(text(i, 14, 20) for i in list_items))
    note = ""
    if note_field:
        note = div(st(display="flex", flex_direction="column", gap="6px"),
                   text(note_field, 13, 18, 600) + div(st(height="88px", border=f"1px solid {LINE_STRONG}", border_radius="6px", background=SURFACE, padding="10px 12px", font_size="14px", color=TEXT3, box_sizing="border-box"), "", "textarea", aria_label=note_field))
    footer = div(st(display="flex", justify_content="flex-end", gap="8px", padding_top="4px", flex_direction="column-reverse" if sheet else "row"),
                 button("Cancel", "secondary", size="lg" if sheet else "md", full=sheet) + button(primary_label, "danger" if danger else "primary", size="lg" if sheet else "md", full=sheet))
    box = div(st(width="100%" if sheet else "min(520px, calc(100% - 32px))", background=SURFACE, border_radius="10px 10px 0 0" if sheet else "10px",
                 box_shadow="0 24px 48px rgba(27,36,48,0.24)", display="flex", flex_direction="column", gap="16px", padding="24px 16px 24px" if sheet else "24px", box_sizing="border-box",
                 align_self="flex-end" if sheet else "center"),
              text(title, 20, 28, 600, TEXT, "", "h2") + text(body, 15, 22, 400, TEXT2) + extra + items + note + footer,
              role="dialog", aria_modal="true", aria_label=title)
    return div(st(position="absolute", inset="0", background="rgba(27,36,48,0.45)", display="flex", align_items="flex-end" if sheet else "center", justify_content="center", z_index="10"), box)


# Shell (mirrors frontend/src/app/AppShell.tsx) -----------------------------------------------

NAV = {
    "operator": [("Dashboard", "Home", "home"), ("My applications", "Applications", "folder")],
    "officer": [("Review queue", "Queue", "queue")],
    "admin": [("Overview", "Overview", "chart"), ("Activity", "Activity", "activity"), ("Users", "Users", "users")],
}
ROLE_LABEL = {"operator": "Operator", "officer": "Licensing officer", "admin": "Administrator"}
ROLE_KICKER = {"operator": "Applicant", "officer": "Licensing office", "admin": "Administration"}
USERS = {"operator": "Tan Wei Ling", "officer": "Rahim bin Abdullah", "admin": "Priya Nair"}


def logo() -> str:
    mark = (
        '<svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true" style="flex-shrink: 0"><rect width="32" height="32" rx="7" fill="#A8192A"></rect>'
        '<path d="M9 10h14M9 16h9M9 22h4M16.5 22l2.5 2.5L24 18" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"></path></svg>'
    )
    return div(st(display="flex", align_items="center", gap="10px", text_decoration="none", color=TEXT), mark + text("PermitFlow", 17, 22, 700, TEXT, "letter-spacing: -0.02em", "span")
               + div(st(border_left=f"1px solid {LINE}", padding_left="10px", font_size="12px", color=TEXT3), "Licensing Services", "span"), "a", href="#", aria_label="PermitFlow home")


def initials(name: str) -> str:
    parts = name.split()
    return (parts[0][0] + parts[-1][0]).upper() if len(parts) > 1 else name[:2].upper()


def shell(width: int, height: int, role: str, active: str, content: str, nav: str = "full", overlay: str = "") -> str:
    """App shell as shipped: masthead 28 (secure portal, session), top bar 56, side nav 232 or 64, footer; bottom tab bar on phones."""
    phone = nav == "phone"
    masthead = div(st(height="28px", background=INK, color="#AEB6C2", display="flex", align_items="center", padding="0 16px" if phone else "0 24px", font_size="12px", gap="8px", white_space="nowrap", overflow="hidden"),
                   text("Secure licensing portal", 12, 16, 600, "#FFFFFF", "", "span") + ("" if phone else text("· Food Establishments Unit", 12, 16, 400, "#AEB6C2", "", "span"))
                   + div(st(margin_left="auto", font_variant_numeric="tabular-nums", color="#E6C8CC"), "Signed in until 18:32", "span", role="status"), role="region", aria_label="Portal notice")
    bell = div(st(position="relative", width="40px", height="40px", display="flex", align_items="center", justify_content="center", border_radius="6px", color=TEXT2, border="none", background="transparent", cursor="pointer"), icon(IC["bell"], 18)
               + div(st(position="absolute", top="6px", right="6px", min_width="16px", height="16px", border_radius="999px", background=PRIMARY, color="#FFFFFF", font_size="10px", font_weight=700, display="flex", align_items="center", justify_content="center", padding="0 4px"), "2"), "button", type="button", aria_label="Notifications, 2 unread")
    avatar = div(st(width="32px", height="32px", border_radius="999px", background=INK, color="#FFFFFF", font_size="11px", font_weight=600, letter_spacing="0.04em", display="flex", align_items="center", justify_content="center", flex_shrink=0), initials(USERS[role]), "span")
    user = div(st(display="flex", align_items="center", gap="10px"), avatar + ("" if phone else div(st(display="flex", flex_direction="column"), text(USERS[role], 13, 16, 600) + text(ROLE_LABEL[role], 12, 16, 400, TEXT3))))
    signout = "" if phone else div(st(height="32px", padding="0 12px", border_radius="6px", font_size="13px", font_weight=600, color=TEXT2, border="none", background="transparent", cursor="pointer", font_family=SANS), "Sign out", "button", type="button")
    topbar = div(st(height="56px", background="rgba(255,255,255,0.95)", border_bottom=f"1px solid {LINE}", display="flex", align_items="center", gap="12px", padding="0 12px" if phone else "0 24px", box_sizing="border-box"),
                 ("" if phone else div(st(width="40px", height="40px", display="flex", align_items="center", justify_content="center", color=TEXT2, border="none", background="transparent", cursor="pointer"), icon(IC["menu"], 18), "button", type="button", aria_label="Collapse navigation"))
                 + logo() + div(st(margin_left="auto", display="flex", align_items="center", gap="4px"), bell + user + signout), "header")
    sidenav = ""
    bottomnav = ""
    if phone:
        tabs = ""
        for label, short, ic in NAV[role]:
            on = label == active
            pill = div(st(width="44px", height="28px", border_radius="999px", background=NEUTRAL_SOFT if on else "transparent", display="flex", align_items="center", justify_content="center"), icon(IC[ic], 20), "span")
            tabs += div(st(display="flex", flex_direction="column", align_items="center", justify_content="center", gap="2px", flex_grow=1, height="64px", color=TEXT if on else TEXT3, font_size="11px", font_weight=600, text_decoration="none"), pill + escape(short), "a", href="#", aria_current="page" if on else "false")
        bottomnav = div(st(position="absolute", left="0", right="0", bottom="0", height="64px", background=SURFACE, border_top=f"1px solid {LINE}", display="flex"), tabs, "nav", aria_label="Main")
    else:
        collapsed = nav == "collapsed"
        w = 64 if collapsed else 232
        items = "" if collapsed else text(ROLE_KICKER[role], 12, 16, 600, TEXT3, "text-transform: uppercase; letter-spacing: 0.08em; padding: 8px 11px 12px")
        for label, _short, ic in NAV[role]:
            on = label == active
            common = st(display="flex", align_items="center", gap="10px", height="40px", border_radius="6px", background=NEUTRAL_SOFT if on else "transparent",
                        color=TEXT if on else TEXT2, font_size="14px", font_weight=600 if on else 500, border_left=f"3px solid {PRIMARY}" if on else "3px solid transparent",
                        box_sizing="border-box", text_decoration="none", justify_content="center" if collapsed else "flex-start", padding="0" if collapsed else "0 12px", width="40px" if collapsed else "auto")
            extra_attrs = {"aria_label": label} if collapsed else {}
            items += div(common, icon(IC[ic], 18) + ("" if collapsed else escape(label)), "a", href="#", aria_current="page" if on else "false", **extra_attrs)
        sidenav = div(st(width=f"{w}px", flex_shrink=0, background=SURFACE, border_right=f"1px solid {LINE}", padding="12px", box_sizing="border-box", display="flex", flex_direction="column", gap="2px", align_items="center" if collapsed else "stretch"), items, "nav", aria_label="Main")
    pad = "16px 16px 96px" if phone else ("24px 24px 40px" if width <= 1024 else "24px 32px 40px")
    main = div(st(flex_grow=1, min_width=0, padding=pad, box_sizing="border-box", display="flex", flex_direction="column", gap="20px"), content, "main", id="main")
    footer = "" if phone else div(st(padding="16px 32px", font_size="12px", color=TEXT3, border_top=f"1px solid {LINE}", display="flex", gap="16px"), "PermitFlow · Fictional assessment product · Privacy · Terms", "footer")
    body = div(st(display="flex", flex_grow=1, align_items="stretch"), sidenav + div(st(display="flex", flex_direction="column", flex_grow=1, min_width=0), main + footer))
    root = div(st(width=f"{width}px", height=f"{height}px", box_sizing="border-box", background=BG, color=TEXT, font_family=SANS, font_size="15px", line_height="22px", display="flex", flex_direction="column", position="relative", overflow="hidden"),
               masthead + topbar + body + bottomnav + overlay)
    return root


def page(title: str, width: int, height: int, root: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{escape(title)}</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700&amp;family=IBM+Plex+Mono&amp;display=swap" rel="stylesheet">
<style>
body{{margin:0;background:{BG};font-family:{SANS}}}
a{{color:{PRIMARY}}}a:hover{{color:{PRIMARY_HOVER}}}
button{{font-family:inherit}}
table{{font-variant-numeric:tabular-nums}}
</style>
</helmet>
{root}
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"$preview":{{"width":{width},"height":{height}}}}}'>
class Component extends DCLogic {{
  renderVals() {{ return {{}}; }}
}}
</script>
</body>
</html>
"""


# Page pieces ----------------------------------------------------------------------------

def breadcrumb(items: list[str]) -> str:
    parts = []
    for i, it in enumerate(items):
        last = i == len(items) - 1
        parts.append(text(it, 13, 18, 500 if last else 400, TEXT if last else TEXT3, "", "span"))
        if not last:
            parts.append(div(st(color=TEXT3, display="inline-flex"), icon(IC["chevron"], 12), "span"))
    return div(st(display="flex", align_items="center", gap="6px", flex_wrap="wrap"), "".join(parts), "nav", aria_label="Breadcrumb")


def page_header(title: str, subtitle: str = "", eyebrow: str = "", actions: str = "", ref: str = "") -> str:
    left = div(st(display="flex", flex_direction="column", gap="4px", min_width=0),
               (div(st(display="flex", gap="8px", align_items="center"), (mono(ref, 13, TEXT3) if ref else "") + (text(eyebrow, 12, 16, 600, TEXT3, "text-transform: uppercase; letter-spacing: 0.08em") if eyebrow else "")) if (eyebrow or ref) else "")
               + text(title, 28, 36, 600, TEXT, "letter-spacing: -0.015em", "h1")
               + (text(subtitle, 15, 22, 400, TEXT2) if subtitle else ""))
    return div(st(display="flex", align_items="flex-end", justify_content="space-between", gap="16px", flex_wrap="wrap"), left + div(st(display="flex", gap="8px", align_items="center", flex_shrink=0), actions))


def status_bar(b: str, explanation: str, meta: str = "", actions: str = "", stack: bool = False) -> str:
    left = div(st(display="flex", align_items="flex-start" if stack else "center", gap="12px", flex_wrap="wrap", flex_direction="column" if stack else "row", min_width=0, flex_grow=1),
               b + text(explanation, 14, 20, 400, TEXT2))
    right = div(st(display="flex", align_items="center", gap="12px", flex_shrink=0, margin_left="auto"), (text(meta, 12, 16, 400, TEXT3, "white-space: nowrap") if meta else "") + actions)
    return div(st(display="flex", align_items="center", gap="16px", padding="14px 20px", background=SURFACE, border=f"1px solid {LINE}", border_radius="10px", flex_wrap="wrap"), left + right)


def stat_strip(cells: list[tuple[str, str, str, bool]]) -> str:
    out = []
    for i, (num, label, ctx, hot) in enumerate(cells):
        out.append(div(st(display="flex", flex_direction="column", gap="2px", padding="16px 20px", border_left=f"1px solid {LINE}" if i else "none", flex_grow=1, min_width=0, text_decoration="none", color=TEXT),
                       text(num, 28, 36, 600, PRIMARY if hot else TEXT, "font-variant-numeric: tabular-nums; letter-spacing: -0.015em")
                       + text(label, 12, 16, 600, TEXT3, "text-transform: uppercase; letter-spacing: 0.08em")
                       + text(ctx, 13, 18, 400, TEXT2), "a", href="#"))
    return div(st(display="flex", background=SURFACE, border=f"1px solid {LINE}", border_radius="10px", overflow="hidden"), "".join(out))


def save_indicator(state: str) -> str:
    if state == "saved":
        return div(st(display="inline-flex", align_items="center", gap="6px", color=TONES["success"][0], font_size="13px", line_height="18px"), icon(IC["check"], 14) + "Saved 14:32", "span", role="status")
    if state == "retrying":
        return div(st(display="inline-flex", align_items="center", gap="6px", color=TONES["warning"][0], font_size="13px", line_height="18px"), icon(IC["clock"], 14) + "Could not save, retrying", "span", role="status")
    return div(st(display="inline-flex", align_items="center", gap="6px", color=TEXT3, font_size="13px", line_height="18px"), icon(IC["clock"], 14) + "Saving", "span", role="status")


# Checklist --------------------------------------------------------------------------------

SECTIONS = [
    ("premises", "Premises", [
        ("layout_matches_plan", "Layout matches the submitted floor plan", "Kitchen area at least 10 m² excluding the servery"),
        ("floor_trap_graded", "Floor trap in the food preparation area", "Kitchen floor graded to the trap"),
        ("coved_edges", "Edge between wall and floor coved", "Preparation and servery areas"),
        ("no_drain_hazards", "No manhole, inspection chamber, waste sump, grease trap or overhead waste pipe in food areas", "Where food is prepared, stored or served"),
        ("walls_impervious", "Walls lined with impervious material to at least 1.5 m", "Preparation and servery areas"),
    ]),
    ("kitchen", "Kitchen", [
        ("sink_provided", "At least one sink in the food preparation area", "More for a large kitchen"),
        ("handwash_basin", "Wash-hand basin with soap for workers", "Separate taps if a double-bowl sink is used"),
        ("exhaust_air_cleaning", "Cooking fumes extracted, treated and exhausted away from neighbours", "Air-cleaning system fitted"),
        ("make_up_air", "Sufficient make-up air; negative pressure under the hood", ""),
        ("ducting", "Air ducts non-combustible, smooth, easy to clean, with inspection openings", ""),
    ]),
    ("storage", "Storage", [
        ("separate_storage", "Separate, pest-proof storage for belongings, cleaning materials, ingredients, cutlery and packaging", ""),
        ("chiller_temperature", "Temperature gauge on every refrigerator and chiller", "Chillers at or below 4 °C, freezers at or below minus 18 °C"),
    ]),
    ("upkeep", "Upkeep", [
        ("pest_control_contract", "Signed pest control contract on the premises", "Rodents, cockroaches and flies, at least monthly"),
        ("cleaning_schedule", "Detailed cleaning schedule on the premises", ""),
        ("refuse_handling", "Covered refuse bins; refuse area clean and away from food areas", ""),
    ]),
    ("people", "People", [
        ("food_handlers_certified", "Every food handler holds Food Safety Course Level 1", "Refresher if attained more than five years ago"),
        ("food_hygiene_officer", "Food Safety Course Level 3 holder appointed", "Only where the kitchen exceeds 16 m² or the shop spans two or more units"),
    ]),
]

# Item titles by key, reused on every screen so the operator and the officer read the same words.
TITLES = {k: t for _, _, items in SECTIONS for k, t, _ in items}

# The demo state of the checklist: key -> (result, comment, flagged). One flagged item has no comment yet.
DEMO: dict[str, tuple[str, str, bool]] = {
    "layout_matches_plan": ("satisfactory", "", False),
    "floor_trap_graded": ("unsatisfactory", "Trap present but the floor slopes away from it; water pools by the wok station.", True),
    "coved_edges": ("unsatisfactory", "Rear wall to floor joint is square-cut behind the dish sink.", True),
    "no_drain_hazards": ("satisfactory", "", False),
    "walls_impervious": ("satisfactory", "", False),
    "sink_provided": ("satisfactory", "", False),
    "handwash_basin": ("satisfactory", "", False),
    "exhaust_air_cleaning": ("satisfactory", "", False),
    "make_up_air": ("not_assessed", "", False),
    "ducting": ("not_assessed", "", False),
    "separate_storage": ("satisfactory", "", False),
    "chiller_temperature": ("unsatisfactory", "", True),
    "pest_control_contract": ("satisfactory", "", False),
    "cleaning_schedule": ("not_assessed", "", False),
    "refuse_handling": ("not_assessed", "", False),
    "food_handlers_certified": ("not_assessed", "", False),
    "food_hygiene_officer": ("not_applicable", "", False),
}


def segmented(result: str, compact: bool = False) -> str:
    opts = [("satisfactory", "Satisfactory", "success"), ("unsatisfactory", "Unsatisfactory", "error"), ("not_applicable", "Not applicable", "neutral")]
    out = []
    for key, label, tone in opts:
        on = key == result
        fg, soft, line = TONES[tone]
        out.append(div(st(display="inline-flex", align_items="center", gap="8px", height="44px", padding="0 14px", border_radius="6px", border=f"1px solid {line if on else LINE_STRONG}", background=soft if on else SURFACE, color=fg if on else TEXT2, font_size="14px", font_weight=600 if on else 500, cursor="pointer", flex_grow=1 if compact else 0, justify_content="center", font_family=SANS),
                       div(st(width="8px", height="8px", border_radius="999px", background=fg if on else LINE_STRONG, flex_shrink=0), "", "span") + escape(label), "button", type="button", aria_pressed="true" if on else "false"))
    return div(st(display="flex", gap="8px", flex_wrap="wrap"), "".join(out), role="group", aria_label="Result")


def flag_toggle(on: bool) -> str:
    fg, soft, line = TONES["warning"]
    box = div(st(width="20px", height="20px", border_radius="4px", border=f"1px solid {fg if on else LINE_STRONG}", background=fg if on else SURFACE, display="flex", align_items="center", justify_content="center", color="#FFFFFF", flex_shrink=0), icon(IC["check"], 14) if on else "", "span")
    return div(st(display="inline-flex", align_items="center", gap="10px", min_height="44px", padding="0 12px 0 0", cursor="pointer", color=fg if on else TEXT2, font_size="14px", font_weight=600 if on else 500),
               box + icon(IC["flag"], 16) + "Need further clarification", "label")


def comment_field(value: str, required: bool, placeholder: str = "Comment (the operator reads it when the item is flagged)") -> str:
    border = LINE_STRONG if value or not required else TONES["error"][0]
    field = div(st(min_height="72px", border=f"1px solid {border}", border_radius="6px", background=SURFACE, padding="10px 12px", font_size="14px", line_height="20px", color=TEXT if value else TEXT3, box_sizing="border-box", width="100%", font_family=SANS), escape(value or placeholder), "textarea", aria_label="Comment")
    err = text("A comment is required for an unsatisfactory or flagged item.", 13, 18, 400, TONES["error"][0], "", "p") if required and not value else ""
    return div(st(display="flex", flex_direction="column", gap="6px"), field + err)


def checklist_item(n: int, key: str, title: str, guidance: str, compact: bool) -> str:
    result, comment, flagged = DEMO[key]
    needs_comment = result == "unsatisfactory" or flagged
    marker = tag("Not assessed", "neutral") if result == "not_assessed" else ""
    head = div(st(display="flex", gap="12px", align_items="flex-start"),
               mono(f"{n:02d}", 13, TEXT3) + div(st(display="flex", flex_direction="column", gap="2px", flex_grow=1, min_width=0), text(title, 16, 24, 600) + (text(guidance, 13, 20, 400, TEXT3) if guidance else "")) + marker)
    controls = div(st(display="flex", flex_direction="column", gap="12px", padding_left="0px" if compact else "34px"),
                   segmented(result, compact) + flag_toggle(flagged) + (comment_field(comment, needs_comment) if (result == "unsatisfactory" or flagged or comment) else ""))
    return div(st(display="flex", flex_direction="column", gap="14px", padding="20px 0", border_bottom=f"1px solid {LINE}"), head + controls)


def remaining_sentence(unassessed: int, missing: int) -> str:
    parts = []
    if unassessed:
        parts.append(f"Assess {unassessed} more item{'s' if unassessed != 1 else ''}")
    if missing:
        parts.append(f"add {missing} comment{'s' if missing != 1 else ''}")
    if not parts:
        return "Everything is assessed. Submit when you are ready."
    joined = " and ".join(parts)
    return joined[0].upper() + joined[1:] + " to submit."


def checklist_body(compact: bool, state: str) -> str:
    assessed = sum(1 for r, _, _ in DEMO.values() if r != "not_assessed")
    flagged = sum(1 for _, _, f in DEMO.values() if f)
    missing = sum(1 for r, c, f in DEMO.values() if (r == "unsatisfactory" or f) and not c)
    unassessed = 17 - assessed
    picker_chips = []
    for sid, name, items in SECTIONS:
        done = sum(1 for k, _, _ in items if DEMO[k][0] != "not_assessed")
        picker_chips.append(chip(name, sid == "premises", f"{done} of {len(items)}", href=f"#{sid}", done=done == len(items)))
    picker = div(st(display="flex", gap="6px", flex_wrap="wrap"), "".join(picker_chips), "nav", aria_label="Sections")
    progress = div(st(display="flex", flex_direction="column", gap="8px"),
                   div(st(display="flex", justify_content="space-between", gap="12px", flex_wrap="wrap"), text(f"{assessed} of 17 assessed, {flagged} flagged", 14, 20, 600) + (text(f"{missing} comment{'s' if missing != 1 else ''} missing", 13, 18, 400, TONES["error"][0]) if missing else ""))
                   + bar(assessed / 17, "info"))
    n = 0
    sections_html = ""
    for sid, name, items in SECTIONS:
        rows = ""
        for key, title, guidance in items:
            n += 1
            rows += checklist_item(n, key, title, guidance, compact)
        sections_html += div(st(display="flex", flex_direction="column"), div(st(padding="20px 0 4px"), text(name, 17, 24, 600, TEXT, "", "h2") + text(f"{len(items)} items", 12, 16, 400, TEXT3)) + rows, id=sid)
    reason = remaining_sentence(unassessed, missing)
    secondary = button("Retry save", "secondary") if state == "offline" else button("Next unassessed", "ghost")
    sticky = div(st(position="sticky", bottom="0px", background=SURFACE, border=f"1px solid {LINE}", border_radius="10px", padding="14px 20px", display="flex", align_items="center", justify_content="space-between", gap="12px", flex_wrap="wrap", box_shadow="0 -8px 24px rgba(27,36,48,0.06)"),
                 div(st(display="flex", flex_direction="column", gap="2px"), text(f"{assessed} of 17 assessed, {flagged} flagged", 14, 20, 600) + text(reason, 13, 18, 400, TEXT2))
                 + div(st(display="flex", gap="8px", flex_wrap="wrap"), secondary + button("Mark visit done and submit", "primary", disabled_reason=reason)))
    offline = alert("warning", "You are offline: changes will not save until you reconnect", "Keep this page open. Your entries stay here and are saved when the connection returns.", "wifi-off") if state == "offline" else ""
    return div(st(display="flex", flex_direction="column", gap="16px"), offline + picker + progress + surface(sections_html, "0 20px", "display: flex; flex-direction: column") + sticky)


def build_checklist(width: int, height: int, state: str) -> str:
    compact = width < 900
    hdr = breadcrumb(["Review queue", "PF-2026-000214", "Site visit checklist"]) + page_header("Site visit checklist", "Kopi & Kaya Toast House Pte. Ltd. · 12 Jalan Besar #01-03", ref="PF-2026-000214", actions=button("Back to the case", "ghost", icon_path=IC["back"]))
    sb = status_bar(badge("Site Visit Scheduled", "info", "lg"), "Visit 1, 22 Sep 2026. Fill the checklist on site; it saves as you go.", "Draft, not submitted", save_indicator("retrying" if state == "offline" else "saved"), stack=compact)
    content = hdr + sb + checklist_body(compact, state)
    return page("Site visit checklist", width, height, shell(width, height, "officer", "Review queue", content, nav="collapsed"))


# One chronology for the demo case (UI_STATES lifecycle rows 3 to 6):
#   22 Sep 16:40  checklist submitted, three items flagged (round 1 released)
#   25 Sep 09:12  operator answers all three and sends
#   25 Sep 11:20  officer marks item 2 clarified
#   25 Sep 14:05  officer asks again on item 1 and requests round 2
#   28 Sep 10:30  operator answers item 1 and sends
#   29 Sep        today: the officer has drafted a new question on item 3, not sent
OFFICER = "Rahim bin Abdullah"
OPERATOR = "Tan Wei Ling"


def thread_item(n: int, key: str, finding: str, state: str, rounds: list[dict[str, str]], actions: str, viewer: str, note: str = "", folded: str = "") -> str:
    tone = {"open": "warning", "answered": "info", "resolved": "success", "withdrawn": "neutral"}[state]
    label = {"open": "Open", "answered": "Answered", "resolved": "Clarified", "withdrawn": "Withdrawn"}[state]
    num = div(st(width="24px", height="24px", border_radius="999px", background=TONES[tone][1], border=f"1px solid {TONES[tone][2]}", color=TONES[tone][0], font_family=MONO, font_size="12px", display="flex", align_items="center", justify_content="center", flex_shrink=0), str(n))
    head = div(st(display="flex", gap="10px", align_items="flex-start"), num + div(st(display="flex", flex_direction="column", gap="4px", flex_grow=1, min_width=0), text(TITLES[key], 14, 20, 600) + div(st(display="flex", gap="6px", flex_wrap="wrap"), tag("Result: Unsatisfactory", "neutral") + badge(label, tone))))
    who = "Your finding on site" if viewer == "officer" else "Officer's finding on site"
    original = div(st(padding="10px 12px", background=SURFACE2, border=f"1px solid {LINE}", border_radius="6px"), text(who, 12, 16, 600, TEXT3, "text-transform: uppercase; letter-spacing: 0.04em") + text(finding, 13, 20, 400, TEXT2))
    return div(st(display="flex", flex_direction="column", gap="12px", padding="16px 0", border_bottom=f"1px solid {LINE}"), head + original + folded + timeline(rounds) + note + (div(st(display="flex", gap="8px", flex_wrap="wrap"), actions) if actions else ""))


def clarification_rail(viewer: str) -> str:
    ro = viewer != "officer"
    you = "You" if not ro else OFFICER
    header = div(st(display="flex", flex_direction="column", gap="6px", padding="14px 20px", border_bottom=f"1px solid {LINE}"),
                 div(st(display="flex", justify_content="space-between", align_items="center", gap="8px"), text("Clarification", 16, 24, 600) + tag("Round 2", "neutral"))
                 + text("Your turn: the operator answered on 28 Sep." if not ro else "The officer's turn: the operator answered on 28 Sep.", 13, 18, 400, TEXT2)
                 + text("1 open · 1 answered · 1 clarified", 13, 18, 400, TEXT3))
    next_step = "" if ro else div(st(display="flex", flex_direction="column", gap="8px", padding="16px 20px", border_bottom=f"1px solid {LINE}", background=SURFACE2),
                                  text("Next step", 12, 16, 600, TEXT3, "text-transform: uppercase; letter-spacing: 0.08em")
                                  + button("Request another round (1 item)", "primary", full=True)
                                  + button("Route to approval", "secondary", disabled_reason="1 item is answered but not yet clarified", full=True)
                                  + button("Reject", "secondary", full=True))
    r1 = [
        {"tone": "warning", "title": f"{you} asked again", "body": "Please send a photo once the floor is regraded and a short note on the drainage test.", "meta": "Round 2 · 25 Sep 2026, 14:05"},
        {"tone": "info", "title": f"{OPERATOR} answered", "body": "Regrading done 27 Sep; water now runs to the trap. Photo attached.", "meta": "Round 2 · 28 Sep 2026, 10:30", "extra": attachment_row("floor-trap-after-regrade.jpg", "JPG · 1.8 MB")},
    ]
    r2 = [
        {"tone": "warning", "title": f"{you} asked", "body": "Please confirm the coving work and attach a photo.", "meta": "Round 1 · 22 Sep 2026, 16:40"},
        {"tone": "info", "title": f"{OPERATOR} answered", "body": "Coving installed 24 Sep; photo attached.", "meta": "Round 1 · 25 Sep 2026, 09:12", "extra": attachment_row("rear-wall-coving.jpg", "JPG · 1.1 MB")},
        {"tone": "success", "title": "You marked this clarified" if not ro else f"{OFFICER} marked this clarified", "meta": "25 Sep 2026, 11:20"},
    ]
    r3 = [
        {"tone": "warning", "title": f"{you} asked", "body": "Please attach a week of chiller readings.", "meta": "Round 1 · 22 Sep 2026, 16:40"},
        {"tone": "info", "title": f"{OPERATOR} answered", "body": "Chiller serviced 24 Sep, now holding 3 °C. Log sheet attached.", "meta": "Round 1 · 25 Sep 2026, 09:12", "extra": attachment_row("chiller-log-week39.pdf", "PDF · 96 KB", "file")},
        {"tone": "warning", "title": "You asked again" if not ro else f"{OFFICER} asked again", "body": "The log shows 5 °C on two afternoons. Please confirm the door seal was checked.", "meta": "Round 3 · not sent yet"},
    ]
    per_item = "" if ro else (button("Mark clarified", "secondary", size="sm") + button("Still needs clarification", "ghost", size="sm"))
    not_sent = alert("neutral", "Not sent yet", "The operator sees this when you request another round." if not ro else "The operator sees this when the officer requests another round.", "info")
    items = (
        thread_item(1, "floor_trap_graded", "Trap present but the floor slopes away from it; water pools by the wok station.", "answered", r1, per_item, viewer, folded=folded_round("Round 1 · 2 messages"))
        + thread_item(2, "coved_edges", "Rear wall to floor joint is square-cut behind the dish sink.", "resolved", r2, "", viewer)
        + thread_item(3, "chiller_temperature", "Display chiller reads 7 °C on the built-in gauge; no log sheet on site.", "open", r3, "" if ro else button("Withdraw", "ghost", size="sm"), viewer, note=not_sent)
    )
    return div(st(width="400px", flex_shrink=0, background=SURFACE, border=f"1px solid {LINE}", border_radius="10px", overflow="hidden", display="flex", flex_direction="column", align_self="flex-start", position="sticky", top="16px"),
               header + next_step + div(st(padding="0 20px"), items), "aside", aria_label="Clarification")


def checklist_summary_card() -> str:
    body = div(st(display="flex", flex_direction="column", gap="8px"),
               text("17 items: 13 satisfactory, 3 unsatisfactory, 1 not applicable. 3 flagged for clarification.", 15, 22, 400)
               + text(f"Submitted by {OFFICER} on 22 Sep 2026, 16:40. The findings are final; the clarification threads carry what came after.", 13, 20, 400, TEXT2))
    return panel("Site visit checklist", body, button("View checklist", "secondary", size="sm", icon_path=IC["eye"]), kicker="Visit 1 · 22 Sep 2026")


def collapsed_sections() -> str:
    rows = "".join(div(st(display="flex", justify_content="space-between", align_items="center", padding="14px 20px", border_bottom=f"1px solid {LINE}" if i < 3 else "none"),
                       div(st(display="flex", gap="10px", align_items="center"), text(s, 15, 22, 600) + tag("Unchanged since Revision 3", "neutral")) + button("Show", "ghost", size="sm"))
                   for i, s in enumerate(["Business", "Premises", "Operations", "Declarations"]))
    return div(st(background=SURFACE, border=f"1px solid {LINE}", border_radius="10px", overflow="hidden"), card_header("Submission", "", "Revision 3") + rows)


def build_case_with_rail(width: int, height: int, read_only: bool) -> str:
    role = "admin" if read_only else "officer"
    hdr = breadcrumb(["Overview" if read_only else "Review queue", "PF-2026-000214"]) + page_header("Kopi & Kaya Toast House Pte. Ltd.", "Food Establishment Licence · 12 Jalan Besar #01-03", ref="PF-2026-000214", actions=(button("Back to the overview", "ghost", icon_path=IC["back"]) if read_only else button("Compare revisions", "secondary", size="sm")))
    ro = alert("neutral", "Read-only: administrators cannot act on a case", "Every action on this page is reserved for licensing officers. What you see is what the officer sees.", "lock") if read_only else ""
    explanation = "The operator answered. Decide each item, then move the case on." if not read_only else "The operator answered. The officer decides item by item, then requests another round or routes to approval."
    sb = status_bar(badge("Post-Site Clarification Resubmitted", "info", "lg"), explanation, "Round 2 · last activity 28 Sep 2026", "" if read_only else button("Audit trail", "ghost", size="sm"))
    facts = facts_row([("Applicant", f"{OPERATOR} (operator)"), ("Licence", "Food Establishment Licence"), ("Premises", "12 Jalan Besar #01-03, Singapore 208811"), ("Submitted", "Revision 3 · 19 Sep 2026")])
    left = div(st(display="flex", flex_direction="column", gap="20px", flex_grow=1, min_width=0), checklist_summary_card() + collapsed_sections())
    content = hdr + ro + sb + facts + div(st(display="flex", gap="20px", align_items="flex-start"), left + clarification_rail(role))
    return page("Case: clarification" if not read_only else "Case, read-only", width, height, shell(width, height, role, "Overview" if read_only else "Review queue", content))


# Operator respond ---------------------------------------------------------------------------

def respond_item(n: int, key: str, guidance: str, ask: str, answer: str, files: list[tuple[str, str, str]], phone: bool, answered: bool, focused: bool = False) -> str:
    fg, soft, line = TONES["warning"]
    num = div(st(width="24px", height="24px", border_radius="999px", background=TONES["success"][1] if answered else soft, border=f"1px solid {TONES['success'][2] if answered else line}", color=TONES["success"][0] if answered else fg, font_family=MONO, font_size="12px", display="flex", align_items="center", justify_content="center", flex_shrink=0), str(n))
    b = badge("Answered" if answered else "Needs your answer", "success" if answered else "warning")
    title_block = text(TITLES[key], 16, 24, 600) + (text(guidance, 13, 18, 400, TEXT3) if guidance else "")
    if phone:
        head = div(st(display="flex", gap="10px", align_items="flex-start"), num + div(st(display="flex", flex_direction="column", gap="6px", flex_grow=1, min_width=0), title_block + div(st(display="flex"), b)))
    else:
        head = div(st(display="flex", gap="10px", align_items="flex-start"), num + div(st(display="flex", flex_direction="column", gap="2px", flex_grow=1, min_width=0), title_block) + b)
    quote = div(st(display="flex", gap="10px", padding="12px 14px", background=soft, border=f"1px solid {line}", border_radius="6px"),
                div(st(color=fg, padding_top="2px"), icon(IC["flag"], 16)) + div(st(display="flex", flex_direction="column", gap="2px"), text("The licensing officer wrote", 12, 16, 600, fg) + text(ask, 14, 20, 400, TEXT) + text(f"{OFFICER} · 22 Sep 2026", 12, 16, 400, TEXT3)))
    ring = f"; outline: 2px solid {FOCUS}; outline-offset: 2px; border-color: {FOCUS}" if focused else ""
    field = div(st(display="flex", flex_direction="column", gap="6px"),
                text("Your response", 13, 18, 600, TEXT, "", "label")
                + div(st(min_height="88px", border=f"1px solid {LINE_STRONG}", border_radius="6px", background=SURFACE, padding="10px 12px", font_size="15px", line_height="22px", color=TEXT if answer else TEXT3, box_sizing="border-box", width="100%", max_width="640px", font_family=SANS) + ring, escape(answer or "Say what you did or will do about it."), "textarea", aria_label="Your response"))
    att = "".join(attachment_row(nm, sz, k, removable=True, phone=phone) for nm, sz, k in files)
    count = text(f"{len(files)} of 3 files attached · PDF, JPG or PNG, up to 10 MB each", 12, 16, 400, TEXT3)
    size = "lg" if phone else "sm"
    add = div(st(display="flex", gap="8px", flex_wrap="wrap"),
              (button("Take a photo", "secondary", size=size, icon_path=IC["camera"]) if phone else "") + button("Choose a file", "secondary", size=size, icon_path=IC["upload"]))
    files_block = div(st(display="flex", flex_direction="column", gap="8px"), text("Supporting documents (optional)", 13, 18, 600) + att + add + count)
    return div(st(display="flex", flex_direction="column", gap="14px", padding="20px 0", border_bottom=f"1px solid {LINE}"), head + quote + field + files_block, id=f"item-{n}")


def respond_body(phone: bool, all_answered: bool, focused_third: bool = False) -> str:
    third_answer = "Chiller serviced 24 Sep, now holding 3 °C. Log sheet attached." if all_answered else ""
    third_files = [("chiller-log-week39.pdf", "PDF · 96 KB", "file")] if all_answered else []
    items = (
        respond_item(1, "floor_trap_graded", "Kitchen floor graded to the trap", "Trap present but the floor slopes away from it; water pools by the wok station. Please confirm the floor will be regraded and by when.", "Contractor engaged; regrading booked for 27 Sep. Quote attached.", [("regrading-quote-27sep.pdf", "PDF · 212 KB", "file")], phone, True)
        + respond_item(2, "coved_edges", "Preparation and servery areas", "Rear wall to floor joint is square-cut behind the dish sink. Please confirm the coving work and attach a photo.", "Coving installed 24 Sep; photo attached.", [("rear-wall-coving.jpg", "JPG · 1.1 MB", "image")], phone, True)
        + respond_item(3, "chiller_temperature", "Chillers at or below 4 °C", "Display chiller reads 7 °C; no temperature log on site. Please attach a week of chiller readings.", third_answer, third_files, phone, all_answered, focused=focused_third)
    )
    n = 3 if all_answered else 2
    ready = div(st(display="flex", flex_direction="column", gap="8px"),
                div(st(display="flex", justify_content="space-between", gap="12px", flex_wrap="wrap"), text(f"Ready to send: {n} of 3 items answered", 14, 20, 600) + text("" if all_answered else "Answer every item to send", 13, 18, 400, TEXT3))
                + bar(n / 3, "success"))
    send = button("Send responses", "primary", size="lg" if phone else "md", full=phone) if all_answered else button("Send responses", "primary", size="lg" if phone else "md", disabled_reason="Answer item 3 first", full=phone)
    sticky = div(st(position="sticky", bottom="64px" if phone else "0px", background=SURFACE, border=f"1px solid {LINE}", border_radius="10px", padding="14px 16px" if phone else "14px 20px", display="flex", flex_direction="column" if phone else "row", align_items="stretch" if phone else "center", justify_content="space-between", gap="12px", box_shadow="0 -8px 24px rgba(27,36,48,0.06)"),
                 ready + send)
    return div(st(display="flex", flex_direction="column", gap="16px"), surface(items, "0 16px" if phone else "0 20px") + sticky)


def build_respond(width: int, height: int, with_dialog: bool = False) -> str:
    phone = width < 600
    hdr = (breadcrumb(["My applications", "PF-2026-000214"]) if not phone else "") + page_header("Respond to clarification", "Kopi & Kaya Toast House Pte. Ltd." if not phone else "", ref="PF-2026-000214", actions=("" if phone else button("Back to the application", "ghost", icon_path=IC["back"])))
    sb = status_bar(badge("Pending Post-Site Clarification", "warning", "lg"), "The licensing officer needs more information on 3 items after the site visit. Only those items are shown; answer each one, then send.", "Round 1", "", stack=phone)
    content = hdr + sb + respond_body(phone, all_answered=with_dialog, focused_third=phone and not with_dialog)
    overlay = dialog("Send your responses?", "Your answers and attachments for all 3 items go to the licensing officer. You cannot change them once sent.", "Send responses",
                     list_items=[TITLES["floor_trap_graded"], TITLES["coved_edges"], TITLES["chiller_temperature"]], sheet=phone) if with_dialog else ""
    return page("Respond to clarification", width, height, shell(width, height, "operator", "My applications", content, nav="phone" if phone else "full", overlay=overlay))


# Operator history ------------------------------------------------------------------------------

def build_history(width: int, height: int) -> str:
    hdr = breadcrumb(["My applications", "PF-2026-000214", "History"]) + page_header("History", "Kopi & Kaya Toast House Pte. Ltd.", ref="PF-2026-000214", actions=button("Back to the application", "ghost", icon_path=IC["back"]))
    tabs = div(st(display="flex", gap="4px", border_bottom=f"1px solid {LINE}"), "".join(
        div(st(padding="10px 14px", font_size="14px", font_weight=600 if on else 500, color=TEXT if on else TEXT2, border_bottom=f"2px solid {PRIMARY}" if on else "2px solid transparent", text_decoration="none"), escape(t), "a", href="#", aria_current="page" if on else "false")
        for t, on in [("Revisions", False), ("Feedback", False), ("Site visit", True)]))
    sb = status_bar(badge("Post-Site Resubmitted", "info", "lg"), "The licensing officer is reviewing your responses. Nothing is needed from you right now.", "Round 2 sent 28 Sep 2026")
    visit = div(st(display="flex", flex_direction="column", gap="12px"),
                div(st(display="flex", gap="12px", align_items="center", flex_wrap="wrap"), text("Visit 1 · 22 Sep 2026", 17, 24, 600) + tag("Inspection recorded", "neutral", IC["check"]) + text("3 items needed clarification", 13, 18, 400, TEXT3))
                + alert("neutral", "You see only the items the officer asked about", "The inspection itself is the licensing office's record.", "info"))

    def rnd(title: str, when: str, items: list[dict[str, str]], state_badge: str, tone: str) -> str:
        return panel(title, timeline(items), badge(state_badge, tone), kicker=when)
    r1 = rnd("Round 1", "22 to 25 Sep 2026", [
        {"tone": "warning", "title": f"{TITLES['floor_trap_graded']}: the officer asked", "body": "Please confirm the floor will be regraded and by when.", "meta": "22 Sep 2026, 16:40"},
        {"tone": "info", "title": "You answered", "body": "Contractor engaged; regrading booked for 27 Sep.", "meta": "Sent 25 Sep 2026, 09:12", "extra": attachment_row("regrading-quote-27sep.pdf", "PDF · 212 KB", "file")},
        {"tone": "warning", "title": f"{TITLES['coved_edges']}: the officer asked", "body": "Please confirm the coving work and attach a photo.", "meta": "22 Sep 2026, 16:40"},
        {"tone": "info", "title": "You answered", "body": "Coving installed 24 Sep; photo attached.", "meta": "Sent 25 Sep 2026, 09:12", "extra": attachment_row("rear-wall-coving.jpg", "JPG · 1.1 MB")},
        {"tone": "success", "title": "Marked clarified by the officer", "meta": "25 Sep 2026, 11:20"},
        {"tone": "warning", "title": f"{TITLES['chiller_temperature']}: the officer asked", "body": "Please attach a week of chiller readings.", "meta": "22 Sep 2026, 16:40"},
        {"tone": "info", "title": "You answered", "body": "Chiller serviced 24 Sep, now holding 3 °C.", "meta": "Sent 25 Sep 2026, 09:12", "extra": attachment_row("chiller-log-week39.pdf", "PDF · 96 KB", "file")},
    ], "Sent", "info")
    r2 = rnd("Round 2", "25 to 28 Sep 2026", [
        {"tone": "warning", "title": f"{TITLES['floor_trap_graded']}: the officer asked again", "body": "Please send a photo once the floor is regraded and a short note on the drainage test.", "meta": "25 Sep 2026, 14:05"},
        {"tone": "info", "title": "You answered", "body": "Regrading done 27 Sep; water now runs to the trap.", "meta": "Sent 28 Sep 2026, 10:30", "extra": attachment_row("floor-trap-after-regrade.jpg", "JPG · 1.8 MB")},
    ], "Sent", "info")
    content = hdr + tabs + sb + visit + r1 + r2
    return page("History: site visit", width, height, shell(width, height, "operator", "My applications", content))


# Admin --------------------------------------------------------------------------------------

# (officer label, count, tone, whose turn) with the plan's reading of the post-site states
STATUS_COUNTS = [
    ("Drafts (not visible to officers)", 5, "neutral", "draft"),
    ("Application Received", 3, "info", "office"), ("Under Review", 4, "info", "office"), ("Pending Pre-Site Resubmission", 3, "warning", "operator"),
    ("Pre-Site Resubmitted", 1, "info", "office"), ("Site Visit Scheduled", 2, "info", "office"), ("Site Visit Done", 0, "info", "office"),
    ("Awaiting Post-Site Clarification", 1, "warning", "operator"), ("Awaiting Post-Site Resubmission", 1, "warning", "operator"),
    ("Post-Site Clarification Resubmitted", 1, "info", "office"), ("Route to Approval", 1, "info", "office"),
    ("Approved", 6, "success", "decided"), ("Rejected", 2, "error", "decided"), ("Withdrawn", 1, "neutral", "decided"),
]


def build_admin_overview(width: int, height: int) -> str:
    total = sum(c for _, c, _, _ in STATUS_COUNTS)
    drafts = sum(c for _, c, _, t in STATUS_COUNTS if t == "draft")
    office = sum(c for _, c, _, t in STATUS_COUNTS if t == "office")
    operators = sum(c for _, c, _, t in STATUS_COUNTS if t == "operator")
    hdr = page_header("Operations overview", "Is anything stuck, and are the document checks working. Numbers as of 23 Sep 2026, 14:32 SGT.", eyebrow="Administration", actions=button("Refresh", "secondary", size="sm"))
    strip = stat_strip([(str(total), "Applications", f"{total - drafts} submitted, {drafts} drafts", False), (str(office), "With the office", "Waiting on an officer", False), (str(operators), "Waiting on operators", "Resubmission or clarification", False), ("2", "Idle over 7 days", "Oldest since 14 Sep", True)])
    mx = max(c for _, c, _, _ in STATUS_COUNTS)
    rows = [[text(lbl, 13, 20, 400, TEXT2 if c else TEXT3), str(c), bar(c / mx, tone, 8, "100%")] for lbl, c, tone, _ in STATUS_COUNTS]
    status_table = panel("Applications by status", table(["Officer status", "Count", ""], rows, ["auto", "80px", "40%"], numeric={1}), kicker="Internal statuses, officer labels", pad="0")
    idle_rows = [
        [mono("PF-2026-000209"), "Nasi Padang Corner", badge("Pending Pre-Site Resubmission", "warning"), "9", "14 Sep 2026", button("Open", "ghost", size="sm")],
        [mono("PF-2026-000198"), "Bak Kut Teh House Pte. Ltd.", badge("Application Received", "info"), "8", "15 Sep 2026", button("Open", "ghost", size="sm")],
    ]
    idle = panel("Idle for more than 7 days", table(["Reference", "Business", "Status", "Days idle", "Last activity", ""], idle_rows, ["150px", "auto", "220px", "90px", "130px", "80px"], numeric={3}), kicker="Ten longest, in Singapore calendar days", pad="0")
    health = panel("Document checks, last 24 hours",
                   div(st(display="flex", flex_direction="column", gap="12px"),
                       def_list([("Checks run", "38"), ("Verified", "29"), ("Issues found", "6"), ("Needs officer review", "2"), ("Could not read", "0"), ("Failed or unavailable", "1"), ("Average time", "4.1 s"), ("Slowest 5 % of checks", "9.8 s")])
                       + text("Provider: OpenAI, gpt-4.1-mini. Results are advisory; officers decide.", 13, 18, 400, TEXT2)),
                   text("1 of 38 checks failed", 13, 18, 400, TEXT2), kicker="Advisory checks")
    quota = panel("Today", div(st(display="flex", flex_direction="column", gap="12px"),
                               def_list([("Submissions", "2"), ("Resubmissions", "1"), ("Checklists submitted", "1"), ("Clarification rounds", "1")])
                               + div(st(display="flex", flex_direction="column", gap="6px"), div(st(display="flex", justify_content="space-between"), text("Document checks against the platform quota", 13, 18, 500) + text("41 of 1,000", 13, 18, 400, TEXT3, "font-variant-numeric: tabular-nums")) + bar(41 / 1000, "info", 6))),
                  kicker="Singapore calendar day")
    grid = div(st(display="grid", grid_template_columns="repeat(2, minmax(0, 1fr))", gap="20px", align_items="start"), status_table + div(st(display="flex", flex_direction="column", gap="20px"), health + quota))
    content = hdr + strip + grid + idle
    return page("Admin overview", width, height, shell(width, height, "admin", "Overview", content))


def build_admin_activity(width: int, height: int) -> str:
    hdr = page_header("Activity", "The latest audit events across every application and every user change. Nothing here can be edited.", eyebrow="Administration")
    fams = ["All", "Application", "Section", "Document", "Check", "Revision", "Status", "Feedback", "Checklist", "Clarification", "User"]
    chips = div(st(display="flex", gap="6px", flex_wrap="wrap"), "".join(chip(f, i == 0) for i, f in enumerate(fams)), role="group", aria_label="Event family")
    ev = [
        ("14:31", "clarification.answered", f"{OPERATOR} answered \"{TITLES['floor_trap_graded']}\" in round 2", f"{OPERATOR} · operator", "PF-2026-000214"),
        ("14:05", "user.role_changed", "Lim Jun Hao changed from operator to licensing officer", "Priya Nair · administrator", ""),
        ("13:58", "status.changed", "Site Visit Scheduled to Site Visit Done", f"{OFFICER} · officer", "PF-2026-000231"),
        ("13:58", "checklist.submitted", "Checklist submitted: 17 items, 2 flagged", f"{OFFICER} · officer", "PF-2026-000231"),
        ("13:58", "status.changed", "Site Visit Done to Awaiting Post-Site Clarification", "System", "PF-2026-000231"),
        ("12:40", "verification.completed", "Food hygiene certificate: verified", "System", "PF-2026-000240"),
        ("12:39", "document.uploaded", "Food hygiene certificate uploaded", "Ng Li Ying · operator", "PF-2026-000240"),
        ("11:02", "feedback.released", "2 feedback items released to the operator", f"{OFFICER} · officer", "PF-2026-000209"),
        ("11:02", "status.changed", "Under Review to Pending Pre-Site Resubmission", f"{OFFICER} · officer", "PF-2026-000209"),
        ("09:15", "user.deactivated", "Account deactivated: contractor@permitflow.example.sg", "Priya Nair · administrator", ""),
        ("08:50", "licence.issued", "Licence FEL-2026-000011 issued", f"{OFFICER} · officer", "PF-2026-000202"),
        ("08:50", "status.changed", "Route to Approval to Approved", f"{OFFICER} · officer", "PF-2026-000202"),
    ]
    rows = [[div(st(font_variant_numeric="tabular-nums", color=TEXT3), f"23 Sep · {t}"), mono(et, 12, TEXT2), text(s, 13, 20), text(a, 13, 20, 400, TEXT2), (div(st(display="inline-flex", color=TEXT, text_decoration="none"), mono(r, 13, TEXT), "a", href="#") if r else text("no case", 13, 20, 400, TEXT3))] for t, et, s, a, r in ev]
    feed = panel("Latest 50 events", table(["When", "Event", "What happened", "Who", "Case"], rows, ["120px", "170px", "auto", "180px", "130px"]) + div(st(display="flex", justify_content="center", padding="12px"), button("Show older activity", "ghost")), kicker="Newest first", pad="0")
    content = hdr + chips + feed
    return page("Admin activity", width, height, shell(width, height, "admin", "Activity", content))


def build_admin_users(width: int, height: int) -> str:
    hdr = page_header("Users", "Change a role or deactivate an account. Every change is audited. New accounts are set up by the service team, not here.", eyebrow="Administration")
    search_input = div(st(border="none", outline="none", background="transparent", font_family=SANS, font_size="14px", color=TEXT, flex_grow=1, min_width=0), "", "input", type="search", placeholder="Search by name or email", aria_label="Search by name or email")
    search = div(st(display="flex", gap="12px", align_items="center", flex_wrap="wrap"),
                 div(st(display="flex", align_items="center", gap="8px", height="40px", padding="0 12px", border=f"1px solid {LINE_STRONG}", border_radius="6px", background=SURFACE, width="360px", box_sizing="border-box", color=TEXT3), icon(IC["search"], 16) + search_input, "label")
                 + div(st(display="flex", gap="6px"), "".join(chip(f, i == 0) for i, f in enumerate(["All", "Operators", "Licensing officers", "Administrators"]))))

    def actions(own: bool, protected: bool, active: bool) -> str:
        if own:
            return button("Change role", "ghost", size="sm", disabled_reason="You cannot change your own account") + button("Deactivate", "ghost", size="sm", disabled_reason="You cannot change your own account")
        if protected:
            return button("Change role", "ghost", size="sm", disabled_reason="Demonstration account, protected") + button("Deactivate", "ghost", size="sm", disabled_reason="Demonstration account, protected")
        return button("Change role", "ghost", size="sm") + (button("Reactivate", "ghost", size="sm") if not active else button("Deactivate", "ghost", size="sm"))
    people = [
        ("Priya Nair", "admin@permitflow.example.sg", "Administrator", True, True, "17 Sep 2026"),
        ("Rahim bin Abdullah", "officer@permitflow.example.sg", "Licensing officer", True, False, "17 Sep 2026"),
        ("Tan Wei Ling", "operator@permitflow.example.sg", "Operator", True, False, "17 Sep 2026"),
        ("Lim Jun Hao", "officer2@permitflow.example.sg", "Operator", False, False, "20 Sep 2026"),
        ("Ng Li Ying", "ng.liying@example.sg", "Operator", False, False, "21 Sep 2026"),
        ("Contractor account", "contractor@permitflow.example.sg", "Operator", False, False, "18 Sep 2026"),
    ]
    rows = []
    for name, email, role, protected, own, created in people:
        active = email != "contractor@permitflow.example.sg"
        rows.append([div(st(display="flex", flex_direction="column", gap="2px"), text(name + (" (you)" if own else ""), 13, 20, 600) + text(email, 12, 16, 400, TEXT3)), role,
                     div(st(display="flex", gap="6px", flex_wrap="wrap"), badge("Active" if active else "Deactivated", "success" if active else "neutral") + (tag("Protected", "neutral", IC["lock"]) if protected else "")), created,
                     div(st(display="flex", gap="4px", justify_content="flex-end"), actions(own, protected, active))])
    tbl = panel("6 accounts", table(["User", "Role", "Status", "Created", ""], rows, ["auto", "150px", "220px", "120px", "220px"]), kicker="Directory", pad="0")
    overlay = dialog("Change Lim Jun Hao's role to Licensing officer?", "They get licensing officer permissions on their next request. This does not sign them out.", "Change role",
                     extra=radio_group("New role", ["Operator", "Licensing officer", "Administrator"], "Licensing officer"))
    content = hdr + search + tbl
    return page("Admin users", width, height, shell(width, height, "admin", "Users", content, overlay=overlay))


# Canvas ----------------------------------------------------------------------------------------

BOARDS: list[tuple[str, str, int, int, str, int]] = [
    # file, title, w, h, builder key, row
    ("Main.dc.html", "S-30 Checklist, iPad landscape 1024", 1024, 4460, "checklist-1024", 0),
    ("S30-Checklist-820.dc.html", "S-30 Checklist, iPad portrait 820, offline", 820, 5000, "checklist-820", 0),
    ("S31-Case-Clarification.dc.html", "S-31 Officer case with the clarification rail", 1280, 2600, "case", 0),
    ("S18-Respond-Phone.dc.html", "S-18 Respond to clarification, phone 390", 390, 2800, "respond-390", 1),
    ("S18-Respond-Phone-Sheet.dc.html", "S-18 phone, send dialog as a sheet", 390, 2800, "respond-390-sheet", 1),
    ("S18-Respond-Desktop.dc.html", "S-18 Respond to clarification, 1280, send dialog", 1280, 2000, "respond-1280", 1),
    ("S19-History.dc.html", "S-19 Operator history, site visit", 1280, 1800, "history", 1),
    ("S40-Admin-Overview.dc.html", "S-40 Admin overview", 1280, 1700, "admin-overview", 2),
    ("S42-Admin-Activity.dc.html", "S-42 Admin activity", 1280, 1250, "admin-activity", 2),
    ("S41-Admin-Users.dc.html", "S-41 Admin users, change-role dialog", 1280, 950, "admin-users", 2),
    ("S43-Admin-ReadOnly-Case.dc.html", "S-43 Admin read-only case", 1280, 2500, "case-ro", 2),
]


def build(key: str, w: int, h: int) -> str:
    if key == "checklist-1024":
        return build_checklist(w, h, "online")
    if key == "checklist-820":
        return build_checklist(w, h, "offline")
    if key == "case":
        return build_case_with_rail(w, h, False)
    if key == "case-ro":
        return build_case_with_rail(w, h, True)
    if key == "respond-390":
        return build_respond(w, h)
    if key == "respond-390-sheet":
        return build_respond(w, h, with_dialog=True)
    if key == "respond-1280":
        return build_respond(w, h, with_dialog=True)
    if key == "history":
        return build_history(w, h)
    if key == "admin-overview":
        return build_admin_overview(w, h)
    if key == "admin-activity":
        return build_admin_activity(w, h)
    if key == "admin-users":
        return build_admin_users(w, h)
    raise KeyError(key)


def main(out: Path) -> None:
    proj = out / "project"
    proj.mkdir(parents=True, exist_ok=True)
    boards: dict[str, dict[str, object]] = {}
    order: list[str] = []
    x, y, row_h, row = 0, 0, 0, 0
    for fname, title, w, h, key, r in BOARDS:
        (proj / fname).write_text(build(key, w, h), encoding="utf-8")
        if r != row:
            row, x, y, row_h = r, 0, y + row_h + 240, 0
        boards[fname] = {"x": x, "y": y, "w": w, "h": h, "title": title, "is_interactive": False}
        order.append(fname)
        x += w + 80
        row_h = max(row_h, h)
    notes = {
        "row-officer": {"x": 0, "y": -300, "text": "Officer: checklist on site, then the clarification rail", "kind": "title1", "maxW": 3400},
        "row-operator": {"x": 0, "y": int(boards["S18-Respond-Phone.dc.html"]["y"]) - 300, "text": "Operator: answer only the flagged items", "kind": "title1", "maxW": 3400},  # type: ignore[call-overload]
        "row-admin": {"x": 0, "y": int(boards["S40-Admin-Overview.dc.html"]["y"]) - 300, "text": "Admin: overview, activity, users, read-only case", "kind": "title1", "maxW": 5400},  # type: ignore[call-overload]
    }
    canvas = {
        "v": 3,
        "createdOnFiles": {"v": 1, "at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")},
        "title": "PermitFlow prototype v0.4.0",
        "launch": {"view": "canvas"},
        "pages": [],
        "boards": boards,
        "order": order,
        "notes": notes,
        "designSystems": [],
    }
    (proj / "canvas.json").write_text(json.dumps(canvas, indent=2), encoding="utf-8")
    print(f"wrote {len(order)} artboards to {proj}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "out"))
