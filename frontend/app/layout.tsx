import type { Metadata } from "next";
import "./globals.css";

import { detectHost } from "./api";

// Use the environment variables for metadata
export const metadata: Metadata = {
  title: process.env.NEXT_PUBLIC_SITE_TITLE || "Default Title",
  description: process.env.NEXT_PUBLIC_SITE_DESCRIPTION || "Default Description",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const faviconUrl = process.env.NEXT_PUBLIC_FAVICON_URL || "/static/icon.ico";

  return (
    <html lang="es">
      {/* <link rel="icon" href="icon.ico" />
      <link rel="icon" href={faviconUrl} /> */}

      <link href={faviconUrl} rel="icon" type="image/x-icon"></link>
      <body>{children}</body>
    </html>
  );
}
