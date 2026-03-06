import { useState, useCallback } from "react";
import AuditReport from "../components/report/AuditReport";
import { useProjectStore } from "../store";
import { reportApi } from "../services/api";

export default function ReportPage() {
  const activeProject = useProjectStore((s) => s.activeProject);
  const [loading, setLoading] = useState(false);
  const [reportHtml, setReportHtml] = useState<string | null>(null);

  const handleGenerate = useCallback(async () => {
    if (!activeProject) return;
    setLoading(true);
    // Generate and then fetch the latest report
    const genRes = await reportApi.generate(activeProject.id);
    if (genRes.success) {
      const reportRes = await reportApi.get(activeProject.id);
      if (reportRes.success) {
        setReportHtml(reportRes.data.html);
      }
    }
    setLoading(false);
  }, [activeProject]);

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Report</h1>
        <p className="mt-1 text-sm text-gray-500">
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
