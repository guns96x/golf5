"""Ingest curated external findings into knowledge/edc16_knowledge.db and render a Markdown digest.

Input JSON (knowledge/13_reports/<name>.json):
{
  "title": "...", "collected": "YYYY-MM-DD",
  "sources": [{"key": "...", "title": "...", "url": "...", "publisher": "...", "date": "...",
               "source_type": "forum|tuner_site|oem_manual|oem_ssp|community_guide|project_measurement",
               "authority": 1-5, "applicability": 1-5, "notes": "..."}],
  "claims": [{"source": "<source key>", "text": "...", "evidence": "short quote/paraphrase",
              "topic": "...", "status": "LEAD|CORROBORATED|CONTRADICTED|OEM_SPEC|PROJECT_VERIFIED",
              "engine_code": "BLS|BKC|PD|...", "ecu_family": "EDC16U34|EDC16|...", "map_name": "...",
              "conditions": "...", "corroborated_by": ["<source key>"], "contradicted_by": ["<source key>"],
              "project_relevance": "..."}],
  "conflicts": [{"topic": "...", "a": "<claim index>", "b": "<claim index>", "explanation": "...",
                 "required_experiment": "...", "verdict": "..."}]
}
Idempotent: sources are keyed by URL, claims by (source, text).
Epistemic rule: forum/tuner claims never enter as verified facts for this car; only PROJECT_VERIFIED uses project data.

  python tools/ingest_findings.py knowledge/13_reports/web-research-2026-09-16.json
"""
import json
import os
import sqlite3
import sys

DB = 'knowledge/edc16_knowledge.db'
AUTHORITY_CAP = {'forum': 2, 'tuner_site': 2, 'community_guide': 3, 'oem_manual': 5, 'oem_ssp': 5,
                 'project_measurement': 4}


def upsert_source(cur, s):
    row = cur.execute('SELECT id FROM sources WHERE url_or_path = ?', (s['url'],)).fetchone()
    authority = min(s['authority'], AUTHORITY_CAP.get(s['source_type'], 3))
    vals = (s['title'], s.get('author'), s.get('publisher'), s.get('date'), s['source_type'], authority,
            s['applicability'], s['url'], s.get('notes'))
    if row:
        cur.execute('UPDATE sources SET title=?, author=?, publisher=?, publication_date=?, source_type=?, '
                    'authority_level=?, applicability_level=?, url_or_path=?, notes=? WHERE id=?', vals + (row[0],))
        return row[0], authority
    cur.execute('INSERT INTO sources (title, author, publisher, publication_date, source_type, authority_level, '
                'applicability_level, url_or_path, notes) VALUES (?,?,?,?,?,?,?,?,?)', vals)
    return cur.lastrowid, authority


