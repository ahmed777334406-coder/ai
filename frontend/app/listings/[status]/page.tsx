"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Search } from "lucide-react";
import { api } from "@/lib/api";
import { PageHeading, EmptyState } from "@/components/Ui";
import ItemCard from "@/components/ItemCard";
import { useI18n } from "@/lib/i18n";
export default function ListingsPage(){const {t}=useI18n();const params=useParams<{status:string}>();const status=(params.status||"LOST").toUpperCase();const [items,setItems]=useState<any[]>([]);const [q,setQ]=useState("");const [loading,setLoading]=useState(true);const [error,setError]=useState("");
const load=useCallback(async (query: string)=>{setLoading(true);setError("");try{const data=await api<any>(`/listings?status=${status}&q=${encodeURIComponent(query)}&limit=50`);setItems(data.items||[]);}catch(e){setError(e instanceof Error?e.message:"Could not load listings");}finally{setLoading(false);}},[status]);
useEffect(()=>{void load("");},[load]);
return <div className="page-stack"><PageHeading eyebrow="CAMPUS LISTINGS" title={status==="LOST"?t("lostListingsTitle"):t("foundListingsTitle")} description={status==="LOST"?t("lostListingsDesc"):t("foundListingsDesc")} action={<Link className="primary-button" href={`/report/${status}`}>+ {status==="LOST"?t("reportLostShort"):t("reportFoundShort")}</Link>}/><form className="search-bar" onSubmit={e=>{e.preventDefault();void load(q);}}><Search size={18}/><input value={q} onChange={e=>setQ(e.target.value)} placeholder={t("searchPlaceholder")}/><button className="primary-button small">{t("search")}</button></form>{error&&<div className="alert error">{error}</div>}{loading?<div className="loading-line">{t("loading")}</div>:items.length?<div className="item-grid">{items.map(item=><ItemCard key={item.id} item={item}/>)}</div>:<EmptyState title={t("noResults")} description={t("noReportsDesc")}/>}</div>}
