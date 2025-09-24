import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Progress } from "./ui/progress";
import { apiGetJob } from "@/lib/api";
import { type JobMeta } from "@/lib/types";
import { useAuthStore } from "@/lib/authStore";
import { toast } from "sonner";

type AnalysisProps = Partial<{
  jobId: string;
  documentId: string;
  query: string;
  onBack: () => void;
}>;

export function Analysis(props: AnalysisProps = {}) {
  const { token } = useAuthStore();
  const navigate = useNavigate();
  const params = useParams();
  const jobIdFromRoute = params.jobId;
  const jobId = useMemo(() => props.jobId || jobIdFromRoute || "", [props.jobId, jobIdFromRoute]);
  const [progress, setProgress] = useState<number>(0);
  const [jobStatus, setJobStatus] = useState<JobMeta["status"] | null>(null);

  useEffect(() => {
    if (!jobId || !token) return;
    const currentJobId = jobId;
    const authToken = token;
    let cancelled = false;

    async function poll() {
      try {
        const meta = await apiGetJob(currentJobId, authToken);
        if (cancelled) return;
        setJobStatus(meta.status);
        const raw = meta.progress ?? 0;
        const pct = raw <= 1 ? Math.round(raw * 100) : Math.round(raw);
        setProgress(Math.max(0, Math.min(100, pct)));
        if (meta.status === "completed" || meta.status === "failed") return;
        setTimeout(poll, 1500);
      } catch (e: any) {
        if (!cancelled) toast.error(e?.message || "Failed to fetch job status");
      }
    }

    poll();
    return () => { cancelled = true; };
  }, [jobId, token]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Analyzing document</CardTitle>
      </CardHeader>
      <CardContent>
        <div>Processing your file. This may take a moment.</div>
        <Progress value={progress} />
        <div>Status: {jobStatus || "unknown"} {progress ? `(${progress}%)` : null}</div>
        <Button onClick={() => (props.onBack ? props.onBack() : navigate(-1))} variant="secondary">Back</Button>
      </CardContent>
    </Card>
  );
}


