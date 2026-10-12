
document.addEventListener("DOMContentLoaded", function () {
    const scanForm = document.getElementById("scan-form");
    const scanButton = document.getElementById("scan-button");
    const scanButtonText = document.getElementById("scan-button-text");
    const scanLoading = document.getElementById("scan-loading");
    const urlInput = document.getElementById("url");

    if (scanForm) {
        scanForm.addEventListener("submit", function (event) {
            const url = urlInput.value.trim();

            if (!url) {
                event.preventDefault();
                urlInput.focus();
                return;
            }

            try {
                const parsedUrl = new URL(url);

                if (
                    parsedUrl.protocol !== "http:" &&
                    parsedUrl.protocol !== "https:"
                ) {
                    event.preventDefault();
                    alert("Please enter a valid HTTP or HTTPS website URL.");
                    urlInput.focus();
                    return;
                }
            } catch {
                event.preventDefault();
                alert("Please enter a valid website URL.");
                urlInput.focus();
                return;
            }

            if (scanButton) {
                scanButton.disabled = true;
            }

            if (scanButtonText) {
                scanButtonText.textContent = "Scanning Website...";
            }

            if (scanLoading) {
                scanLoading.hidden = false;
            }
        });
    }

    document.querySelectorAll(".flash-close").forEach(function (button) {
        button.addEventListener("click", function () {
            const message = button.closest(".flash-message");

            if (message) {
                message.remove();
            }
        });
    });

    const scoreCircle = document.querySelector(".score-circle");
    const scoreNumber = document.querySelector(".score-number");

    if (scoreCircle && scoreNumber) {
        const score = Number.parseInt(scoreNumber.textContent, 10);

        if (Number.isFinite(score)) {
            const safeScore = Math.max(0, Math.min(100, score));
            scoreCircle.style.setProperty("--score-percent", safeScore);
        }
    }
});
