import { fireEvent, render, screen } from "@testing-library/react";

import {
  PageError,
  PageErrorSoftHover,
} from "@/components/ui/page-error";

describe("PageError", () => {
  beforeEach(() => {
    jest.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("renders the error message and digest", () => {
    const error = Object.assign(new Error("Request failed"), {
      digest: "digest-123",
    });

    render(<PageError error={error} reset={jest.fn()} />);

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Request failed")).toBeInTheDocument();
    expect(screen.getByText("Error ID: digest-123")).toBeInTheDocument();
    expect(console.error).toHaveBeenCalledWith("Page error:", error);
  });

  it("uses the fallback message when the error message is empty", () => {
    render(<PageError error={new Error("")} reset={jest.fn()} />);

    expect(
      screen.getByText("An unexpected error occurred."),
    ).toBeInTheDocument();
  });

  it("calls reset when Try again is clicked", () => {
    const reset = jest.fn();

    render(<PageError error={new Error("Failed")} reset={reset} />);

    fireEvent.click(
      screen.getByRole("button", { name: "Try again" }),
    );

    expect(reset).toHaveBeenCalledTimes(1);
  });

  it("preserves the standard button style", () => {
    render(<PageError error={new Error("Failed")} reset={jest.fn()} />);

    const button = screen.getByRole("button", { name: "Try again" });

    expect(button).toHaveClass("transition-colors");
    expect(button).toHaveClass("hover:bg-primary/90");
  });

  it("preserves the soft-hover button style", () => {
    render(
      <PageErrorSoftHover
        error={new Error("Failed")}
        reset={jest.fn()}
      />,
    );

    const button = screen.getByRole("button", { name: "Try again" });

    expect(button).toHaveClass("hover:bg-primary/80");
    expect(button).not.toHaveClass("transition-colors");
  });
});
