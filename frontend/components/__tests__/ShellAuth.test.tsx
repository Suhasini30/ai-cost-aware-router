import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  useAuth: vi.fn(),
  failOn: { userButton: false, signIn: false, signUp: false },
}));

vi.mock("@clerk/nextjs", () => ({
  useAuth: mocks.useAuth,
  UserButton: () => {
    if (mocks.failOn.userButton) throw new Error("clerk down");
    return <div data-testid="user-button" />;
  },
  SignInButton: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  SignIn: () => {
    if (mocks.failOn.signIn) throw new Error("clerk down");
    return <div data-testid="clerk-signin" />;
  },
  SignUp: () => {
    if (mocks.failOn.signUp) throw new Error("clerk down");
    return <div data-testid="clerk-signup" />;
  },
}));

vi.mock("next/navigation", () => ({ usePathname: () => "/console" }));

import { Shell } from "../Shell";
import SignInPage from "@/app/sign-in/[[...sign-in]]/page";
import SignUpPage from "@/app/sign-up/[[...sign-up]]/page";

afterEach(() => {
  cleanup();
  mocks.failOn.userButton = false;
  mocks.failOn.signIn = false;
  mocks.failOn.signUp = false;
});

describe("Shell auth footer", () => {
  it("shows a loading skeleton while Clerk loads, no auth buttons", () => {
    mocks.useAuth.mockReturnValue({ isLoaded: false, isSignedIn: false });
    render(
      <Shell>
        <div />
      </Shell>
    );
    expect(screen.getByLabelText("Authentication loading")).toBeTruthy();
    expect(screen.queryByText("Sign in")).toBeNull();
    expect(screen.queryByTestId("user-button")).toBeNull();
  });

  it("shows Sign in and Sign up when signed out", () => {
    mocks.useAuth.mockReturnValue({ isLoaded: true, isSignedIn: false });
    render(
      <Shell>
        <div />
      </Shell>
    );
    expect(screen.getByText("Sign in")).toBeTruthy();
    expect(screen.getByText("Sign up")).toBeTruthy();
  });

  it("shows static fallback without Clerk when auth rendering throws", () => {
    mocks.useAuth.mockReturnValue({ isLoaded: true, isSignedIn: true });
    mocks.failOn.userButton = true;
    render(
      <Shell>
        <div />
      </Shell>
    );
    expect(
      screen.getByText("Authentication is temporarily unavailable.")
    ).toBeTruthy();
    expect(screen.getByText("Sign In")).toBeTruthy();
    expect(screen.getByText("Sign Up")).toBeTruthy();
    expect(screen.queryByTestId("user-button")).toBeNull();
  });

  it("keeps signed-in avatar behavior intact", () => {
    mocks.useAuth.mockReturnValue({ isLoaded: true, isSignedIn: true });
    render(
      <Shell>
        <div />
      </Shell>
    );
    expect(screen.getByTestId("user-button")).toBeTruthy();
    expect(screen.getByText("Signed in")).toBeTruthy();
  });
});

describe("Auth pages", () => {
  it("renders Clerk SignIn normally", () => {
    render(<SignInPage />);
    expect(screen.getByTestId("clerk-signin")).toBeTruthy();
  });

  it("shows fallback with home link when SignIn fails", () => {
    mocks.failOn.signIn = true;
    render(<SignInPage />);
    expect(
      screen.getByText(/Authentication is temporarily unavailable/)
    ).toBeTruthy();
    expect(screen.getByText("Go home")).toBeTruthy();
    expect(screen.queryByTestId("clerk-signin")).toBeNull();
  });

  it("renders Clerk SignUp normally", () => {
    render(<SignUpPage />);
    expect(screen.getByTestId("clerk-signup")).toBeTruthy();
  });

  it("shows fallback with home link when SignUp fails", () => {
    mocks.failOn.signUp = true;
    render(<SignUpPage />);
    expect(
      screen.getByText(/Authentication is temporarily unavailable/)
    ).toBeTruthy();
    expect(screen.getByText("Go home")).toBeTruthy();
    expect(screen.queryByTestId("clerk-signup")).toBeNull();
  });
});
