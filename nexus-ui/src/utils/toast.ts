/**
 * Toast notification system — replaces alert() calls
 * Usage: toast("Message"), toast.error("Error"), toast.success("Done")
 */

type ToastType = "success" | "error" | "info";

function getContainer(): HTMLElement {
  let container = document.querySelector(".toast-container") as HTMLElement;
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }
  return container;
}

function showToast(message: string, type: ToastType = "info", duration = 3000) {
  const container = getContainer();
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.textContent = message;
  container.appendChild(el);

  setTimeout(() => {
    el.classList.add("removing");
    setTimeout(() => el.remove(), 200);
  }, duration);
}

export const toast = Object.assign(
  (message: string) => showToast(message, "info"),
  {
    success: (message: string) => showToast(message, "success"),
    error: (message: string) => showToast(message, "error", 5000),
    info: (message: string) => showToast(message, "info"),
  }
);
