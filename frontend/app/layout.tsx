import "@/styles/globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Cleveland Investor Finder",
  description: "Find off-market and listed properties for cash buyers in Cleveland."
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="page-shell">
          <header className="site-header">
            <div className="brand">
              <span className="brand__dot" />
              <div>
                <p className="brand__name">Cleveland Investor Finder</p>
                <p className="brand__tag">Off-market outreach + cash buyer workflow</p>
              </div>
            </div>
            <nav className="site-nav">
              <a href="#workflow">Workflow</a>
              <a href="#signals">Signals</a>
              <a href="#contact">Contact</a>
            </nav>
          </header>
          {children}
          <footer className="site-footer">
            <p>Built for Cleveland investors sourcing distressed property opportunities.</p>
          </footer>
        </div>
      </body>
    </html>
  );
}
