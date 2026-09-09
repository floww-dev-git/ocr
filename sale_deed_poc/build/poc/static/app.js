// Sale Deed Chain Validator — frontend. Upload → SSE analyze → progressive render.
'use strict';

const $ = (id) => document.getElementById(id);
let files = [];                 // File[]
const deedMap = {};             // deed_id -> extracted deed payload

// ---------- file selection ----------
const drop = $('drop'), fileInput = $('file');
drop.addEventListener('click', () => fileInput.click());
drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('over'); });
drop.addEventListener('dragleave', () => drop.classList.remove('over'));
drop.addEventListener('drop', (e) => {
  e.preventDefault(); drop.classList.remove('over');
  addFiles(e.dataTransfer.files);
});
fileInput.addEventListener('change', () => addFiles(fileInput.files));

function addFiles(list) {
  for (const f of list) files.push(f);
  renderFileList();
}
function removeFile(i) { files.splice(i, 1); renderFileList(); }

function renderFileList() {
  const ul = $('filelist');
  ul.innerHTML = '';
  files.forEach((f, i) => {
    const li = document.createElement('li');
    li.innerHTML = `<span class="id">${String.fromCharCode(65 + i)}</span>
      <span class="nm">${esc(f.name)}</span>
      <button class="rm" title="remove">×</button>`;
    li.querySelector('.rm').onclick = () => removeFile(i);
    ul.appendChild(li);
  });
  $('go').disabled = files.length === 0;
  $('hint').textContent = files.length < 2
    ? 'Add 2 or more deeds to validate a chain.'
    : `${files.length} deeds ready.`;
}

// ---------- analyze ----------
$('go').addEventListener('click', analyze);
$('fullReportBtn').addEventListener('click', openFullReport);

// open the full analysis as a clean, standalone single page (demo style), from live data
function openFullReport() {
  const styleTag = document.querySelector('style').outerHTML;
  const html = `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sale Deed — Title Chain Report</title>${styleTag}</head>
    <body><div class="wrap">
      <header>
        <div class="kicker">Solution 4 · Sale Deed Chain Validator</div>
        <h1>Title <span class="em">Chain Report</span></h1>
      </header>
      ${$('risk').innerHTML}
      ${$('verdict').innerHTML}
      <div class="glance">${$('glance').innerHTML}</div>
      <h2 style="font-size:18px"><span class="dot"></span>Ownership timeline</h2>
      <div class="timeline">${$('timeline').innerHTML}</div>
      <h2 style="font-size:18px"><span class="dot"></span>Chronology of activity</h2>
      ${$('chronology').innerHTML}
      <h2 style="font-size:18px"><span class="dot"></span>Findings</h2>
      ${$('findings').innerHTML}
      <div class="note" style="background:#fbfaf5;border:1px solid var(--line);border-radius:13px;padding:14px 18px;margin-top:18px;font-size:12.5px;color:var(--soft)">
        Automated screening of the documents provided. Not a legal opinion on title and not verified against the government registry. It flags; a human decides.
      </div>
    </div></body></html>`;
  const url = URL.createObjectURL(new Blob([html], { type: 'text/html' }));
  window.open(url, '_blank');
}

