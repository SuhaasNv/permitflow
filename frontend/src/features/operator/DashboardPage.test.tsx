import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import * as api from "@/api/applications";
import { AppProviders } from "@/app/providers";
import { AuthProvider } from "@/features/auth/AuthContext";
import { OperatorDashboardPage } from "./DashboardPage";

function renderPage() {
  sessionStorage.setItem(
    "permitflow.session",
    JSON.stringify({
      token: "t",
      expiresAt: new Date(Date.now() + 60_000).toISOString(),
      user: {
        id: "1",
        email: "a@b.sg",
        full_name: "Tan Wei Ling",
        role: "operator",
      },
    }),
  );
  return render(
    <AppProviders>
      <AuthProvider>
        <MemoryRouter>
          <OperatorDashboardPage />
        </MemoryRouter>
      </AuthProvider>
    </AppProviders>,
  );
}

describe("OperatorDashboardPage", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("shows the empty state when there are no applications", async () => {
    vi.spyOn(api, "listApplications").mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText("No applications yet")).toBeInTheDocument();
  });

  it("lists applications with the served label", async () => {
    vi.spyOn(api, "listApplications").mockResolvedValue([
      {
        id: "a1",
        reference_no: "PF-2026-001000",
        licence_title: "Food Establishment Licence",
        status_label: "Draft",
        status_tone: "neutral",
        business_name: null,
        premises_summary: null,
        percent: 0,
        revision_count: 0,
        created_at: "2026-09-18T01:00:00Z",
        updated_at: "2026-09-18T01:00:00Z",
      },
    ]);
    renderPage();
    expect(await screen.findByText("PF-2026-001000")).toBeInTheDocument();
    expect(screen.getAllByText("Draft").length).toBeGreaterThan(0);
    expect(screen.getByText("Continue")).toBeInTheDocument();
  });
});
