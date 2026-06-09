import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { ShieldCheck, FileText, Upload as UploadIcon } from "lucide-react";

const REQUIRED_DOCS = [
  { value: "attendance_summary", label: "Attendance Summary" },
  { value: "stock_summary", label: "Stock Summary" },
  { value: "meal_summary", label: "Meal Summary" },
  { value: "compliance_certificate", label: "Compliance Certificate" },
];

export default function AuditPage() {
  const [readiness, setReadiness] = useState<any | null>(null);
  const [docs, setDocs] = useState<any[]>([]);
  const [docType, setDocType] = useState("attendance_summary");
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [saving, setSaving] = useState(false);

  const reload = async () => {
    const [r, d] = await Promise.all([api.audit.readiness(), api.audit.listDocs()]);
    setReadiness(r);
    setDocs(d);
  };
  useEffect(() => {
    reload();
  }, []);

  const upload = async () => {
    if (!file) return;
    setSaving(true);
    try {
      const fd = new FormData();
      fd.append("doc_type", docType);
      fd.append("title", title);
      fd.append("file", file);
      await api.audit.upload(fd);
      setFile(null);
      setTitle("");
      await reload();
    } finally {
      setSaving(false);
    }
  };

  const score = readiness?.readiness_score ?? 0;
  const badge: "success" | "warning" | "destructive" = score >= 80 ? "success" : score >= 50 ? "warning" : "destructive";

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Audit Readiness</h1>
        <p className="text-muted-foreground">Compliance status, missing documents, recommendations</p>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2"><ShieldCheck className="h-5 w-5" /> Readiness Score</CardTitle>
            <CardDescription>Composite score across attendance, meals, stock, documents</CardDescription>
          </div>
          <div className="text-right">
            <div className="text-4xl font-bold">{score}<span className="text-lg text-muted-foreground">/100</span></div>
            <Badge variant={badge} className="mt-1">
              {score >= 80 ? "Audit Ready" : score >= 50 ? "Needs Improvement" : "Action Required"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-3 gap-3 text-sm">
            <div className="p-3 bg-slate-50 rounded">
              <div className="text-muted-foreground">Attendance (30d)</div>
              <div className="font-semibold">{readiness?.attendance_days_30 ?? 0} days</div>
            </div>
            <div className="p-3 bg-slate-50 rounded">
              <div className="text-muted-foreground">Meals (30d)</div>
              <div className="font-semibold">{readiness?.meal_days_30 ?? 0} days</div>
            </div>
            <div className="p-3 bg-slate-50 rounded">
              <div className="text-muted-foreground">Stock items</div>
              <div className="font-semibold">{readiness?.stock_items_tracked ?? 0}</div>
            </div>
          </div>

          {readiness?.recommendations?.length > 0 && (
            <div>
              <div className="font-medium text-sm mb-2">Recommendations</div>
              <ul className="space-y-1 text-sm">
                {readiness.recommendations.map((r: string, i: number) => (
                  <li key={i} className="flex gap-2"><span className="text-primary">→</span>{r}</li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Required Documents</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              {REQUIRED_DOCS.map((d) => {
                const missing = readiness?.missing_documents?.includes(d.value);
                return (
                  <div key={d.value} className="flex items-center justify-between p-2 border rounded">
                    <span className="text-sm">{d.label}</span>
                    {missing
                      ? <Badge variant="destructive">Missing</Badge>
                      : <Badge variant="success">Uploaded</Badge>}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Upload Document</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1">
              <Label>Document Type</Label>
              <select className="w-full h-10 px-3 border rounded-md text-sm bg-background" value={docType} onChange={(e) => setDocType(e.target.value)}>
                {REQUIRED_DOCS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <Label>Title (optional)</Label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. May 2026 Attendance Summary" />
            </div>
            <div className="space-y-1">
              <Label>File</Label>
              <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} className="block w-full text-sm" />
            </div>
            <Button onClick={upload} disabled={!file || saving}>
              <UploadIcon className="h-4 w-4 mr-2" />
              {saving ? "Uploading…" : "Upload"}
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Uploaded Documents ({docs.length})</CardTitle></CardHeader>
        <CardContent>
          {docs.length === 0 ? (
            <div className="text-sm text-muted-foreground">No documents uploaded.</div>
          ) : (
            <div className="space-y-2">
              {docs.map((d) => (
                <div key={d.id} className="flex items-center justify-between p-3 border rounded">
                  <div className="flex items-center gap-3">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <div className="text-sm font-medium">{d.title || d.doc_type}</div>
                      <div className="text-xs text-muted-foreground">{d.doc_type} · {new Date(d.uploaded_at).toLocaleString()}</div>
                    </div>
                  </div>
                  <Badge>{d.status}</Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
