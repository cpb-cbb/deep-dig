import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Deep Dig — 材料科学论文数据抽取",
  description: "面向材料科学论文的桌面端 AI 数据抽取工具。PDF 本地解析，按需抽取样品、工艺、测试条件与性能数据。",
  openGraph: {
    title: "Deep Dig — 材料科学论文数据抽取",
    description: "从材料科学论文中批量提取样品属性、测试条件与性能数据。",
    type: "website",
    images: [{ url: "/og.png", width: 1536, height: 1024, alt: "Deep Dig 数据抽取工具" }],
  },
  twitter: { card: "summary_large_image", images: ["/og.png"] },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body className={`${geistSans.variable} ${geistMono.variable}`}>{children}</body></html>;
}
