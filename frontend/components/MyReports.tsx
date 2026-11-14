"use client";
import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
export default function MyReports({items,onChange}:{items:any[];onChange:(items:any[])=>void}) {
  const {t}=useI18n();
  const [editing,setEditing]=useState<number|null>(null);
  const [title,setTitle]=useState("");const [description,setDescription]=useState("");
  const [busy,setBusy]=useState(false);const [error,setError]=useState("");
  async function update(id:number,close=false) {
    setBusy(true);setError("");
    try {await api(`/listings/${id}`,close?{method:"DELETE"}:{method:"PATCH",body:JSON.stringify({title,description})});onChange(await api<any[]>("/listings/mine"));setEditing(null);}
    catch(e){setError(e instanceof Error?e.message:t("unavailable"));}finally{setBusy(false);}
  }
  return <section className="panel form-stack"><h2>{t("myReports")}</h2>{error&&<p role="alert" className="alert error">{error}</p>}{items.map(item=><div className="form-stack" key={item.id}><Link href={`/item/${item.id}`}>{item.title} · {item.state}</Link>{editing===item.id?<form className="form-stack" onSubmit={e=>{e.preventDefault();update(item.id);}}><label>{t("title")}<input required minLength={2} maxLength={180} value={title} onChange={e=>setTitle(e.target.value)}/></label><label>{t("description")}<textarea required minLength={5} maxLength={5000} value={description} onChange={e=>setDescription(e.target.value)}/></label><div className="form-actions"><button className="primary-button" disabled={busy}>{t("saveChanges")}</button><button className="secondary-button" type="button" onClick={()=>setEditing(null)}>{t("cancel")}</button></div></form>:<div className="form-actions"><button className="secondary-button" disabled={busy||item.state!=="OPEN"} onClick={()=>{setEditing(item.id);setTitle(item.title);setDescription(item.description);}}>{t("editReport")}</button><button className="secondary-button" disabled={busy||!["OPEN","CLAIM_PENDING"].includes(item.state)} onClick={()=>update(item.id,true)}>{t("closeReport")}</button></div>}</div>)}</section>;
}
