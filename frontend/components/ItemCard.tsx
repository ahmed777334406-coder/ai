"use client";
import { useI18n } from "@/lib/i18n";
import { API_ORIGIN } from "@/lib/api";
import Link from "next/link";
import { MapPin, CalendarDays, ArrowUpRight } from "lucide-react";
import { StatusPill } from "@/components/Ui";
export default function ItemCard({item}:{item:any}) {
  const {t,lang}=useI18n();
  return <article className="item-card"><div className="item-image">{item.image_urls?.[0]?<img src={`${API_ORIGIN}${item.image_urls[0]}`} alt={item.title}/>:<div className="image-placeholder">{item.category?.slice(0,1)||"?"}</div>}<StatusPill value={item.status}/></div><div className="item-body"><div className="item-category">{item.category}</div><h3>{item.title}</h3><p>{item.description}</p><div className="item-meta">{item.zone_name_en&&<span><MapPin size={13}/>{lang==="zh"?item.zone_name_zh:item.zone_name_en}</span>}{item.occurred_at&&<span><CalendarDays size={13}/>{new Date(item.occurred_at).toLocaleDateString()}</span>}</div><Link href={`/item/${item.id}`} className="item-link">{t("viewDetails")} <ArrowUpRight size={15}/></Link></div></article>;
}
