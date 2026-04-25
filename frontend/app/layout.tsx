import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lumos Frontend",
  description: "Lesson Viewer and Live Brain Panel"
};

export default function RootLayout({
  children
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
