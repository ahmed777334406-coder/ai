#!/usr/bin/env python3
"""Isolated, deterministic text/hybrid evaluation; no production DB or API access."""
import json, sys, time, statistics
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.models import Listing, ListingStatus, User, UserRole
from app.services.matching import score_pair
from app.config import settings
settings.enable_local_models=False
engine=create_engine('sqlite://')
Base.metadata.create_all(engine)
cases=[
 ('黑色耳机盒 白色星星贴纸','Black earbuds case white star sticker','Black earbuds case red stripe','Electronics'),
 ('蓝色钱包 银色搭扣','Blue wallet silver clasp','Blue wallet gold zipper','Wallets'),
 ('红色水杯 白色贴纸','Red water bottle white sticker','Red water bottle black sleeve','Water Bottles'),
 ('黑色背包 蓝色丝带','Black backpack blue ribbon','Black backpack red ribbon','Bags'),
]
latencies=[];ranks=[];negative_scores=[];methods=set()
with Session(engine) as db:
 for i in range(2): db.add(User(email=f'eval{i}@visitor.invalid',full_name='Synthetic',password_hash='!',role=UserRole.STUDENT))
 db.flush()
 found=[]
 for i,(query,positive,negative,category) in enumerate(cases):
  for label,title in [('positive',positive),('hard_negative',negative)]:
   item=Listing(owner_id=2,status=ListingStatus.FOUND,title=title,description=title,category=category,occurred_at=datetime(2026,1,1,tzinfo=timezone.utc))
   db.add(item);db.flush();found.append((i,label,item))
 for i,(query,_,_,category) in enumerate(cases):
  lost=Listing(owner_id=1,status=ListingStatus.LOST,title=query,description=query,category=category,occurred_at=datetime(2026,1,1,tzinfo=timezone.utc));db.add(lost);db.flush()
  ranking=[]
  for j,label,candidate in found:
   start=time.perf_counter();evidence=score_pair(db,lost,candidate);latencies.append((time.perf_counter()-start)*1000)
   ranking.append((evidence['score'],j==i and label=='positive',candidate.title))
   methods.update(evidence['methods'].values())
   if j!=i or label!='positive': negative_scores.append(evidence['score'])
  ranking.sort(key=lambda row:row[0],reverse=True)
  ranks.append(next(index+1 for index,row in enumerate(ranking) if row[1]))
report={'dataset':'4 bilingual queries; 8 found reports; four same-category attribute hard negatives plus cross-category negatives','positive_ranks':ranks,'top1':sum(r==1 for r in ranks)/len(ranks),'mrr':statistics.mean(1/r for r in ranks),'nonpositive_pairs':len(negative_scores),'false_positive_rate_at_notification_threshold_35':sum(s>=35 for s in negative_scores)/len(negative_scores),'pair_latency_ms_median':round(statistics.median(latencies),3),'pair_latency_ms_p95':round(sorted(latencies)[int(len(latencies)*.95)-1],3),'methods':sorted(methods),'limitations':['Synthetic tiny sample; no general accuracy claim.','Local rule/hash text fallback, not pretrained semantic inference.','No image signal in this experiment; historical image evaluation remains separate.','False positives show why administrator review and richer attributes remain necessary.']}
path=Path(__file__).resolve().parents[1]/'docs/verification/final-evaluation.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
