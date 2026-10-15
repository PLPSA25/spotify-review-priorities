import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Spotify review priorities",
  description:
    "Partial-scope review analysis with two rankings, stored evidence and the owner-approved decision memo.",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