async function analyze() {
  $('go').disabled = true;
  $('errSlot').innerHTML = '';
  $('deeds').innerHTML = '';
  $('files').innerHTML = '';
  $('deedProgress').textContent = '';
  $('chainSec').classList.add('hidden');
  $('deedsSec').classList.remove('hidden');

  // one status row per uploaded file (a file may split into several documents)
  files.forEach((f, i) => $('files').appendChild(fileRow(i, f.name)));

  let session;
  try {
    const fd = new FormData();
    files.forEach((f) => fd.append('files', f));
    const res = await fetch('/api/upload', { method: 'POST', body: fd });
    session = await res.json();
  } catch (e) {
    return showError('Upload failed: ' + e.message);
  }

  let read = 0;
  const es = new EventSource(`/api/analyze/${session.session_id}`);

  es.addEventListener('file_start', (ev) => {
    const d = JSON.parse(ev.data);
    setFileBadge(d.file_index, '<span class="spin"></span> reading…', 'read');
  });

  // Pass 1 result — what's inside the file
  es.addEventListener('file_inventory', (ev) => {
    const d = JSON.parse(ev.data);
    const n = d.documents.length;
    setFileBadge(d.file_index, `${n} document${n > 1 ? 's' : ''} found`, n > 1 ? 'multi' : '');
    const row = document.getElementById('frow-' + d.file_index);
    if (row && n) {
      const items = d.documents.map((doc) =>
        `<div class="invitem">${doc.is_title_doc ? '📄' : '📎'} <b>${esc(doc.doc_type)}</b> <span class="muted">· ${esc(doc.page_label)}</span>${doc.summary ? ` — ${esc(doc.summary)}` : ''}</div>`
      ).join('');
      const sub = document.createElement('div'); sub.className = 'invlist'; sub.innerHTML = items;
      row.appendChild(sub);
    }
  });

  // Pass 2 result — a fully extracted document
  es.addEventListener('deed', (ev) => {
    const d = JSON.parse(ev.data);
    deedMap[d.deed_id] = d.deed;
    read++;
    $('deedProgress').textContent = `${read} document(s) read`;
    createDeedCard(d);
  });

  es.addEventListener('deed_error', (ev) => {
    const d = JSON.parse(ev.data);
    setFileBadge(d.file_index, 'failed', 'read');
    showError(`${esc(d.filename || 'File')}: ${esc(d.message)}`);
  });

  es.addEventListener('warning', (ev) => { showWarning(JSON.parse(ev.data).message); });
  es.addEventListener('file_done', () => {});
  es.addEventListener('chain', (ev) => renderChain(JSON.parse(ev.data)));
  es.addEventListener('error', (ev) => {
    try { showError(JSON.parse(ev.data).message); } catch { /* stream closed */ }
  });
  es.addEventListener('done', () => { es.close(); $('go').disabled = false; });
}

function showError(msg) {
  $('errSlot').innerHTML = `<div class="errbox">${esc(msg)}</div>`;
  $('go').disabled = false;
}

function showWarning(msg) {
  const d = document.createElement('div');
  d.className = 'errbox';
  d.style.cssText = 'background:#fdebdd;border-color:#f2c39b;color:var(--gap);margin-bottom:10px';
  d.textContent = '⚠ ' + msg;
  $('errSlot').appendChild(d);
}

// ---------- file rows & deed cards ----------
function fileRow(i, filename) {
  const el = document.createElement('div');
  el.className = 'frow'; el.id = 'frow-' + i;
  el.innerHTML = `<span class="fn">${esc(filename)}</span><span class="b2">queued</span>`;
  return el;
}
function setFileBadge(i, html, cls) {
  const row = document.getElementById('frow-' + i);
  if (!row) return;
  const b = row.querySelector('.b2');
  b.className = 'b2' + (cls ? ' ' + cls : '');
  b.innerHTML = html;
}

function createDeedCard(d) {
  const el = document.createElement('div');
  el.className = 'dcard done'; el.id = 'card-' + d.deed_id;
  const role = d.doc_role
    ? `<span class="docrole ${d.doc_role}">${d.doc_role === 'primary' ? 'PRIMARY' : 'LINK DOC'}</span>` : '';
  const origin = [esc(d.filename || ''), d.page_label ? esc(d.page_label) : ''].filter(Boolean).join(' · ');
  el.innerHTML = `<div class="dhead"><span class="id">${d.deed_id}</span>
      <div><div class="t">Deed ${d.deed_id}</div><div class="file">${origin} ${role}</div></div>
      <span class="status st-ok">✓ read</span></div>
    <div class="dgridslot"></div>`;
  $('deeds').appendChild(el);
  fillDeedCard(d);
}
function setStatus(card, cls, html) { const s = card.querySelector('.status'); s.className = 'status ' + cls; s.innerHTML = html; }

