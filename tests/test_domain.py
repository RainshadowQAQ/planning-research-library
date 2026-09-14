import json
from pathlib import Path
from app.domain import normalize_case, exact_candidates, hk_date, agenda_documents, documents_from_detail
import pytest

SAMPLE=Path('docs/research/2026-09-05-api-feasibility')
def test_full_number_does_not_select_related():
    assert exact_candidates([{'caseNo':'A/K1/265-1'}], 'A/K1/265') == []
    assert normalize_case(' a/k1/265 ') == 'A/K1/265'
    with pytest.raises(ValueError): normalize_case('../etc/passwd')
def test_hong_kong_date():
    assert hk_date('/Date(1665676800000+0800)/') == '2022-10-14'
    assert hk_date(None) is None
def test_agenda_scope():
    html='<table><tr><td>A/K1/265</td><td><a href="/a.pdf">Paper</a></td></tr><tr><td>A/K1/265-1</td><td><a href="/b.pdf">Paper</a></td></tr></table>'
    docs=agenda_documents(html,'https://www.tpb.gov.hk/a.html','A/K1/265','2022-10-14')
    assert [d['url'] for d in docs] == ['https://www.tpb.gov.hk/a.pdf']
def test_cutoff_excludes_future_meeting():
    detail=json.loads((SAMPLE/'perm-detail.json').read_text())['Data'][0]
    docs=documents_from_detail(detail,'2022-08-01')
    assert all(d['event_date'] is None or d['event_date'] <= '2022-08-01' for d in docs)
    assert not any('705' in d['url'] for d in docs)
    assert not any(d['kind']=='Gist' for d in docs)

def test_iso_timestamp_converts_timezone():
    assert hk_date('2022-10-13T18:00:00+00:00')=='2022-10-14'