def main(path):
    data = json.load(open(path, encoding='utf-8'))
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    src_ids, src_auth = {}, {}
    for s in data['sources']:
        src_ids[s['key']], src_auth[s['key']] = upsert_source(cur, s)
    claim_ids = []
    for c in data['claims']:
        sid = src_ids[c['source']]
        src = next(s for s in data['sources'] if s['key'] == c['source'])
        conditions = '; '.join(x for x in (c.get('topic'), c.get('conditions'), c.get('project_relevance')) if x)
        row = cur.execute('SELECT id FROM claims WHERE source_id=? AND claim_text=?', (sid, c['text'])).fetchone()
        vals = (c['text'], sid, c.get('section'), c.get('evidence'), src['source_type'], src_auth[c['source']],
                src['applicability'], c.get('ecu_family'), c.get('engine_code'), c.get('map_name'), conditions,
                c['status'], ','.join(c.get('corroborated_by', [])), ','.join(c.get('contradicted_by', [])))
        if row:
            cur.execute('UPDATE claims SET claim_text=?, source_id=?, page_or_section=?, exact_evidence=?, source_type=?, '
                        'authority_score=?, applicability_score=?, ecu_family=?, engine_code=?, map_name=?, conditions=?, '
                        'epistemic_status=?, corroborated_by=?, contradicted_by=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
                        vals + (row[0],))
            claim_ids.append(row[0])
        else:
            cur.execute('INSERT INTO claims (claim_text, source_id, page_or_section, exact_evidence, source_type, '
                        'authority_score, applicability_score, ecu_family, engine_code, map_name, conditions, '
                        'epistemic_status, corroborated_by, contradicted_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', vals)
            claim_ids.append(cur.lastrowid)
    for k in data.get('conflicts', []):
        a, b = data['claims'][k['a']], data['claims'][k['b']]
        exists = cur.execute('SELECT id FROM conflicts WHERE topic=? AND claim_a_id=? AND claim_b_id=?',
                             (k['topic'], claim_ids[k['a']], claim_ids[k['b']])).fetchone()
        if not exists:
            cur.execute('INSERT INTO conflicts (topic, claim_a_id, claim_b_id, claim_a_text, claim_b_text, source_a, source_b, '
                        'possible_explanation, required_experiment, provisional_verdict) VALUES (?,?,?,?,?,?,?,?,?,?)',
                        (k['topic'], claim_ids[k['a']], claim_ids[k['b']], a['text'], b['text'], a['source'], b['source'],
                         k['explanation'], k['required_experiment'], k['verdict']))
    cur.execute("INSERT INTO claims_fts(claims_fts) VALUES('rebuild')")
    conn.commit()
    print('sources %d, claims %d, conflicts %d -> %s' % (len(data['sources']), len(data['claims']),
                                                        len(data.get('conflicts', [])), DB))
    md = os.path.join('docs', 'knowledge', os.path.splitext(os.path.basename(path))[0] + '.md')
    with open(md, 'w', encoding='utf-8') as f:
        f.write(render(data))
    print('digest ->', md)


def render(d):
    by_key = {s['key']: s for s in d['sources']}
    L = ['# %s' % d['title'], '', 'Collected %s. Generated from `knowledge/13_reports/` JSON by `tools/ingest_findings.py`; '
         'also stored in `knowledge/edc16_knowledge.db` (tables `sources`, `claims`, `conflicts`).' % d['collected'], '',
         'Status legend: `OEM_SPEC` factory documentation · `PROJECT_VERIFIED` confirmed with this car\'s BIN/A2L/logs · '
         '`CORROBORATED` ≥2 independent external sources · `LEAD` single external source, unverified · `CONTRADICTED` '
         'conflicts with project data.', '']
    topics = []
    for c in d['claims']:
        if c['topic'] not in topics:
            topics.append(c['topic'])
    for t in topics:
        L += ['## %s' % t, '', '| status | claim | source | relevance to this car |', '|---|---|---|---|']
        for c in d['claims']:
            if c['topic'] != t:
                continue
            s = by_key[c['source']]
            L.append('| `%s` | %s%s | [%s](%s) (%s, authority %d) | %s |' % (
                c['status'], c['text'].replace('|', '/'),
                (' — «%s»' % c['evidence'].replace('|', '/')) if c.get('evidence') else '',
                s['title'].replace('|', '/'), s['url'], s['source_type'], min(s['authority'], AUTHORITY_CAP.get(s['source_type'], 3)),
                (c.get('project_relevance') or '').replace('|', '/')))
        L.append('')
    if d.get('conflicts'):
        L += ['## Conflicts', '', '| topic | A | B | explanation | experiment | verdict |', '|---|---|---|---|---|---|']
        for k in d['conflicts']:
            L.append('| %s | %s | %s | %s | %s | %s |' % (k['topic'], d['claims'][k['a']]['text'], d['claims'][k['b']]['text'],
                                                         k['explanation'], k['required_experiment'], k['verdict']))
        L.append('')
    L += ['## Sources', '']
    for s in d['sources']:
        L.append('- [%s](%s) — %s, %s%s' % (s['title'], s['url'], s['source_type'], s.get('publisher') or '',
                                            (', ' + s['date']) if s.get('date') else ''))
    return '\n'.join(L) + '\n'


if __name__ == '__main__':
    main(sys.argv[1])
