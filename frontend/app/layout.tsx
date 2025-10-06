import type { Metadata } from "next";
import Providers from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "YouTube Comment Analyzer",
  description: "Analyze YouTube comments with AI-powered sentiment analysis",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body className="font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

