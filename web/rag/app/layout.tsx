import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "./_components/Sidebar";
import { AuthProvider } from "./_contexts/AuthContext";
import { AuthGate } from "./_components/AuthGate";

export const metadata: Metadata = {
  title: "RAG 知识库",
  description: "上传文档并管理知识库",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="flex h-full overflow-hidden">
        <AuthProvider>
          <AuthGate>
            <Sidebar />
            <main className="flex flex-1 flex-col overflow-y-auto">{children}</main>
          </AuthGate>
        </AuthProvider>
      </body>
    </html>
  );
}
