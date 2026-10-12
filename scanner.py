
from playwright.sync_api import sync_playwright


def scan_website(url):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        page = browser.new_page()
        page.set_default_timeout(20000)

        try:
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=45000
            )
            page.wait_for_timeout(1500)

            page.add_script_tag(
                url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.3/axe.min.js"
            )

            axe_results = page.evaluate("""
                async () => {
                    const results = await axe.run(document, {
                        runOnly: {
                            type: "tag",
                            values: [
                                "wcag2a",
                                "wcag2aa",
                                "wcag21a",
                                "wcag21aa"
                            ]
                        }
                    });

                    return results.violations.map(violation => ({
                        id: violation.id,
                        impact: violation.impact || "minor",
                        description: violation.description,
                        help: violation.help,
                        helpUrl: violation.helpUrl,
                        count: violation.nodes.length,
                        elements: violation.nodes.slice(0, 10).map(node => ({
                            target: node.target,
                            summary: node.failureSummary || ""
                        }))
                    }));
                }
            """)

            critical = sum(
                item["count"] for item in axe_results
                if item["impact"] == "critical"
            )
            serious = sum(
                item["count"] for item in axe_results
                if item["impact"] == "serious"
            )
            moderate = sum(
                item["count"] for item in axe_results
                if item["impact"] == "moderate"
            )
            minor = sum(
                item["count"] for item in axe_results
                if item["impact"] == "minor"
            )

            total_issues = critical + serious + moderate + minor

            weighted_penalty = (
                critical * 10
                + serious * 5
                + moderate * 2
                + minor
            )

            score = max(0, min(100, 100 - weighted_penalty))

            return {
                "url": url,
                "page_title": page.title(),
                "score": score,
                "total_issues": total_issues,
                "critical_issues": critical,
                "serious_issues": serious,
                "moderate_issues": moderate,
                "minor_issues": minor,
                "violations": axe_results
            }

        finally:
            browser.close()
