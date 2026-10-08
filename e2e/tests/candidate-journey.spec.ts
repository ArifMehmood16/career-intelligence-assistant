import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const fixtures = resolve(import.meta.dirname, "../../sample-data/fixtures");
const cv = resolve(fixtures, "resumes/cv-strong-match.txt");
const advert = resolve(fixtures, "job-descriptions/jd-clean-match.txt");
const cvText = readFileSync(cv, "utf8");
const title = "Synthetic browser Data Engineer";

async function checkSource(page: Page) {
  const source = page.getByRole("dialog");
  await expect(source.locator("blockquote")).toBeVisible();
  const quote = (await source.locator("blockquote").textContent())?.trim() ?? "";
  expect(quote.length).toBeGreaterThan(10);
  expect(cvText).toContain(quote);
  await source.getByRole("button", { name: "Close evidence" }).click();
}

test("candidate completes analysis, reads sources, drafts and asks with persisted history", async ({ page }) => {
  const externalRequests: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.protocol.startsWith("http") && url.hostname !== "127.0.0.1") {
      externalRequests.push(url.origin);
    }
  });
  await page.goto("/");
  const cvCard = page.getByRole("region", { name: "CV", exact: true });
  const chooser = page.waitForEvent("filechooser");
  await cvCard.getByRole("button", { name: "Browse", exact: true }).click();
  await (await chooser).setFiles(cv);
  await expect(cvCard.getByText("cv-strong-match.txt", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Add role", exact: true }).click();
  const form = page.getByRole("dialog", { name: "Add role" });
  await form.getByLabel("Role title").fill(title);
  await form.getByLabel("Company").fill("Synthetic Northwind");
  await form.getByLabel("Job description file").setInputFiles(advert);
  await form.getByRole("button", { name: "Add role", exact: true }).click();
  await expect(form).toBeHidden();
  await page.getByRole("link", { name: title, exact: true }).click();
  await expect(page.getByRole("region", { name: "Fit", exact: true })).toContainText("/ 100");
  const requirements = page.getByRole("region", { name: "Requirements", exact: true });
  await expect(requirements.getByRole("article").first()).toBeVisible();
  await expect(requirements).toContainText("earned points");
  await page.getByLabel("Match status").selectOption("met");
  await expect(requirements.getByRole("article").first()).toContainText("Met");
  await page.getByLabel("Requirement score").selectOption("75-100");
  await expect(requirements.getByRole("article").first()).toBeVisible();
  await requirements.getByRole("button", { name: "Clear filters" }).click();
  await requirements.getByRole("button", { name: "Show retrieval trace" }).first().click();
  const trace = page.getByRole("dialog", { name: "Retrieval trace" });
  await expect(trace.getByRole("table").first()).toBeVisible();
  await trace.getByRole("button", { name: "Close", exact: true }).click();

  await page.getByRole("tab", { name: "Prepare", exact: true }).click();
  await page.getByRole("region", { name: "Evidence to lead with" }).getByRole("button").first().click();
  await checkSource(page);
  await page.getByRole("tab", { name: "Letter", exact: true }).click();
  await page.getByRole("button", { name: "Generate letter", exact: true }).click();
  await expect(page.getByRole("region", { name: "Generated letter" })).toBeVisible();
  await page.getByRole("button", { name: "Citation 1 details", exact: true }).click();
  await checkSource(page);
  await page.reload();
  await page.getByRole("tab", { name: "Letter", exact: true }).click();
  await expect(page.getByRole("region", { name: "Generated letter" })).toBeVisible();

  await page.getByRole("link", { name: "Ask", exact: true }).click();
  const question = "What evidence do I have for Python?";
  await page.getByPlaceholder("Ask about your CV and the roles you saved").fill(question);
  await page.getByRole("button", { name: "Send", exact: true }).click();
  const citation = page.getByRole("button", { name: "dbt, Snowflake, SQL, Python, Looker, Git, CI for analytics", exact: true }).first();
  await expect(citation).toBeVisible();
  await expect(page.getByRole("status", { name: "Question processing" })).toBeHidden();
  await citation.click();
  await checkSource(page);
  await page.reload();
  await expect(page.getByText(question, { exact: true })).toBeVisible();
  await expect(citation).toBeVisible();
  await citation.click();
  await checkSource(page);

  page.on("dialog", (dialog) => void dialog.accept());
  await page.getByRole("button", { name: "Delete history", exact: true }).click();
  await page.getByRole("link", { name: "Workspace", exact: true }).click();
  await page.getByRole("button", { name: `Delete ${title}`, exact: true }).click();
  await expect(page.getByRole("link", { name: title, exact: true })).toHaveCount(0);
  await page.getByRole("region", { name: "CV", exact: true }).getByRole("button", { name: "Delete", exact: true }).click();
  await expect(page.getByRole("region", { name: "CV", exact: true })).toContainText("Upload your CV");
  expect(externalRequests).toEqual([]);
});
