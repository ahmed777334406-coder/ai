"use client";
import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeading, StatusPill } from "@/components/Ui";
import { useI18n } from "@/lib/i18n";
type Profile = {email: string; full_name: string; role: string; preferred_language: "en" | "zh"};
export default function ProfilePage() {
  const {t, lang, setLang} = useI18n();
  const [user, setUser] = useState<Profile | null>(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {api<Profile>("/auth/me").then(setUser).catch(e => setError(e.message));}, []);
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setSaved(false);
    try {
      const updated = await api<Profile>("/auth/me", {method:"PATCH", body:JSON.stringify({full_name:user?.full_name, preferred_language:user?.preferred_language})});
      setUser(updated); setLang(updated.preferred_language); setSaved(true);
      localStorage.setItem("smartfind_user", JSON.stringify(updated));
    } catch (e) {setError(e instanceof Error ? e.message : "Could not save profile");}
    finally {setBusy(false);}
  }
  return <div className="page-stack narrow"><PageHeading eyebrow="ACCOUNT" title={t("profileTitle")} description={t("profileDesc")}/>
    {error && <div className="alert error" role="alert">{error}</div>}
    {user ? <form onSubmit={save} className="panel form-stack">
      <label>{lang === "zh" ? "姓名" : "Full name"}<input required minLength={2} maxLength={160} value={user.full_name} onChange={e=>setUser({...user, full_name:e.target.value})}/></label>
      <div className="status-row"><span>Email</span><b>{user.email}</b></div>
      <div className="status-row"><span>{lang === "zh" ? "账户角色" : "Account role"}</span><StatusPill value={user.role}/></div>
      <label>{t("preferredLanguage")}<select value={user.preferred_language} onChange={e=>setUser({...user, preferred_language:e.target.value as "en" | "zh"})}><option value="en">English</option><option value="zh">简体中文</option></select></label>
      <button className="primary-button" disabled={busy}>{busy ? (lang === "zh" ? "保存中…" : "Saving…") : (lang === "zh" ? "保存更改" : "Save changes")}</button>
      {saved && <p className="alert success" role="status">{lang === "zh" ? "个人信息已保存" : "Profile saved"}</p>}
    </form> : !error && <div className="loading-line">{t("loading")}</div>}
  </div>;
}
