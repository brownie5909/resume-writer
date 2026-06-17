console.log("Hire Ready pricing.js loaded");

document.addEventListener("DOMContentLoaded", function () {
  const premiumButton = document.getElementById("start-premium-checkout");

  if (!premiumButton) {
    console.warn("Premium checkout button not found");
    return;
  }

  premiumButton.addEventListener("click", async function (event) {
    event.preventDefault();

    const token = localStorage.getItem("hire_ready_token");

    if (!token) {
      window.location.href = "/register/";
      return;
    }

    const originalText = premiumButton.textContent;

    premiumButton.textContent = "Opening checkout...";
    premiumButton.style.pointerEvents = "none";

    try {
      const response = await fetch(
        "https://resume-writer.onrender.com/api/subscriptions/create-checkout?tier=premium",
        {
          method: "POST",
          headers: {
            Authorization: "Bearer " + token,
          },
        }
      );

      const data = await response.json();

      if (!response.ok || !data.checkout_url) {
        throw new Error(data.detail || "Could not start checkout");
      }

      window.location.href = data.checkout_url;
    } catch (error) {
      console.error("Stripe checkout error:", error);
      alert("Checkout error: " + error.message);

      premiumButton.textContent = originalText;
      premiumButton.style.pointerEvents = "auto";
    }
  });
});
