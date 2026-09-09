"""Standalone HTML report renderer (v2) — the intuitive, ownership-centric layout:
verdict-first, title-journey, documents-by-role, plain-language attention list.
Renders the dict produced by report.build_report_v2().
"""
from __future__ import annotations

import html as _html

_CSS = """
:root{--ink:#1a2233;--ink2:#4a5568;--soft:#7b8595;--paper:#f4f6fa;--card:#fff;--line:#e3e8f0;
--brand:#3b5bdb;--brandsoft:#eef2ff;--ok:#1f9d63;--oksoft:#e6f6ee;--warn:#d98421;--warnsoft:#fdf1e1;
--bad:#d6336c;--badsoft:#fdebf2;--gap:#c2410c;--gapsoft:#fdeee2;--mono:'SFMono-Regular',Consolas,monospace;}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:'Segoe UI',system-ui,-apple-system,sans-serif;line-height:1.4}
.wrap{max-width:760px;margin:0 auto;padding:16px 16px 50px}
.kick{font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--soft);font-weight:700}
.tag{display:inline-block;font-size:9.5px;font-weight:800;letter-spacing:.03em;padding:1px 8px;border-radius:20px}
.hero{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;margin:8px 0 14px;box-shadow:0 6px 18px rgba(26,34,51,.05)}
.hero .top{padding:14px 16px;display:flex;gap:13px;align-items:flex-start}
.hero .vbadge{flex:none;width:50px;height:50px;border-radius:12px;display:grid;place-items:center;font-size:25px}
.vb-clean{background:var(--oksoft)}.vb-review{background:var(--warnsoft)}.vb-broken{background:var(--badsoft)}
.hero h1{font-size:18px;margin:1px 0 3px;line-height:1.2}
.hero .plain{color:var(--ink2);font-size:13px;margin:0;max-width:560px}
.hero .addr{font-size:12px;color:var(--soft);margin:5px 0 0;font-weight:600}
.hero .strip{display:flex;border-top:1px solid var(--line);background:#fafbfd}
.hero .stat{flex:1;padding:8px 10px;text-align:center;border-right:1px solid var(--line)}
.hero .stat:last-child{border-right:none}
.hero .stat .n{font-size:15px;font-weight:800}.hero .stat .n.warn{color:var(--warn)}.hero .stat .n.bad{color:var(--bad)}
.hero .stat .l{font-size:9.5px;color:var(--soft);text-transform:uppercase;letter-spacing:.04em;font-weight:700;margin-top:0}
h2{font-size:14px;margin:20px 0 3px;display:flex;align-items:center;gap:7px}.lead{color:var(--soft);font-size:11.5px;margin:0 0 7px}
.callout{background:var(--brandsoft);border:1px solid #d6e0ff;border-radius:11px;padding:10px 13px;display:flex;gap:10px;align-items:flex-start}
.callout .ic{font-size:18px}.callout b{color:var(--brand)}.callout p{margin:2px 0 0;font-size:12.5px;color:var(--ink2)}
.owner{display:grid;grid-template-columns:30px 1fr;gap:10px;align-items:center}
.owner .av{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;font-size:14px;background:var(--card);border:2px solid var(--line);z-index:2}
.owner.now .av{border-color:var(--brand);background:var(--brandsoft)}.owner.root .av{border-color:var(--soft)}
.ocard{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:7px 12px}.owner.now .ocard{border:1.5px solid var(--brand)}
.ocard .role{font-size:9.5px;font-weight:800;text-transform:uppercase;letter-spacing:.04em;color:var(--soft)}
.ocard .nm{font-size:14px;font-weight:700}.ocard .meta{font-size:11.5px;color:var(--soft)}.ocard .orig{color:var(--soft);font-weight:400}
.badge-now{background:var(--brandsoft);color:var(--brand)}.badge-owner{background:var(--oksoft);color:var(--ok)}.badge-root{background:#eef0f4;color:var(--soft)}
.transfer{display:grid;grid-template-columns:30px 1fr;gap:10px;align-items:center;margin:1px 0}
.transfer .rail{justify-self:center;width:2px;background:var(--line);min-height:18px;height:100%}
.transfer.linked .rail{background:var(--ok)}.transfer.weak .rail{background:var(--warn)}
.transfer.authority .rail{background:repeating-linear-gradient(var(--brand) 0 5px,transparent 5px 11px)}
.tcard{font-size:12px;padding:6px 11px;border-radius:9px;border:1px solid var(--line);background:#fbfcfe}
.tcard .th{display:flex;align-items:center;gap:7px;flex-wrap:wrap}
.tcard .vmark{font-size:10.5px;font-weight:800;padding:1px 8px;border-radius:20px}
.vm-linked{background:var(--oksoft);color:var(--ok)}.vm-weak{background:var(--warnsoft);color:var(--warn)}
.vm-authority{background:var(--brandsoft);color:var(--brand)}.vm-origin{background:#eef0f4;color:var(--soft)}
.tcard .dref{font-family:var(--mono);font-size:11px;color:var(--soft)}.tcard .tn{font-size:11.5px;color:var(--ink2);margin-top:2px}
.rupture{grid-column:1 / -1;background:var(--gapsoft);border:1.5px solid #f1c3a0;border-radius:10px;padding:9px 13px;display:flex;gap:10px;align-items:flex-start;margin:2px 0}
.rupture.broken{background:var(--badsoft);border-color:#f0a8c4}
.rupture .ic{font-size:18px}.rupture .rh{font-weight:800;color:var(--gap);font-size:13px}.rupture.broken .rh{color:var(--bad)}
.rupture .rd{font-size:11.5px;color:var(--ink2);margin-top:1px}
.ghead{font-size:11px;font-weight:800;color:var(--ink2);text-transform:uppercase;letter-spacing:.04em;margin:11px 0 6px;display:flex;align-items:center;gap:7px}
.ghead .cnt{font-size:10.5px;color:var(--soft);font-weight:700}
.doc{display:flex;gap:10px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:7px 12px;margin-bottom:6px}
.doc .di{width:26px;height:26px;flex:none;border-radius:8px;display:grid;place-items:center;font-size:14px;background:var(--paper)}
.doc .dt{font-weight:700;font-size:13px}.doc .dm{font-size:11px;color:var(--soft);font-family:var(--mono)}
.doc .roletag{margin-left:auto;font-size:9.5px;font-weight:800;padding:2px 9px;border-radius:20px}
.rt-title{background:var(--oksoft);color:var(--ok)}.rt-authority{background:var(--brandsoft);color:var(--brand)}.rt-metadata{background:#eef0f4;color:var(--soft)}
.att{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--warn);border-radius:10px;padding:9px 13px;margin-bottom:7px}
.att.high{border-left-color:var(--gap)}.att h4{margin:0 0 2px;font-size:13px;display:flex;align-items:center;gap:7px}
.att .sev{font-size:9.5px;font-weight:800;padding:1px 8px;border-radius:20px}
.att .sev.medium{background:var(--warnsoft);color:var(--warn)}.att .sev.high{background:var(--gapsoft);color:var(--gap)}
.att p{margin:1px 0 0;font-size:12px;color:var(--ink2)}.att .do{margin:5px 0 0;font-size:11.5px;color:var(--ink)}.att .do b{color:var(--brand)}
.foot{font-size:11px;color:var(--soft);margin-top:16px;background:#fafbfd;border:1px solid var(--line);border-radius:10px;padding:10px 13px}
"""