function fillDeedCard(d) {
  const card = $('card-' + d.deed_id);
  if (!card) return;
  card.className = 'dcard done';
  setStatus(card, 'st-ok', '✓ read');
  const dd = d.deed, p = dd.property || {};
  card.querySelector('.t').textContent = dd.deed_type || `Deed ${d.deed_id}`;

  // crucial details — surfaced as prominent chips
  const pans = [...(dd.sellers || []), ...(dd.buyers || [])].map((x) => x.pan).filter(Boolean);
  const ids = [...(dd.sellers || []), ...(dd.buyers || [])].map((x) => x.aadhaar).filter(Boolean);
  const surveyPlot = [p.survey_no && 'Sy. ' + p.survey_no, p.plot_no && 'Plot ' + p.plot_no].filter(Boolean).join(' ');
  const key = [
    ['Date', dd.registration_date || dd.execution_date],
    ['Doc no', dd.doc_no],
    ['Survey / Plot', surveyPlot],
    ['Extent', p.extent_text],
    ['PAN', pans.join(', ')],
    ['Govt ID', ids.join(', ')],
    ['Value', dd.consideration_text],
  ].filter(([, v]) => v);
  const LABELMAP = { 'Date': 'registration_date', 'Doc no': 'doc_no', 'Survey / Plot': 'survey_no', 'Value': 'consideration' };
  const keystrip = key.map(([k, v]) => {
    const lbl = LABELMAP[k];
    const attr = lbl ? ` data-label="${lbl}" data-deed="${d.deed_id}"` : '';
    return `<span class="kchip"${attr}><b>${k}:</b> ${esc(v)}</span>`;
  }).join('');

  const rows = [
    ['Registered at (SRO)', esc(dd.sro || '—')],
    ['Seller', partyStr(dd.sellers)],
    ['Buyer', partyStr(dd.buyers)],
    ['Boundaries', esc(p.boundaries || '—')],
    ['Source of title', (dd.prior_deed_refs || []).length ? dd.prior_deed_refs.map((r) => `<code>${esc(r)}</code>`).join(' ') : '—'],
  ];
  const grid = rows.map(([k, v]) => `<div><div class="k">${k}</div><div>${v}</div></div>`).join('');
  const flags = (d.flags || []).map((f) => `<span class="flag f-${f.severity}" title="${esc(f.message)}">${esc(f.message)}</span>`).join('');

  // document viewer + provenance overlay
  const pageImgs = d.page_images || [];
  const boxes = dd.boxes || [];
  let docHtml = '';
  if (pageImgs.length) {
    docHtml = `<button class="doctoggle">📄 View document &amp; provenance</button>
      <div class="docview" id="dv-${d.deed_id}">
        <p class="provhint">Boxes mark where each value was read. Click a highlighted chip above to spotlight its source on the page.</p>
        ${pageImgs.map((url, n) => buildPage(d.deed_id, url, n, boxes)).join('')}
      </div>`;
  }

  card.querySelector('.dgridslot').innerHTML =
    `<div class="keystrip">${keystrip}</div><div class="dgrid">${grid}</div>` +
    `${flags ? `<div class="flags">${flags}</div>` : ''}${docHtml}`;

  // wire interactions
  const toggle = card.querySelector('.doctoggle');
  if (toggle) toggle.onclick = () => document.getElementById('dv-' + d.deed_id).classList.toggle('open');
  card.querySelectorAll('.kchip[data-label]').forEach((chip) => {
    chip.onclick = () => highlightBox(d.deed_id, chip.getAttribute('data-label'));
  });
}

