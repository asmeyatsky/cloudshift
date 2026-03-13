import { useState, useCallback } from "react";
import AuditReport from "../components/report/AuditReport";
import { useProjectStore, useManifestStore, useOperationStore, useValidationStore } from "../store";

export default function ReportPage() {
  const activeProject = useProjectStore((s) => s.activeProject);
  const entries = useManifestStore((s) => s.entries);
  const diffs = useOperationStore((s) => s.diffs);
  const refactorSummary = useOperationStore((s) => s.refactorSummary);
  const validationResult = useValidationStore((s) => s.result);

  const [loading, setLoading] = useState(false);
  const [reportHtml, setReportHtml] = useState<string | null>(null);

  const handleGenerate = useCallback(async () => {
    if (!activeProject) return;
    setLoading(true);

    // Simulate generation delay
    await new Promise((r) => setTimeout(r, 1500));

    const statusCounts = entries.reduce<Record<string, number>>((acc, e) => {
      acc[e.status] = (acc[e.status] ?? 0) + 1;
      return acc;
    }, {});

    const resourceCounts = entries.reduce<Record<string, number>>((acc, e) => {
      acc[e.resourceType] = (acc[e.resourceType] ?? 0) + 1;
      return acc;
    }, {});

    const issueRows = (validationResult?.issues ?? [])
      .map(
        (i) =>
          `<tr>
            <td style="padding:8px 12px;border-bottom:1px solid #1e1e2e;"><code style="color:#8be9fd;font-size:11px;">${i.code}</code></td>
            <td style="padding:8px 12px;border-bottom:1px solid #1e1e2e;"><span style="color:${i.severity === "error" ? "#ff5555" : i.severity === "warning" ? "#f1fa8c" : "#8be9fd"};">${i.severity}</span></td>
            <td style="padding:8px 12px;border-bottom:1px solid #1e1e2e;font-size:13px;color:#ccc;">${i.message}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #1e1e2e;font-family:monospace;font-size:11px;color:#888;">${i.filePath}:${i.line}</td>
          </tr>`,
      )
      .join("");

    const resourceRows = Object.entries(resourceCounts)
      .map(
        ([type, count]) =>
          `<tr><td style="padding:4px 0;color:#888;">${type}</td><td style="color:#fff;font-weight:600;">${count}</td></tr>`,
      )
      .join("");

    const statusRows = Object.entries(statusCounts)
      .map(
        ([status, count]) =>
          `<tr><td style="padding:4px 0;color:#888;text-transform:capitalize;">${status}</td><td style="color:#fff;font-weight:600;">${count} (${Math.round((count / entries.length) * 100)}%)</td></tr>`,
      )
      .join("");

    const valColor = validationResult?.passed ? "#50fa7b" : "#ff5555";
    const valText = validationResult?.passed ? "Yes" : validationResult ? "No" : "\u2014";

    const html = `
      <div style="font-family:system-ui,sans-serif;color:#e0e0e0;">
        <h2 style="color:#fff;margin-bottom:4px;">Migration Audit Report</h2>
        <p style="color:#888;font-size:13px;margin-top:0;">
          ${activeProject.name} &mdash;
          <span style="color:#8be9fd;">${activeProject.sourceProvider.toUpperCase()}</span>
          &rarr;
          <span style="color:#50fa7b;">${activeProject.targetProvider.toUpperCase()}</span>
          &mdash; Generated ${new Date().toLocaleString()}
        </p>

        <h3 style="color:#bd93f9;margin-top:24px;">Refactor Summary</h3>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <tr><td style="padding:6px 0;color:#888;">Files Processed</td><td style="color:#fff;font-weight:600;">${refactorSummary?.total ?? "\u2014"}</td></tr>
          <tr><td style="padding:6px 0;color:#888;">Files Changed</td><td style="color:#fff;font-weight:600;">${diffs.length || (refactorSummary?.changed ?? "\u2014")}</td></tr>
          <tr><td style="padding:6px 0;color:#888;">Via Patterns</td><td style="color:#fff;font-weight:600;">${refactorSummary?.patternCount ?? "\u2014"}</td></tr>
          <tr><td style="padding:6px 0;color:#888;">Via LLM</td><td style="color:#fff;font-weight:600;">${refactorSummary?.llmCount ?? "\u2014"}</td></tr>
          <tr><td style="padding:6px 0;color:#888;">Skipped</td><td style="color:#fff;font-weight:600;">${refactorSummary?.skipped ?? "\u2014"}</td></tr>
          <tr><td style="padding:6px 0;color:#888;">Validation Issues</td><td style="color:#fff;font-weight:600;">${validationResult?.summary.totalIssues ?? "\u2014"}</td></tr>
          <tr><td style="padding:6px 0;color:#888;">Validation Passed</td><td style="font-weight:600;color:${valColor};">${valText}</td></tr>
        </table>

        ${entries.length > 0 ? `
        <h3 style="color:#bd93f9;margin-top:24px;">Resource Breakdown</h3>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          ${resourceRows}
        </table>

        <h3 style="color:#bd93f9;margin-top:24px;">Entry Status</h3>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          ${statusRows}
        </table>` : ""}

        ${
          validationResult && validationResult.issues.length > 0
            ? `
          <h3 style="color:#bd93f9;margin-top:24px;">Validation Issues</h3>
          <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead><tr style="text-align:left;border-bottom:2px solid #2a2a3e;">
              <th style="padding:8px 12px;color:#888;font-weight:600;">Code</th>
              <th style="padding:8px 12px;color:#888;font-weight:600;">Severity</th>
              <th style="padding:8px 12px;color:#888;font-weight:600;">Message</th>
              <th style="padding:8px 12px;color:#888;font-weight:600;">Location</th>
            </tr></thead>
            <tbody>${issueRows}</tbody>
          </table>`
            : `<p style="color:#50fa7b;margin-top:24px;">All validation checks passed.</p>`
        }
      </div>
    `;

    setReportHtml(html);
    setLoading(false);
  }, [activeProject, entries, diffs, refactorSummary, validationResult]);

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white">Report</h1>
        <p className="mt-1 text-base text-gray-500">
          Generate and view comprehensive migration audit reports
        </p>
      </div>
      <AuditReport
        loading={loading}
        reportHtml={reportHtml}
        onGenerate={handleGenerate}
      />
    </div>
  );
}
