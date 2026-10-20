import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Modal } from "./Modal";
afterEach(cleanup);
it("blocks Escape and close while a save is pending, then permits dismissal", () => {
  const close = vi.fn();
  const { rerender } = render(
    <Modal busy onClose={close}>
      Saving
    </Modal>,
  );
  fireEvent(
    screen.getByRole("dialog"),
    new Event("cancel", { bubbles: true, cancelable: true }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Close monitor editor" }));
  expect(close).not.toHaveBeenCalled();
  rerender(<Modal onClose={close}>Saved</Modal>);
  fireEvent(
    screen.getByRole("dialog"),
    new Event("cancel", { bubbles: true, cancelable: true }),
  );
  expect(close).toHaveBeenCalledTimes(1);
});