def _esc(s) -> str:
    return _html.escape(str(s if s is not None else ""))


def _party(p: dict) -> str:
    if not p:
        return '<span class="meta">Unknown</span>'
    s = _esc(p.get("name") or "Unknown")
    if p.get("name_original"):
        s += f' <span class="orig">({_esc(p["name_original"])})</span>'
    if p.get("extra"):
        s += f' <span class="orig">&amp; {p["extra"]} more</span>'
    return s


def render_report_v2(r: dict) -> str:
    v = r["verdict"]
    st = r["stats"]
    p = r.get("property", {})
    addr = " · ".join(x for x in [
        (f"Sy. {p.get('survey_no')}" if p.get("survey_no") else None),
        (f"Plot {p.get('plot_no')}" if p.get("plot_no") else None),
        p.get("extent_text"), p.get("locality")] if x) or "—"

    # journey
    journey = ""
    for it in r["journey"]:
        if it["kind"] == "owner":
            now = " now" if it.get("now") else (" root" if it.get("badge") == "MOTHER DEED" else "")
            badgecls = {"DEVELOPER": "badge-now", "TITLE OWNER": "badge-owner", "MOTHER DEED": "badge-root"}.get(it.get("badge"), "")
            badge = f'<span class="tag {badgecls}">{_esc(it["badge"])}</span>' if it.get("badge") else ""
            av = "🏗️" if it.get("badge") == "DEVELOPER" else ("📜" if it.get("badge") == "MOTHER DEED" else "👤")
            journey += f"""<div class="owner{now}"><div class="av">{av}</div>
              <div class="ocard"><div class="role">{_esc(it["role"])}</div>
              <div class="nm">{_party(it["party"])} {badge}</div>
              <div class="meta">{_esc(it.get("meta") or "")}</div></div></div>"""
        else:  # transfer
            vd = it["verdict"]
            if vd in ("gap", "broken"):
                cls = "broken" if vd == "broken" else ""
                ic = "⛔" if vd == "broken" else "⛳"
                head = "Chain breaks here" if vd == "broken" else "A deed may be missing here"
                journey += f"""<div class="transfer {vd}"><div class="rail"></div>
                  <div class="rupture {cls}"><div class="ic">{ic}</div>
                  <div><div class="rh">{head}</div><div class="rd">{_esc(it.get("note") or "Ownership does not carry over between these deeds.")}</div></div></div></div>"""
            else:
                score = f" · {it['id_score']}/100" if it.get("id_score") is not None and vd in ("linked", "weak") else ""
                note = f'<div class="tn">{_esc(it["note"])}</div>' if it.get("note") else ""
                journey += f"""<div class="transfer {vd}"><div class="rail"></div>
                  <div class="tcard"><div class="th"><span class="vmark vm-{vd}">{_esc(it["label"])}{score}</span>
                  <span class="dref">{_esc(it["ref"])}</span></div>{note}</div></div>"""

    # documents by role
    def _docgroup(title_html, items, role):
        if not items:
            return ""
        icon = {"title": "📄", "authority": "🏗️", "metadata": "📋"}[role]
        rows = ""
        for d in items:
            di = "📜" if d.get("is_root") else icon
            rows += f"""<div class="doc"><div class="di">{di}</div>
              <div><div class="dt">{_esc(d.get("deed_type") or "Document")}</div>
              <div class="dm">{_esc(d.get("doc_no") or "")}{(" · " + _esc(d["date"])) if d.get("date") else ""}{" · root" if d.get("is_root") else ""}</div></div>
              <span class="roletag rt-{role}">{ {"title":"CONVEYS TITLE","authority":"AUTHORITY","metadata":"METADATA"}[role] }</span></div>"""
        return f'<div class="ghead">{title_html} <span class="cnt">· {len(items)}</span></div>{rows}'

    docs = r["docs_by_role"]
    docgroups = (
        _docgroup("⛓️ Title chain — the conveyances", docs["title"], "title")
        + _docgroup("🗝️ Authority &amp; supporting — do NOT convey title", docs["authority"], "authority")
        + _docgroup("📋 Metadata — not a deed", docs["metadata"], "metadata")
    )

    # callout
    callout = ""
    if r["authority"]:
        a = r["authority"][0]
        callout = f"""<h2>🧭 What you're looking at</h2>
        <div class="callout"><div class="ic">🏗️</div><div>
        <b>The current document is a {_esc(a["deed_type"] or "Development Agreement")} — it does not transfer ownership.</b>
        <p>The land is <b>owned by {_esc(a["owner"])}</b>; <b>{_esc(a["holder"])}</b> holds the authority to develop it and execute sale deeds on the owner's behalf. The chain of title below runs through the <b>sale &amp; partition deeds</b> — not this agreement.</p>
        </div></div>"""

    # attention
    att = "".join(
        f"""<div class="att {a["severity"]}"><h4><span class="sev {a["severity"]}">{_esc(a["verb"])}</span>{_esc(a["title"])}</h4>
        <p>{_esc(a["detail"])}</p><div class="do"><b>Do:</b> {_esc(a["action"])}</div></div>"""
        for a in r["attention"]
    ) or '<p class="lead">Nothing flagged.</p>'

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Title Chain Report</title><style>{_CSS}</style></head><body><div class="wrap">
  <div class="kick">Title Chain Report</div>
  <div class="hero"><div class="top"><div class="vbadge vb-{v['level']}">{v['icon']}</div>
    <div><h1>{_esc(v['headline'])}</h1><p class="plain">{_esc(v['plain'])}</p>
    <p class="addr">📍 {_esc(addr)}</p></div></div>
    <div class="strip">
      <div class="stat"><div class="n">{st['title_deeds']}</div><div class="l">Title deeds</div></div>
      <div class="stat"><div class="n">{_esc(st['span_from'] or '—')}→{_esc(st['span_to'] or '—')}</div><div class="l">Span</div></div>
      <div class="stat"><div class="n warn">{st['need_review']}</div><div class="l">Need review</div></div>
      <div class="stat"><div class="n {'bad' if st['breaks'] else ''}">{st['breaks']}</div><div class="l">Hard breaks</div></div>
    </div></div>
  {callout}
  <h2>🧬 The title journey</h2>
  <p class="lead">Who has owned this property, newest at the top — and whether each hand-off checks out.</p>
  {journey}
  <h2>📂 Documents, by role</h2>
  <p class="lead">{st['title_deeds'] + len(docs['authority']) + len(docs['metadata'])} documents read — grouped by what they actually do.</p>
  {docgroups}
  <h2>🔎 What needs attention</h2>
  {att}
  <div class="foot">Automated screening of the documents provided. <b>Not a legal opinion on title</b> and not verified
  against the government registry (EC / 22-A / revenue records) — a separate step. It flags; a human decides.</div>
</div></body></html>"""
