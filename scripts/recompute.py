"""Offline audit of the supplied handoff. Standard library only; no model imports/network.

Usage: python scripts/recompute.py --source /path/to/MemRL_stage_handoff_2026-10-20 --out data
Original records are opened read-only. Scores are checked, never rewritten.
"""
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

METHODS = ('no_memory', 'similarity_only', 'memrl_frozen_memory')
TOKENS = ('prompt_tokens', 'completion_tokens', 'total_tokens')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def run(source, out):
    source, out = source.resolve(), out.resolve()
    if out == source or source in out.parents:
        raise ValueError('Output must be outside the read-only source bundle.')
    out.mkdir(parents=True, exist_ok=True)
    used = {}
    def read(rel, lines=False):
        p = source / rel
        used[rel] = sha(p)
        txt = p.read_text(encoding='utf-8')
        return [json.loads(l) for l in txt.splitlines() if l.strip()] if lines else json.loads(txt)
    def write_csv(name, rows):
        with (out / name).open('w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    verified = 0
    for line in (source/'FILES_SHA256.txt').read_text().splitlines():
        h, rel = line.split('  ', 1)
        assert sha(source/rel) == h, rel
        verified += 1
    ar = 'research_records/results/alfworld/unseen_challenge50_frozen_v1/'
    hr = 'research_records/results/harp_aime/memrl_compact_train50_v3/confirmation50_v3/'
    a = read(ar+'eval_results.jsonl', True)
    h = read(hr+'results.jsonl', True)
    am, hm = read(ar+'experiment_manifest.json'), read(hr+'manifest.json')
    ass = read(ar+'eval_summary.json')
    steps = read('research_records/alfworld_interactions/steps.jsonl', True)
    retr = read('research_records/alfworld_interactions/retrievals.jsonl', True)
    assert len(a)==150 and len(h)==100 and len(steps)==2496 and len(retr)==150
    ab = {(r['id'], r['method']):r for r in a}
    hb = {(r['id'], r['method']):r for r in h}
    assert len(ab)==150 and len(hb)==100
    ids = sorted({r['id'] for r in a}); hids = sorted({r['id'] for r in h})
    assert len(ids)==len(hids)==50
    common = {i for i in ids if all(ab[i,m]['final_state']['won'] for m in METHODS)}
    sb = collections.defaultdict(list)
    for s in steps:
        sb[s['id'],s['method']].append(s)
        legal = s['parsed_action'] in s['before']['admissible_commands']
        assert legal == s['action_in_admissible_commands']
        assert sum(s['usage'][t] for t in TOKENS[:2])==s['usage']['total_tokens']
    for rr in retr:
        assert rr['retrieval']==ab[rr['id'],rr['method']]['retrieval']
    aflat=[]
    for r in a:
        ss=sorted(sb[r['id'],r['method']],key=lambda s:s['decision'])
        assert [s['decision'] for s in ss]==list(range(1,len(ss)+1))
        assert len(ss)==r['decisions']
        assert r['success']==r['final_state']['won']==ss[-1]['after']['won']
        assert r['binding']['before_memory']==am['frozen_memory_sha256']
        inv=sum(not s['action_in_admissible_commands'] for s in ss)
        assert inv==r['invalid_actions']
        assert sum(s['finish_reason']=='length' for s in ss)==r['length_limited']
        aflat.append(dict(id=r['id'],method=r['method'],task_type=r['task_type'],success=int(r['success']),
            decisions=len(ss),common_success=int(r['id'] in common),invalid_actions=inv,
            length_limited=r['length_limited'],**{t:sum(s['usage'][t] for s in ss) for t in TOKENS}))
    write_csv('alfworld_per_task.csv',aflat)
    aggregates=[]
    for m in METHODS:
        rr=[r for r in aflat if r['method']==m]; cc=[r for r in rr if r['common_success']]
        row=dict(method=m,tasks=len(rr),successes=sum(r['success'] for r in rr),
            success_rate=sum(r['success'] for r in rr)/len(rr),total_decisions=sum(r['decisions'] for r in rr),
            mean_decisions_all50=statistics.mean(r['decisions'] for r in rr),
            median_decisions_all50=statistics.median(r['decisions'] for r in rr),
            common_success_count=len(cc),mean_decisions_common_success=statistics.mean(r['decisions'] for r in cc),
            invalid_actions=sum(r['invalid_actions'] for r in rr),length_limited=sum(r['length_limited'] for r in rr),
            **{t:sum(r[t] for r in rr) for t in TOKENS})
        row['invalid_action_rate']=row['invalid_actions']/row['total_decisions']
        for t in TOKENS: assert row[t]==ass['api_usage'][m]['solver'][t]
        row.update({f'common_{t}':sum(r[t] for r in cc) for t in TOKENS})
        aggregates.append(row)
    write_csv('alfworld_metrics.csv',aggregates)
    paired=[]
    for i in ids:
        s=ab[i,'similarity_only']['retrieval']; m=ab[i,'memrl_frozen_memory']['retrieval']
        row=dict(id=i,common_success=int(i in common),same_memory_set=int(set(s['retrieved_ids'])==set(m['retrieved_ids'])),
            same_memory_order=int(s['retrieved_ids']==m['retrieved_ids']),same_memory_context=int(s['memory_context']==m['memory_context']))
        for method in METHODS:
            row[method+'_success']=int(ab[i,method]['success']);row[method+'_decisions']=ab[i,method]['decisions']
        paired.append(row)
    write_csv('alfworld_paired.csv',paired)
    hf=[]
    for r in h:
        # Verify stored numeric equality; retain original fixed parser/score.
        assert r['correct']==(r['predicted'] is not None and r['predicted']==r['expected'])
        assert r['memory_write'] is False and r['utility_update'] is False and r['memory_unchanged_verified']
        assert r['memory_state_sha256']==hm['memory_state_sha256']
        assert sum(r['usage'][t] for t in TOKENS[:2])==r['usage']['total_tokens']
        hf.append(dict(id=r['id'],method=r['method'],correct=int(r['correct']),
            truncated=int(r['finish_reason']=='length'),unparsed=int(r['predicted'] is None),**{t:r['usage'][t] for t in TOKENS}))
    for m in ('no_memory','memrl_frozen_memory'):
        assert read(hr+m+'_results.jsonl',True)==[r for r in h if r['method']==m]
    write_csv('harp_per_task.csv',hf)
    ha=[]
    for m in ('no_memory','memrl_frozen_memory'):
        rr=[r for r in hf if r['method']==m]
        ha.append(dict(method=m,tasks=len(rr),correct=sum(r['correct'] for r in rr),success_rate=sum(r['correct'] for r in rr)/len(rr),
            truncated=sum(r['truncated'] for r in rr),unparsed=sum(r['unparsed'] for r in rr),**{t:sum(r[t] for r in rr) for t in TOKENS}))
    write_csv('harp_metrics.csv',ha)
    hp=[]; counts=collections.Counter()
    for i in hids:
        n,m=hb[i,'no_memory'],hb[i,'memrl_frozen_memory']
        outcome={(True,True):'both_correct',(False,False):'both_wrong',(False,True):'wrong_to_correct',(True,False):'correct_to_wrong'}[n['correct'],m['correct']]
        counts[outcome]+=1
        hp.append(dict(id=i,no_memory_correct=int(n['correct']),memrl_correct=int(m['correct']),outcome=outcome,
                       no_memory_finish_reason=n['finish_reason'],memrl_finish_reason=m['finish_reason']))
    write_csv('harp_paired.csv',hp)
    write_csv('harp_pair_counts.csv',[dict(outcome=k,count=v) for k,v in counts.items()])
    # Check source data SHA and membership rather than trusting aggregate claims.
    ad='research_records/data/alfworld/unseen_challenge50_v1/eval50.jsonl'
    hd='research_records/data/harp/level6_confirm50_v3/evaluation_level6_50_seed2026101901.jsonl'
    assert sha(source/ad)==am['dataset_sha256'];assert sha(source/hd)==hm['dataset_sha256']
    assert {r['id'] for r in read(ad,True)}==set(ids)
    assert {r['id'] for r in read(hd,True)}==set(hids)
    overlaps={}
    for split in ('train100','eval50','dev3'):
        rr=read('research_records/data/alfworld/minimal_train100_eval50_v1/'+split+'.jsonl',True)
        overlaps[split]=len(set(ids)&{r['id'] for r in rr});assert overlaps[split]==0
    ht=read('research_records/data/harp/level6_memrl_train50_v1/train_level6_50_seed20261019.jsonl',True)
    assert not set(hids)&{r['id'] for r in ht}
    # Replay Q updates from committed training rows and compare final exported states.
    qrows=[]; training={}
    for name,root,memfile,scorekey,initial in [
        ('alfworld','research_records/results/alfworld/memrl_train100_eval50_v1/','alfworld_train100','success',0),
        ('harp','research_records/results/harp_aime/memrl_compact_train50_v3/','harp_compact_train50_v3','correct',None)]:
        rr=read(root+'train_results.jsonl',True); bank=read('research_records/memory_export/'+memfile+'_memories.jsonl',True)
        q={};vis=collections.Counter(); updates=0
        for r in rr:
            if name=='alfworld':assert r['success']==r['final_state']['won']
            mids=r.get('retrieved_ids',r.get('retrieval',{}).get('retrieved_ids',[]))
            assert set(mids)==set(r['q_updates'])
            for mid in mids:
                new=.7*q[mid]+.3*(1 if r[scorekey] else -1)
                assert math.isclose(new,r['q_updates'][mid],abs_tol=1e-10)
                q[mid]=new;vis[mid]+=1;updates+=1
            q[r['new_memory_id']]=float(r[scorekey]) if initial is None else initial
        for r in bank:
            assert math.isclose(q[r['memory_id']],r['q_value'],abs_tol=1e-10)
            assert vis[r['memory_id']]==r['q_visits']
            qrows.append(dict(benchmark=name,memory_id=r['memory_id'],q_value=r['q_value'],q_visits=r['q_visits']))
        training[name]=dict(tasks=len(rr),successes=sum(r[scorekey] for r in rr),memories=len(bank),q_updates=updates,
            zero_visits=sum(r['q_visits']==0 for r in bank),q_median=statistics.median(r['q_value'] for r in bank))
    write_csv('memory_q.csv',qrows)
    # Export numerical retrieval evidence only, not problem text or memory content.
    bank={r['memory_id']:r for r in read('research_records/memory_export/alfworld_train100_memories.jsonl',True)}
    details=[]
    for r in a:
        for rank,d in enumerate(r['retrieval']['retrieval_details'],1):
            assert math.isclose(d['q_estimate'],bank[d['memory_id']]['q_value'],abs_tol=1e-10)
            details.append(dict(id=r['id'],method=r['method'],rank=rank,**d))
    write_csv('alfworld_retrieval.csv',details)
    state=read('research_records/memory_export/alfworld_train100_state.json')
    trainplan=read('research_records/results/alfworld/memrl_train100_eval50_v1/experiment_manifest.json')
    norm=trainplan['preflight']['memory']
    residuals=[]; rank_checks=0
    for r in a:
        if r['method']=='no_memory':continue
        ret=r['retrieval']; candidates=[]
        for query,sim in ret['retrieved_queries']:
            for mid in state['index'][query]:candidates.append((mid,sim,bank[mid]['q_value']))
        qvals=[q for _,_,q in candidates];mean=statistics.mean(qvals);std=statistics.pstdev(qvals)
        scores={}
        for mid,sim,q in candidates:
            zsim=(sim-norm['sim_norm_mean'])/norm['sim_norm_std']
            zq=(q-mean)/(std+1e-8)
            scores[mid]=zsim if r['method']=='similarity_only' else .5*zsim+.5*zq
        # Tolerance accommodates implementation epsilon in normalization.
        for d in ret['retrieval_details']:
            residuals.append(abs(scores[d['memory_id']]-d['score']))
        selected=ret['retrieved_ids']
        assert len(selected)==3
        assert all(scores[x]+1e-6>=scores[y] for x,y in zip(selected,selected[1:]))
        assert min(scores[x] for x in selected)+1e-6>=max([v for k,v in scores.items() if k not in selected],default=-math.inf)
        rank_checks+=1
    assert max(residuals)<1e-6
    mechanism=[]
    for category in ('different_set','order_only','same_context'):
        pp=[r for r in paired if ('same_context' if r['same_memory_context'] else ('order_only' if r['same_memory_set'] else 'different_set'))==category]
        diffs=[r['similarity_only_decisions']-r['memrl_frozen_memory_decisions'] for r in pp]
        mechanism.append(dict(category=category,tasks=len(pp),memrl_faster=sum(x>0 for x in diffs),tie=sum(x==0 for x in diffs),
            memrl_slower=sum(x<0 for x in diffs),decisions_saved=sum(diffs)))
    write_csv('retrieval_outcomes.csv',mechanism)
    cost=[]
    for m,services in ass['api_usage'].items():
        for service,v in services.items():cost.append(dict(benchmark='alfworld',stage='evaluation',method=m,service=service,provenance='summary_crosschecked_solver_steps' if service=='solver' else 'summary_only',**{k:v[k] for k in ('requests_started',)+TOKENS}))
    ats=read('research_records/results/alfworld/memrl_train100_eval50_v1/train_summary.json')
    for service,v in ats['api_usage'].items():cost.append(dict(benchmark='alfworld',stage='training',method='shared_bank',service=service,provenance='summary_only',**{k:v[k] for k in ('requests_started',)+TOKENS}))
    hts=read('research_records/results/harp_aime/memrl_compact_train50_v3/train_summary.json')
    htrain=read('research_records/results/harp_aime/memrl_compact_train50_v3/train_results.jsonl',True)
    for t in TOKENS:assert sum(r['usage'][t] for r in htrain)==hts['solver_tokens'][t]
    cost.append(dict(benchmark='harp',stage='training',method='memrl',service='solver',provenance='per_training_answer',requests_started=50,**hts['solver_tokens']))
    for row in ha:cost.append(dict(benchmark='harp',stage='evaluation',method=row['method'],service='solver',provenance='per_answer',requests_started=50,**{t:row[t] for t in TOKENS}))
    write_csv('token_ledger.csv',cost)
    gsm=read('research_records/results/gsm8k/no_memory_pilot200_v1/results.jsonl',True)
    summary=dict(verified_source_files=verified,alfworld=aggregates,harp=ha,harp_pairs=dict(counts),training=training,
        gsm8k=dict(completed=len(gsm),correct=sum(r['correct'] for r in gsm),status='exploration_closed'),
        retrieval=dict(set_changed=sum(not r['same_memory_set'] for r in paired),order_changed=sum(not r['same_memory_order'] for r in paired),
                       context_changed=sum(not r['same_memory_context'] for r in paired),ranking_checks=rank_checks,
                       max_score_reconstruction_error=max(residuals)),alfworld_split_id_overlaps=overlaps)
    # Compare all shared aggregate columns with the supplied analysis CSVs.
    for name,computed in [('alfworld_method_metrics.csv',aggregates),('harp_final_method_metrics.csv',ha)]:
        with (source/'analysis'/name).open(encoding='utf-8',newline='') as f:
            for old in csv.DictReader(f):
                new=next(r for r in computed if r['method']==old['method'])
                for k,v in old.items():
                    if k in new and k!='method':assert math.isclose(float(v),new[k],abs_tol=1e-9),(name,k)
    (out/'audit_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    write_csv('source_hashes.csv',[dict(relative_path=k,sha256=v) for k,v in sorted(used.items())])
    print(json.dumps(summary,indent=2,ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,default=Path('data'))
    args=p.parse_args();run(args.source,args.out)
