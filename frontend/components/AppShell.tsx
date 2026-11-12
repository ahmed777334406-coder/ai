"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bell, Bookmark, Boxes, ClipboardList, FilePlus2, Flag, LayoutDashboard, LogOut, Search, Settings, ShieldCheck, Languages, UserRound, BarChart3, MapPin } from "lucide-react";
import { api, clearSession, getToken } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { useEffect, useState } from "react";

const links = [
  {href:"/dashboard",key:"dashboard",icon:LayoutDashboard,auth:true},
  {href:"/listings/LOST",key:"lost",icon:Search,auth:false},
  {href:"/listings/FOUND",key:"found",icon:Bookmark,auth:false},
  {href:"/report/LOST",key:"reportLost",icon:FilePlus2,auth:true},
  {href:"/report/FOUND",key:"reportFound",icon:Flag,auth:true},
  {href:"/matches",key:"matches",icon:Boxes,auth:true},
  {href:"/claims",key:"claims",icon:ClipboardList,auth:true},
  {href:"/notifications",key:"notifications",icon:Bell,auth:true},
];
export default function AppShell({children}:{children:React.ReactNode}) {
  const path=usePathname();
  const router=useRouter();
  const {lang,setLang,t}=useI18n();
  const [signedIn,setSignedIn]=useState(false);
  const [role,setRole]=useState("STUDENT");

  useEffect(()=>{
    const token=!!getToken();
    let currentRole="STUDENT";
    const raw=localStorage.getItem("smartfind_user");
    if(raw){try{currentRole=JSON.parse(raw).role||"STUDENT";}catch{currentRole="STUDENT";}}
    setSignedIn(token);
    setRole(currentRole);
  },[path,router]);

  const logout=async()=>{
    try { await api("/auth/logout", {method:"POST"}); } catch { /* Local sign-out still works offline. */ }
    clearSession();
    setSignedIn(false);
    setRole("STUDENT");
    router.replace("/");
  };

  return <div className="min-h-screen bg-[#f5f7fb] text-slate-900">
    <header className="topbar">
      <Link href="/" className="brand"><span className="brand-mark">SF</span><span>Beihang <b>SmartFind</b><small>北航校园智能失物招领系统</small></span></Link>
      <div className="top-actions">
        <button className="lang-button" onClick={()=>setLang(lang==="en"?"zh":"en")}><Languages size={16}/>{lang==="en"?"中文":"English"}</button>
        {signedIn?<button className="ghost-button" onClick={logout}><LogOut size={16}/>{t("signOut")}</button>:<span className="muted">{lang==="en"?"Anonymous visitor":"匿名访客"}</span>}
      </div>
    </header>
    <div className="app-layout">
      <aside className="sidebar">
        <div className="side-label">{signedIn?"WORKSPACE":"EXPLORE"}</div>
        {links.map(item=>{const Icon=item.icon;return <Link key={item.href} href={item.href} className={`nav-link ${path===item.href?"active":""}`}><Icon size={17}/>{t(item.key)}</Link>;})}
        {signedIn&&<Link href="/profile" className={`nav-link ${path==="/profile"?"active":""}`}><UserRound size={17}/>{t("profileTitle")}</Link>}
        {signedIn&&role==="ADMIN"&&<><div className="side-label spaced">ADMINISTRATION</div><Link href="/admin" className={`nav-link ${path==="/admin"?"active":""}`}><ShieldCheck size={17}/>{t("admin")}</Link><Link href="/admin/listings" className={`nav-link ${path==="/admin/listings"?"active":""}`}><ClipboardList size={17}/>{t("listingManagement")}</Link><Link href="/admin/claims" className={`nav-link ${path==="/admin/claims"?"active":""}`}><ShieldCheck size={17}/>{t("claimReview")}</Link><Link href="/admin/analytics" className={`nav-link ${path==="/admin/analytics"?"active":""}`}><BarChart3 size={17}/>{t("analytics")}</Link><Link href="/admin/zones" className={`nav-link ${path==="/admin/zones"?"active":""}`}><MapPin size={17}/>{lang==="en"?"Campus zones":"校园区域"}</Link></>}
        <div className="side-bottom">{signedIn&&<Link href="/settings" className="nav-link"><Settings size={17}/>{t("settings")}</Link>}<div className="side-note">Independent academic project</div></div>
      </aside>
      <main className="main-content">{children}</main>
    </div>
    <footer className="footer">Beihang SmartFind · Independent student project · Not an official university service</footer>
  </div>;
}
