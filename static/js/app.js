document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll('form[method="post"]').forEach((form) => {
    form.addEventListener("submit", () => {
      const button = form.querySelector('button[type="submit"]');
      if (!button) {
        return;
      }

      button.disabled = true;
      button.dataset.originalLabel = button.textContent;
      button.textContent = "Working...";

      window.setTimeout(() => {
        button.disabled = false;
        if (button.dataset.originalLabel) {
          button.textContent = button.dataset.originalLabel;
        }
      }, 10000);
    });
  });
});
