import type { Metadata } from "next";
import { Providers } from "../components/Providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "JARVIS.AGI",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-page text-fg antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

