"""Draft preliminary lean from fixed rule checks over site facts and precedents.

Rules, not free judgement: each finding names its check, the records it read and their
citations. The lean only counts findings; it never weighs them (weighted scores are future work)."""
import re
from datetime import date

RULES_VERSION='2026-10-14'
CHECKS={'C1':'用途許可','C2':'法定上限','C3':'規劃意向','C4':'許可狀態','C5':'附加條件',
        'C6':'先例','C7':'跨鏈一致','C8':'證據充足'}
QUESTIONS=[('use','用途是否允許？'),('limits','是否符合法定限制？'),('history','規劃歷史怎麼說？'),
           ('approvals','還需要哪些其他批准？'),('unknowns','無法評估清單')]
OUTCOMES={'support':'支持','limit':'限制','conflict':'衝突','cannot_assess':'無法評估','planner':'需規劃師判斷'}
SEVERITIES={'blocker':'阻斷','major':'重要','note':'備註'}
LEANS={'optimistic':'偏向樂觀','pessimistic':'偏向悲觀','insufficient':'證據不足'}

def _open(issue):return issue['status']!='resolved'

def _cite_label(c):
    where=f"p.{c['page']}" if c.get('page') else (c.get('locator') or '')
    return f"{c['source']} {c['source_title']} · {where}".strip(' ·')

class _Facts:
    def __init__(self,payload):
        self.claims={c['id']:c for c in payload['claims']}
        self.issues={i['id']:i for i in payload['issues']}
    def claim(self,id):return self.claims.get(id)
    def open_issues(self,claim,only=None):
        return [self.issues[i] for i in claim['issue_ids'] if i in self.issues and _open(self.issues[i]) and (only is None or i in only)]

def _finding(check,question,outcome,severity,text,claims=(),open_issues=(),citations=None):
    cites=citations if citations is not None else [dict(c,label=_cite_label(c)) for f in claims for c in f['citations']]
    return dict(check=check,check_label=CHECKS[check],question=question,
                outcome=outcome,outcome_label=OUTCOMES[outcome],severity=severity,severity_label=SEVERITIES[severity],
                text=text,basis=[f['id'] for f in claims],
                # Pending review or an open issue on a premise makes the finding provisional (覆核閘).
                provisional=any(f['review_status']=='pending' for f in claims) or bool(open_issues),
                gaps=[i['title'] for i in open_issues],citations=cites)

def _c1(facts):
    zoning=facts.claim('ozp-zoning')
    if not zoning:return _finding('C1','use','cannot_assess','major','未有分區資料。')
    gaps=facts.open_issues(zoning)
    if '第一欄' in zoning['value']:
        return _finding('C1','use','support','major','第一欄用途，經常准許。',[zoning],gaps)
    if '第二欄' in zoning['value']:
        return _finding('C1','use','limit','major','第二欄用途，須申請規劃許可。',[zoning],gaps)
    return _finding('C1','use','cannot_assess','major','未載明屬第幾欄。',[zoning],gaps)

def _c3(facts):
    intent=facts.claim('planning-intention')
    if not intent:return None
    return _finding('C3','use','planner','note','是否符合規劃意向，由規劃師判斷。',[intent])

def _blocked(facts,check,question,claim_id,issue_ids,severity,text):
    """A claim whose answer depends on a named open issue cannot be assessed until it is closed."""
    claim=facts.claim(claim_id)
    if not claim:return None
    gaps=facts.open_issues(claim,issue_ids)
    if not gaps:return None
    return _finding(check,question,'cannot_assess',severity,text,[claim],gaps)

