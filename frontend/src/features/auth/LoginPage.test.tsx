import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import * as authApi from "@/api/auth";
import { AppError } from "@/api/client";
import { AppProviders } from "@/app/providers";
import { AuthProvider } from "./AuthContext";
import { LoginPage } from "./LoginPage";

function renderLogin() {
  return render(
    <AppProviders>
      <AuthProvider>
        <MemoryRouter initialEntries={["/login"]}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/officer/queue" element={<div>Officer home</div>} />
            <Route path="/app/dashboard" element={<div>Operator home</div>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </AppProviders>,
  );
}

describe("LoginPage", () => {
  beforeEach(() => sessionStorage.clear());

  it("validates inline before calling the API", async () => {
    const spy = vi.spyOn(authApi, "login");
    renderLogin();
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findAllByRole("alert")).toHaveLength(2);
    expect(spy).not.toHaveBeenCalled();
  });

  it("routes an officer to the review queue after sign-in", async () => {
    vi.spyOn(authApi, "login").mockResolvedValue({
      access_token: "t",
      token_type: "bearer",
      expires_at: new Date(Date.now() + 60_000).toISOString(),
      user: {
        id: "1",
        email: "o@x.sg",
        full_name: "Rahim bin Abdullah",
        role: "officer",
      },
    });
    renderLogin();
    await userEvent.type(screen.getByLabelText(/Email address/), "o@x.sg");
    await userEvent.type(screen.getByLabelText(/Password/), "pw");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() =>
      expect(screen.getByText("Officer home")).toBeInTheDocument(),
    );
  });

  it("shows the generic message on 401", async () => {
    vi.spyOn(authApi, "login").mockRejectedValue(
      new AppError(401, {
        code: "unauthorized",
        message: "Email or password is incorrect.",
      }),
    );
    renderLogin();
    await userEvent.type(screen.getByLabelText(/Email address/), "o@x.sg");
    await userEvent.type(screen.getByLabelText(/Password/), "pw");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(
      await screen.findByText("Email or password is incorrect."),
    ).toBeInTheDocument();
  });
});
