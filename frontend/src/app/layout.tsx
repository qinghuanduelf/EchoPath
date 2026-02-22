import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "EchoPath — Find Your Career Path",
  description:
    "Career navigation & mentorship platform for underserved students. Discover paths walked by people who started where you are.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} antialiased`}>
        {/* ── Navigation ── */}
        <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-[var(--color-border)]">
          <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2 group">
              <span className="text-2xl">🚀</span>
              <span className="text-xl font-bold gradient-text group-hover:opacity-80 transition-opacity">
                EchoPath
              </span>
            </Link>
            <p className="text-sm text-[var(--color-muted)] hidden sm:block">
              Every path was once walked by someone before you.
            </p>
          </div>
        </nav>

        {/* ── Main content ── */}
        <main className="pt-16 min-h-screen">{children}</main>

        {/* ── Footer ── */}
        <footer className="border-t border-[var(--color-border)] py-8 text-center text-sm text-[var(--color-muted)]">
          <p>
            Built with ❤️ for students from underserved communities &middot;
            EchoPath &copy; {new Date().getFullYear()}
          </p>
        </footer>
      </body>
    </html>
  );
}
