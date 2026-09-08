import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("renders the Trazio login experience", () => {
    render(<App />);

    expect(
      screen.getByText("Trazio"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: "Plan your next experience.",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("textbox", {
        name: "Email or username",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Sign in",
      }),
    ).toBeInTheDocument();
  });
});