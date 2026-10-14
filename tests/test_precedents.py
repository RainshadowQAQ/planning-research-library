from app.precedents import extract

def items(groups,kind='similar'):
    return next(g for g in groups if g['kind']==kind)['items']

def test_numbered_sections_and_sentence_decisions():
    pages=['''5. Previous Applications
The site is the subject of Application No. A/YL/10 which was rejected by the Committee on 3.4.2018.
6. Similar Applications
Applications No. A/YL/20 and A/YL/21 for similar uses were approved with conditions by the Committee on 1.2.2019 and 5.6.2020 respectively.
Application No. A/YL/22 was approved by the Board on review on 7.8.2021. The current application A/YL/30 is the subject.
7. The Site and Its Surrounding Areas
A/YL/99 is mentioned outside the sections and is ignored.''']
    groups=extract(pages,'A/YL/30')
    assert [(i['case_no'],i['decision'],i['decision_date'],i['page']) for i in items(groups,'previous')]==[('A/YL/10','rejected','2018-04-03',1)]
    similar=[(i['case_no'],i['decision']) for i in items(groups)]
    assert similar==[('A/YL/20','approved_with_conditions'),('A/YL/21','approved_with_conditions'),('A/YL/22','approved')]
    assert all(i['excerpt'] and i['case_no'] in i['excerpt'] or i['case_no']=='A/YL/21' for i in items(groups))

def test_appendix_table_rows_read_decision_per_row_across_pages():
    pages=['''Appendix III
Similar Applications within the "AGR" Zone
No. Application No. Uses/Development Date of Consideration Decision
1 A/YL-KTN/101 Temporary shop 12.3.2019 Approved
2 A/YL-KTN/102 Temporary warehouse 4.6.2019 Rejected''','''3 A/YL-KTN/103 Temporary shop 9.9.2020 Approved with conditions
4 A/YL-KTN/104 Temporary shop 1.1.2021 Withdrawn''']
    rows=[(i['case_no'],i['decision'],i['decision_date'],i['page']) for i in items(extract(pages,'A/YL-KTN/200'))]
    assert rows==[('A/YL-KTN/101','approved','2019-03-12',1),('A/YL-KTN/102','rejected','2019-06-04',1),
                  ('A/YL-KTN/103','approved_with_conditions','2020-09-09',2),('A/YL-KTN/104','withdrawn','2021-01-01',2)]

def test_no_precedents_keeps_the_papers_own_statement():
    groups=extract(['5. Previous Application\nThere is no previous application covering the Premises.\n6. Similar Application\nThere is no similar application within the same zone.\n7. Other'],'A/K1/1')
    assert all(g['items']==[] for g in groups)
    assert [g['statements'][0]['text'] for g in groups]==['There is no previous application covering the Premises.','There is no similar application within the same zone.']

def test_unreadable_wording_is_unknown_not_guessed():
    groups=extract(['6. Similar Application\nApplication No. A/H1/5 is referred to in Plan A-1 for location only.'],'A/H1/9')
    assert items(groups)[0]['decision']=='unknown'
