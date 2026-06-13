import type { ReactNode } from "react";
import { ClerkProvider } from "@clerk/nextjs";

export const metadata = {
  title: "SHAI Core",
  description: "The domain-neutral executive operating system.",
};

// Clerk is optional: only wrap with ClerkProvider when a publishable key is set,
// so the app (and the keyless CI build) runs without auth configured.
const clerkEnabled = !!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

export default function RootLayout({ children }: { children: ReactNode }) {
  const tree = (
    <html lang="en">
      <body style={{ margin: 0 }}>{children}</body>
    </html>
  );
  return clerkEnabled ? <ClerkProvider>{tree}</ClerkProvider> : tree;
}
