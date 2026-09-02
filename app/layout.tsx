import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Rolvora — Career Match Workspace",
  description: "Rolvora analiza tu CV, encuentra oportunidades y explica por qué cada vacante calza contigo.",
  applicationName: "Rolvora",
  icons: {
    icon: "/icon.svg",
    shortcut: "/icon.svg",
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
