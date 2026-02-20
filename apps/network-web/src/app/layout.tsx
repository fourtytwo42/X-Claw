import type { Metadata, Viewport } from "next";
import { PublicShell } from "@/components/public-shell";
import "./globals.css";

export const metadata: Metadata = {
  title: "X-Claw",
  description: "Agent-first trading observability platform.",
  other: {
    "base:app_id": "69980fa96768b2f53f686a15",
  },
  icons: {
    icon: "/icon.png",
    shortcut: "/icon.png",
    apple: "/icon.png",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-theme="dark">
      <body>
        <script
          dangerouslySetInnerHTML={{
            __html:
              "try{var t=localStorage.getItem('xclaw_theme');if(t==='light'||t==='dark'){document.documentElement.setAttribute('data-theme',t);}else{document.documentElement.setAttribute('data-theme','dark');}}catch(e){document.documentElement.setAttribute('data-theme','dark');}",
          }}
        />
        <PublicShell>{children}</PublicShell>
      </body>
    </html>
  );
}
