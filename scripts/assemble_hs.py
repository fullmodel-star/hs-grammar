# -*- coding: utf-8 -*-
"""組裝高中英語文法 master.json。
輸入: data/wf_output.json (工作流產出: grammar[], reading[]) + data/words6000_raw.json
輸出: data/master.json (build_app.py 可直接吃)"""
import json, os, sys
try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception: pass
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'data')

wf = json.load(open(os.path.join(D, 'wf_output.json'), encoding='utf-8'))
words = json.load(open(os.path.join(D, 'words6000_raw.json'), encoding='utf-8'))

GROUP_ORDER = ['動詞與語態', '子句', '句型與句構', '詞類與用法']

notes = {}
taxonomy_topics = []
questions = []
gid = 0

# 依 group 順序、再依工作流回傳順序排主題
gram = wf['grammar']
def gkey(g):
    grp = g['topic']['group']
    return (GROUP_ORDER.index(grp) if grp in GROUP_ORDER else 99)
gram_sorted = sorted(gram, key=gkey)

for g in gram_sorted:
    t = g['topic']
    key, label, group = t['key'], t['label'], t['group']
    taxonomy_topics.append({'key': key, 'label': label, 'group': group})
    # note
    n = g.get('note') or {}
    n = dict(n); n['topicKey'] = key
    if not n.get('title'): n['title'] = label
    notes[key] = n
    # questions d1/d2/d3
    for diff, arr in ((1, g.get('d1') or []), (2, g.get('d2') or []), (3, g.get('d3') or [])):
        for q in arr:
            opts = q.get('options') or []
            ans = q.get('answer')
            if len(opts) != 4 or not isinstance(ans, int) or ans < 0 or ans > 3:
                continue
            if not q.get('stem'):
                continue
            gid += 1
            questions.append({
                'id': f'GH{gid:04d}', 'type': 'grammar',
                'unitGroup': group, 'unit': label, 'topicKey': key,
                'level': diff, 'difficulty': diff, 'difficultyScore': 0.2 + 0.3 * (diff - 1),
                'stem': q['stem'], 'options': opts, 'answer': ans,
                'explanation': q.get('explanation', ''), 'explSource': 'ai',
                'source': '原創',
                'flags': {'ocr': False, 'answerCheck': 'ok'},
            })

# ---- 閱讀 ----
passages = []
rid = 0; pid = 0
GENRE_SEEN = []
for r in wf.get('reading', []):
    spec = r.get('spec') or {}
    genre = spec.get('genre', '文章'); level = spec.get('level', 1)
    if genre not in GENRE_SEEN: GENRE_SEEN.append(genre)
    pid += 1
    passage_id = f'PH{pid:03d}'
    passages.append({
        'passageId': passage_id, 'genre': genre, 'unitGroup': '閱讀',
        'level': level, 'hasText': True, 'text': r.get('text', ''),
        'title': r.get('title', ''), 'source': '原創', 'ocr': False,
    })
    for q in r.get('questions') or []:
        opts = q.get('options') or []; ans = q.get('answer')
        if len(opts) != 4 or not isinstance(ans, int) or ans < 0 or ans > 3 or not q.get('stem'):
            continue
        rid += 1
        questions.append({
            'id': f'RH{rid:04d}', 'type': 'reading', 'passageId': passage_id,
            'unitGroup': '閱讀', 'unit': genre, 'genre': genre,
            'level': level, 'difficulty': level, 'difficultyScore': 0.2 + 0.3 * (level - 1),
            'stem': q['stem'], 'options': opts, 'answer': ans,
            'explanation': q.get('explanation', ''), 'explSource': 'ai',
            'source': '原創', 'flags': {'ocr': False, 'answerCheck': 'ok'},
        })

# ---- 單字 (高中6000, 依大考中心6級分組) ----
vocab = []
words_sorted = sorted(words, key=lambda x: (x.get('level', 1), str(x.get('word', '')).lower()))
for i, x in enumerate(words_sorted, 1):
    lv = x.get('level', 1)
    vocab.append({
        'id': f'V-{i:04d}', 'type': 'vocab', 'unitGroup': '單字',
        'unit': f'第{lv}級', 'level': lv, 'difficulty': min(lv, 3),
        'word': x.get('word', ''), 'pos': x.get('pos', ''), 'zh': x.get('zh_tw', ''),
        'example': x.get('ex', ''), 'exampleZh': x.get('exZh', ''),
    })

readingGenres = GENRE_SEEN or ['文章']

master = {
    'version': 'hs-1.0',
    'notes': notes,
    'taxonomy': {'grammarTopics': taxonomy_topics, 'readingGenres': readingGenres},
    'counts': {
        'grammar': sum(1 for q in questions if q['type'] == 'grammar'),
        'reading': sum(1 for q in questions if q['type'] == 'reading'),
        'passages': len(passages), 'vocab': len(vocab),
    },
    'questions': questions, 'passages': passages, 'vocab': vocab,
}
json.dump(master, open(os.path.join(D, 'master.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print('✓ master.json 完成')
print('  文法主題:', len(taxonomy_topics), '| 群組:', GROUP_ORDER)
print('  counts:', master['counts'])
# 每主題題數
from collections import Counter
c = Counter((q['unit'], q['difficulty']) for q in questions if q['type'] == 'grammar')
for t in taxonomy_topics:
    d1 = c.get((t['label'], 1), 0); d2 = c.get((t['label'], 2), 0); d3 = c.get((t['label'], 3), 0)
    print(f"   {t['label']}: d1={d1} d2={d2} d3={d3} (共{d1+d2+d3})")