function buildPage(deedId, url, n, boxes) {
  const onPage = boxes.filter((b) => (b.page || 0) === n && Array.isArray(b.box) && b.box.length === 4);
  const overlays = onPage.map((b) => {
    const [ymin, xmin, ymax, xmax] = b.box;
    const st = `top:${ymin / 10}%;left:${xmin / 10}%;width:${(xmax - xmin) / 10}%;height:${(ymax - ymin) / 10}%`;
    return `<div class="bbox" id="bx-${deedId}-${esc(b.label)}" style="${st}"><span class="blabel">${esc(b.label)}</span></div>`;
  }).join('');
  return `<div class="pagewrap"><img src="${url}" alt="deed ${deedId} page ${n + 1}">${overlays}</div>`;
}

function highlightBox(deedId, label) {
  const view = document.getElementById('dv-' + deedId);
  if (view) view.classList.add('open');
  document.querySelectorAll('#dv-' + deedId + ' .bbox').forEach((b) => b.classList.remove('active'));
  const box = document.getElementById('bx-' + deedId + '-' + label);
  if (box) { box.classList.add('active'); box.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
}

function partyStr(parties, max = 3) {
  if (!parties || !parties.length) return '—';
  const rows = parties.slice(0, max).map((p) => {
    const orig = p.name_original ? ` <span class="orig">(${esc(p.name_original)})</span>` : '';
    const rel = p.relation && p.relative_name ? ` <span class="muted">· ${esc(p.relation)} ${esc(p.relative_name)}</span>` : '';
    const id = [p.pan && 'PAN ' + p.pan, p.aadhaar && 'ID ' + p.aadhaar].filter(Boolean).map(esc).join(' · ');
    return `${esc(p.name)}${orig}${rel}${id ? `<span class="idtag">${id}</span>` : ''}`;
  });
  const extra = parties.length - max;
  if (extra > 0) rows.push(`<span class="muted">&amp; ${extra} more</span>`);
  return rows.join('<br>');
}

// ---------- chain ----------
function renderChain(r) {
  $('chainSec').classList.remove('hidden');

  // risk / fraud panel
  const risk = r.risk;
  if (risk) {
    const sigs = (risk.signals || []).map((s) =>
      `<div class="r ${s.severity}"><span class="sv">${s.severity.toUpperCase()}</span><div><b>${esc(s.title)}</b><div class="d">${esc(s.detail)}</div></div></div>`
    ).join('');
    $('risk').innerHTML =
      `<div class="riskpanel"><div class="score risk-${esc(risk.level)}">${esc(String(risk.score))}</div>
        <div><div class="rt">Risk: ${esc(risk.level)}</div>
        <div class="rs">${(risk.signals || []).length} signal(s) across the bundle · higher score = more to check.</div></div></div>` +
      (sigs ? `<div class="risksig">${sigs}</div>` : '<p class="lead">No risk signals raised.</p>');
  } else { $('risk').innerHTML = ''; }

  // verdict banner
  const icon = { intact: '✅', review: '⚠️', broken: '⛔' }[r.overall] || 'ℹ️';
  const c = r.counts || {};
  const counts = [
    c.linked ? `<span class="vc ok">✓ ${c.linked} clean</span>` : '',
    c.weak ? `<span class="vc warn">⚠ ${c.weak} weak</span>` : '',
    c.gap ? `<span class="vc gap">⛳ ${c.gap} gap</span>` : '',
    c.broken ? `<span class="vc broke">✕ ${c.broken} broken</span>` : '',
  ].join('');
  $('verdict').innerHTML = `<div class="verdict ${r.overall}">
      <div class="badge">${icon}</div>
      <div><h3>${esc(r.overall_label || '')}</h3><p>${esc(r.overall_blurb || '')}</p>
      <div class="counts">${counts}</div></div></div>`;

  // glance
  const g = r.glance || {};
  $('glance').innerHTML = [
    ['Verdict', (r.overall_label || '').split(' ')[0] || '—'],
    ['Deeds', g.deeds ?? '—'],
    ['Span', [g.span_from, g.span_to].filter(Boolean).join(' → ') || '—'],
    ['Avg confidence', g.avg_confidence ?? '—'],
  ].map(([l, v]) => `<div class="g"><div class="l">${l}</div><div class="v">${esc(String(v))}</div></div>`).join('');

  // timeline — deed by deed, with loud break markers
  const tl = $('timeline');
  tl.innerHTML = '';
  const ordered = r.ordered_deed_ids || [];
  const links = r.links || [];

  // chronological position of each deed, so labels read 1 → 2 → 3 (not scrambled letters)
  const ord = {};
  ordered.forEach((id, i) => { ord[id] = i + 1; });

  // up-front, plain-language break summary
  links.forEach((l) => {
    if (l.verdict === 'broken' || l.verdict === 'gap') {
      const n = document.createElement('div');
      n.className = 'breaknote ' + l.verdict;
      const word = l.verdict === 'broken' ? '⛔ Chain breaks' : '⛳ Deed missing';
      n.textContent = `${word} between Deed ${ord[l.from_deed]} and Deed ${ord[l.to_deed]}`;
      tl.appendChild(n);
    }
  });

  ordered.forEach((id, k) => {
    tl.appendChild(tlDeed(id, deedMap[id] || {}, k + 1));
    if (k < ordered.length - 1) tl.appendChild(tlJoin(links[k], deedMap[ordered[k]], deedMap[ordered[k + 1]]));
  });

  // chronology table
  $('chronology').innerHTML = chronologyTableHTML(r);

  // findings
  $('findings').innerHTML = (r.findings || []).map((f) =>
    `<div class="finding ${f.severity}"><h4><span class="sev f-${f.severity === 'clear' ? 'low' : f.severity}">${f.severity.toUpperCase()}</span>${esc(f.title)}</h4><div class="body">${esc(f.detail)}</div></div>`
  ).join('') || '<p class="lead">No findings.</p>';

  $('chainSec').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// compact party names: first 2 + "& N more" so a joint-family list doesn't swallow the page
// chronology of activity — one row per transaction, in date order, with specifics
function chronologyTableHTML(r) {
  const ordered = r.ordered_deed_ids || [];
  const links = r.links || [];
  if (!ordered.length) return '<p class="lead">No transactions.</p>';
  const STAT = {
    origin: ['origin', 'background:var(--chip);color:var(--soft)'],
    linked: ['✓ linked', 'background:#e3f3eb;color:var(--land)'],
    weak: ['⚠ review', 'background:#fdeede;color:var(--warn)'],
    gap: ['⛳ gap', 'background:#fde7da;color:var(--gap)'],
    broken: ['⛔ broken', 'background:#fce4ee;color:var(--broke)'],
  };
  const rows = ordered.map((id, k) => {
    const dd = deedMap[id] || {}, p = dd.property || {};
    const v = k > 0 ? (links[k - 1] || {}).verdict || 'origin' : 'origin';
    const [label, css] = STAT[v] || STAT.origin;
    const prop = [p.survey_no && 'Sy. ' + p.survey_no, p.plot_no && 'Plot ' + p.plot_no].filter(Boolean).map(esc).join(' ') || '—';
    const ext = p.extent_text ? esc(p.extent_text) : (p.extent_sqyd ? p.extent_sqyd + ' sq.yd' : '—');
    return `<tr>
      <td>${k + 1}</td>
      <td>${esc(dd.registration_date || dd.execution_date || '—')}</td>
      <td>${esc(dd.deed_type || '—')}${dd.doc_no ? `<br><code>${esc(dd.doc_no)}</code>` : ''}</td>
      <td>${partyNames(dd.sellers)} <span class="arrow" style="color:var(--deed)">→</span> ${partyNames(dd.buyers)}</td>
      <td>${prop}<br><span class="muted">${ext}</span></td>
      <td>${esc(dd.consideration_text || '—')}</td>
      <td><span class="vc" style="${css};font-weight:700;padding:2px 9px;border-radius:20px;font-size:11px">${label}</span></td>
    </tr>`;
  }).join('');
  return `<table>
    <tr><th>#</th><th>Date</th><th>Activity</th><th>From → To</th><th>Property</th><th>Value</th><th>Continuity</th></tr>
    ${rows}</table>`;
}

function partyNames(ps, max = 2) {
  if (!ps || !ps.length) return '<span class="muted">unknown</span>';
  const shown = ps.slice(0, max).map((p) =>
    esc(p.name || '?') + (p.name_original ? ` <span class="orig">(${esc(p.name_original)})</span>` : '')).join(', ');
  const extra = ps.length - max;
  return shown + (extra > 0 ? ` <span class="muted">&amp; ${extra} more</span>` : '');
}

// one card per deed (transfer); `ordinal` is its chronological position (1, 2, 3…)
function tlDeed(id, dd, ordinal) {
  const el = document.createElement('div');
  el.className = 'tldeed';
  const meta = [dd.doc_no, dd.registration_date, dd.consideration_text].filter(Boolean).map(esc).join(' · ');
  el.innerHTML = `<div class="dn">${esc(String(ordinal))}</div>
    <div><div class="ttl">${esc(dd.deed_type || 'Deed')} <span class="muted" style="font-weight:400;font-size:12px">· ref ${esc(id)}</span></div>
      <div class="flow">${partyNames(dd.sellers)}<span class="arrow">→</span>${partyNames(dd.buyers)}</div>
      ${meta ? `<div class="meta">${meta}</div>` : ''}</div>`;
  return el;
}

// the join BETWEEN two consecutive deeds — where a break actually lives
function tlJoin(link, prevDeed, nextDeed) {
  const v = link ? link.verdict : 'linked';
  const note = link && link.notes && link.notes.length ? link.notes.join(' ') : '';
  const score = link && link.id_score != null ? link.id_score : null;

  if (v === 'broken' || v === 'gap') {
    const el = document.createElement('div');
    el.className = 'rupture ' + v;
    const head = v === 'broken' ? 'Chain breaks here' : 'A deed is missing here';
    const ic = v === 'broken' ? '⛔' : '⛳';
    // name-match score is only meaningful for an identity break
    const scoreTag = (v === 'broken' && score != null)
      ? ` <span style="font-weight:400;font-size:12.5px;color:var(--soft)">· name match ${score}/100</span>` : '';
    let mm = '';
    if (v === 'broken') {
      mm = `<div class="mm">Buyer in ${esc((prevDeed || {}).doc_no || 'previous deed')}: ${partyNames((prevDeed || {}).buyers)}<br>` +
           `Seller in ${esc((nextDeed || {}).doc_no || 'next deed')}: ${partyNames((nextDeed || {}).sellers)}<br>` +
           `<span class="x">✕ these should be the same person — they do not match.</span></div>`;
    }
    el.innerHTML = `<div class="ic">${ic}</div><div>
      <div class="rh">${esc(head)}${scoreTag}</div>
      <div class="rd">${esc(note || 'Ownership does not carry over between these two deeds.')}</div>${mm}</div>`;
    return el;
  }

  const el = document.createElement('div');
  el.className = 'tljoin ' + (v === 'weak' ? 'weak' : 'ok');
  const label = v === 'weak' ? '⚠ weak link' : '✓ ownership carries over';
  const scoreTxt = score != null ? ` · ${score}/100` : '';
  el.innerHTML = `<span class="jb">${esc(label + scoreTxt)}</span>${note ? `<span class="jt">${esc(note)}</span>` : ''}`;
  return el;
}

function esc(s) { return String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }
