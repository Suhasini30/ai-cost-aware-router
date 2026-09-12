import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="flex justify-center pt-10">
      <SignUp forceRedirectUrl="/console" />
    </div>
  );
}
