"use client";
import { FormEvent, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { PageHeading } from "@/components/Ui";
import ItemCard from "@/components/ItemCard";

type Result = {score:number; method:string; listing:any};
export default function SmartSearchPage() {
  const {t}=useI18n();
  const [query,setQuery]=useState("");
  const [mode,setMode]=useState("search");
  const [rows,setRows]=useState<Result[]>([]);
  const [answer,setAnswer]=useState("");
  const [method,setMethod]=useState("");
  const [busy,setBusy]=useState(false);
  const [searched,setSearched]=useState(false);
  const [error,setError]=useState("");
  async function submit(event:FormEvent) {
    event.preventDefault();setBusy(true);setError("");setAnswer("");setRows([]);setSearched(false);
    try {
      const data=await api<any>(`/ai/${mode}`,{method:"POST",body:JSON.stringify({query,limit:10})});
      setMethod(mode==="search"?data.method:`${data.retrieval_method} / ${data.answer_provider}`);
      if(mode==="search") setRows(data.results);
      else {setAnswer(data.answer);setRows(data.retrieved_records.map((record:any)=>({score:record.score,method:data.retrieval_method,listing:{...record,id:record.id,zone_name_en:record.zone}})));}
      setSearched(true);
    } catch(e) {setError(e instanceof Error?e.message:t("unavailable"));}
    finally {setBusy(false);}
  }
  return <div className="page-stack"><PageHeading eyebrow="SMARTFIND" title={t("smartSearch")} description={t("smartSearchDesc")}/>
    <form className="panel form-stack" onSubmit={submit}>
      <label>{t("searchQuery")}<textarea required minLength={2} maxLength={1000} value={query} onChange={e=>setQuery(e.target.value)} placeholder={t("searchHint")} rows={3}/></label>
      <label>{t("searchMode")}<select value={mode} onChange={e=>setMode(e.target.value)}><option value="search">{t("semanticMode")}</option><option value="assistant">{t("assistantMode")}</option></select></label>
      <div className="form-actions"><button className="primary-button" disabled={busy}>{busy?t("loading"):t("search")}</button><Link href="/listings/FOUND" className="text-link">{t("exactSearch")}</Link></div>
    </form>
    {error&&<div role="alert" className="alert error">{error}</div>}
    <div role="status" aria-live="polite">{searched&&<p>{t("method")}: {method}</p>}{searched&&!rows.length&&<p>{t("noSearchResults")}</p>}</div>
    {answer&&<section className="panel"><h2>{t("summary")}</h2><p style={{whiteSpace:"pre-wrap"}}>{answer}</p><p className="muted">{t("notProbability")}</p></section>}
    <div className="item-grid">{rows.map(row=><div key={row.listing.id}>{mode==="search"?<ItemCard item={row.listing}/>:<Link className="panel" href={`/item/${row.listing.id}`}>{row.listing.title} · {row.listing.status} · {row.listing.zone_name_en}</Link>}<p>{t("score")}: {row.score}% · {row.method}</p></div>)}</div>
  </div>;
}
