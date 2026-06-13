import type { ReactNode } from "react";

export const metadata = {
  title: "SHAI Core",
  description: "The domain-neutral executive operating system.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0 }}>{children}</body>
    </html>
  );
}
