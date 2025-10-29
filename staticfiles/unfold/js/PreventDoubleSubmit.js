document.addEventListener("DOMContentLoaded", function () {
  const form = document.querySelector("#content-main form");
  const submitRow = document.querySelector("#submit-row");
  const savingRow = submitRow.querySelector("#submit-row > div > div");
  const saveButtons = submitRow.querySelectorAll('button[type="submit"]');

  let isSubmitting = false;

  if (form) {
    form.addEventListener("submit", function (e) {
      if (isSubmitting) {
        console.log("Form already submitting - preventing double submit");
        e.preventDefault();
        return false;
      }

      isSubmitting = true;

      saveButtons.forEach((btn) => {
        btn.style.display = "none";
      });
      const savingDiv = document.createElement("div");
      savingDiv.id = "saving-message";
      savingDiv.textContent = "Saving...";
      savingRow.insertBefore(savingDiv, savingRow.firstChild);
    });
  }
});
