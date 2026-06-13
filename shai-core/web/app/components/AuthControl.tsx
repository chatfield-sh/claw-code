"use client";

import { SignedIn, SignedOut, SignInButton, UserButton } from "@clerk/nextjs";

// Rendered only when Clerk is enabled (see Shell), so the provider is present.
export default function AuthControl() {
  return (
    <div style={{ marginTop: 24 }}>
      <SignedOut>
        <SignInButton mode="modal" />
      </SignedOut>
      <SignedIn>
        <UserButton />
      </SignedIn>
    </div>
  );
}
