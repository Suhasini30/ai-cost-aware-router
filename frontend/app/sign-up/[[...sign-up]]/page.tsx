import Link from "next/link";
import { SignUp } from "@clerk/nextjs";
import { ErrorBoundary } from "@/components/ErrorBoundary";

function SignUpFallback() {
  return (
    <div className="text-center">
      <p className="text-[13px] text-ink-muted m-0 mb-3">
        Authentication is temporarily unavailable. Please check your
        connection and try again.
      </p>
      <Link href="/" className="text-xs text-gold">
        Go home
      </Link>
    </div>
  );
}

export default function SignUpPage() {
  return (
    <div className="flex justify-center pt-10">
      <ErrorBoundary fallback={<SignUpFallback />}>
        <SignUp forceRedirectUrl="/console" />
      </ErrorBoundary>
    </div>
  );
}
