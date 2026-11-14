"use client";
import { useI18n } from "@/lib/i18n";
import { ReactNode } from "react";
export function PageHeading({eyebrow,title,description,action}:{eyebrow?:string;title:string;description?:string;action?:ReactNode}){return <div className="page-heading"><div>{eyebrow&&<div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{description&&<p>{description}</p>}</div>{action&&<div>{action}</div>}</div>}
export function StatCard({label,value,detail,icon}:{label:string;value:string|number;detail?:string;icon?:ReactNode}){return <div className="stat-card"><div className="stat-top"><span>{label}</span><span className="stat-icon">{icon}</span></div><strong>{value}</strong>{detail&&<small>{detail}</small>}</div>}
export function EmptyState({title,description}:{title:string;description?:string}){return <div className="empty-state"><div className="empty-icon">⌕</div><strong>{title}</strong>{description&&<p>{description}</p>}</div>}
export function StatusPill({value}:{value:string}){const {t}=useI18n();return <span className={`status-pill status-${value.toLowerCase().replaceAll("_","-")}`}>{t(value)===value?value.replaceAll("_"," "):t(value)}</span>}
