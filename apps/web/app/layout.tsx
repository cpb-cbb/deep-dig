import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Deep Dig — 把任何资料，变成可用的数据",
  description: "面向日常通用任务与科研文献的桌面端 AI 数据抽取工具。PDF 本地解析，批量抽取并导出结构化数据。",
  openGraph: {
    title: "Deep Dig — 把任何资料，变成可用的数据",
    description: "日常资料与科研文献的桌面端 AI 数据抽取工具。",
    type: "website",
    images: [{ url: "/og.png", width: 1536, height: 1024, alt: "Deep Dig 数据抽取工具" }],
  },
  twitter: { card: "summary_large_image", images: ["/og.png"] },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body className={`${geistSans.variable} ${geistMono.variable}`}>{children}</body></html>;
}