def _c4(facts,as_of):
    expiry=facts.claim('original-expiry')
    if not expiry:return _finding('C4','history','cannot_assess','blocker','未有許可期限。')
    m=re.search(r'\d{4}-\d{2}-\d{2}',expiry['value'])
    gaps=facts.open_issues(expiry,{'permission-status-eot'})
    if not m:return _finding('C4','history','cannot_assess','blocker','未能讀出許可期限。',[expiry],gaps)
    until=date.fromisoformat(m[0]);days=(until-as_of).days
    when=f'已過期 {-days} 日' if days<0 else '基準日當日到期' if days==0 else f'尚餘 {days} 日'
    if gaps:
        return _finding('C4','history','cannot_assess','blocker',
                        f'許可期限至 {until.isoformat()}（{when}）。未核實是否已展開或已申請續期。',[expiry],gaps)
    if days<0:return _finding('C4','history','limit','major',f'許可期限至 {until.isoformat()}（{when}），未見續期記錄。',[expiry])
    return _finding('C4','history','support','note',f'許可期限至 {until.isoformat()}（{when}）。',[expiry])

def _c6(precedents):
    if not precedents or precedents.get('status')!='ready':
        return _finding('C6','history','cannot_assess','note','未能讀取主文件。',citations=[])
    s=precedents['summary'];previous,similar=precedents['groups']
    cites=[dict(i['citation'],label=f"主文件 · p.{i['page']}") for g in (previous,similar) for i in g['items']]
    total=s['approved']+s['rejected']+s['other']
    count=f"主文件列出同類申請 {total} 宗：批准 {s['approved']}、拒絕 {s['rejected']}"+(f"、其他 {s['other']}" if s['other'] else '')+'。'
    if s['approved']>s['rejected']:outcome='support'
    elif s['rejected']>s['approved']:outcome='limit'
    else:outcome='cannot_assess'
    finding=_finding('C6','history',outcome,'major' if outcome!='cannot_assess' else 'note',count,citations=cites)
    finding['provisional']=True  # A staff-selected sample, never the full district record.
    return finding

def _c8(facts):
    return [dict(title=i['title'],priority=i['priority'],status=i['status'],needed=i['needed'])
            for i in sorted(facts.issues.values(),key=lambda i:i['priority']) if _open(i)]

def _lean(findings):
    blockers=[f for f in findings if f['severity']=='blocker' and f['outcome'] in ('cannot_assess','conflict')]
    name=lambda f:f"{f['check']} {f['check_label']}"
    if blockers:
        return dict(value='insufficient',label=LEANS['insufficient'],
                    reason='阻斷項：'+'、'.join(map(name,blockers))+'。')
    pro=[f for f in findings if f['outcome']=='support']
    con=[f for f in findings if f['outcome'] in ('limit','conflict')]
    detail=f"支持 {len(pro)}（{'、'.join(map(name,pro)) or '—'}）；限制 {len(con)}（{'、'.join(map(name,con)) or '—'}）"
    if len(pro)>len(con):value='optimistic'
    elif len(con)>len(pro):value='pessimistic'
    else:return dict(value='insufficient',label=LEANS['insufficient'],reason=detail+'，相同。')
    return dict(value=value,label=LEANS[value],reason=detail+'。')

def preliminary_lean(site_facts,precedents,as_of):
    """Findings grouped by question, the open-issue list and a counted draft lean."""
    facts=_Facts(site_facts)
    findings=[f for f in [
        _c1(facts),_c3(facts),
        _blocked(facts,'C2','limits','pr-application',{'ozp-notes-pr-limit'},'note',
                 '地積比約 1.41；未有注釋上限，無法比較。'),
        _c4(facts,as_of),_c6(precedents),
        _blocked(facts,'C5','approvals','approval-conditions',{'conditions-compliance'},'major',
                 '四項批給條件未見履行記錄。'),
        _blocked(facts,'C7','approvals','department-advice',{'lands-lease-consent'},'major',
                 '地政總署指批准後須另申請地契同意；未有地契，未能核對。'),
    ] if f]
    lean=_lean(findings)
    lean['provisional']=any(f['provisional'] for f in findings if f['outcome'] in ('support','limit','conflict'))
    groups=[dict(id=q,label=label,findings=[f for f in findings if f['question']==q]) for q,label in QUESTIONS[:-1]]
    return dict(case_no=site_facts['case_no'],as_of=as_of.isoformat(),rules_version=RULES_VERSION,
                lean=lean,groups=groups,unknowns=dict(label=QUESTIONS[-1][1],items=_c8(facts)))
