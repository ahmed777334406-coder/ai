import "./globals.css";
import { I18nProvider } from "@/lib/i18n";
import AppShell from "@/components/AppShell";
export const metadata = { title: "Beihang SmartFind", description: "AI-powered bilingual campus lost and found platform" };
export default function RootLayout({children}:{children:React.ReactNode}) { return <html lang="en"><body><I18nProvider><AppShell>{children}</AppShell></I18nProvider></body></html>; }
