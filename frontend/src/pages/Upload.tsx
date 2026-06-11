import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { Upload as UploadIcon, FileText, CheckCircle2, AlertCircle, Sparkles } from "lucide-react";

const REGISTER_TYPES = [
  { value: "attendance", label: "Attendance Register" },
  { value: "pm_poshan", label: "PM POSHAN Register" },
  { value: "stock", label: "Stock Register" },
  { value: "audit", label: "Audit Document" },
];

export default function UploadPage() {
  const [type, setType] = useState("attendance");
  const [file, setFile] = useState<File | null>(null);
  const [helperFile, setHelperFile] = useState<File | null>(null);
  const [result, setResult] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [helperLoading, setHelperLoading] = useState(false);
  const [err, setErr] = useState("");
  const [history, setHistory] = useState<any[]>([]);

  const refreshHistory = () => api.upload.history().then(setHistory);
  useEffect(() => {
    refreshHistory();
  }, []);

  const submit = async () => {
    if (!file) return;
    setLoading(true);
    setErr("");
    setResult(null);
    try {
      const fd = new FormData();
      fd.append("register_type", type);
      fd.append("file", file);
      const res = await api.upload.register(fd);
      setResult(res);
      refreshHistory();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  };

  const submitHelper = async () => {
    if (!helperFile) return;
    setHelperLoading(true);
    setErr("");
    setResult(null);
    try {
      const fd = new FormData();
      fd.append("file", helperFile);
      const res = await api.upload.helper(fd);
      setResult(res);
      refreshHistory();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setHelperLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Upload Register</h1>
        <p className="text-muted-foreground">Upload a register image — Gemini Vision will extract structured data.</p>
      </div>

      <Tabs defaultValue="upload">
        <TabsList>
          <TabsTrigger value="upload">New Upload</TabsTrigger>
          <TabsTrigger value="history">History ({history.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="upload" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Upload Register Image</CardTitle>
              <CardDescription>JPEG/PNG of a handwritten or printed register</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Register Type</Label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  {REGISTER_TYPES.map((r) => (
                    <Button
                      key={r.value}
                      variant={type === r.value ? "default" : "outline"}
                      onClick={() => setType(r.value)}
                      size="sm"
                    >
                      {r.label}
                    </Button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="file">Image File</Label>
                <input
                  id="file"
                  type="file"
                  accept="image/*"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="block w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-primary/10 file:text-primary hover:file:bg-primary/20"
                />
              </div>

              <Button onClick={submit} disabled={!file || loading} className="w-full sm:w-auto">
                <UploadIcon className="h-4 w-4 mr-2" />
                {loading ? "Extracting…" : "Upload & Extract"}
              </Button>

              {err && <div className="text-sm text-destructive">{err}</div>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                AI Helper
              </CardTitle>
              <CardDescription>Upload any register image and let AI label, clean, and save it</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="helper-file">Image File</Label>
                <input
                  id="helper-file"
                  type="file"
                  accept="image/*"
                  onChange={(e) => setHelperFile(e.target.files?.[0] || null)}
                  className="block w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-primary/10 file:text-primary hover:file:bg-primary/20"
                />
              </div>

              <Button onClick={submitHelper} disabled={!helperFile || helperLoading} className="w-full sm:w-auto">
                <Sparkles className="h-4 w-4 mr-2" />
                {helperLoading ? "Labeling & Saving..." : "AI Label & Save"}
              </Button>
            </CardContent>
          </Card>

          {result && (
            <Card className="mt-4">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {result.validation?.valid ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                  ) : (
                    <AlertCircle className="h-5 w-5 text-amber-600" />
                  )}
                  Extraction Result
                </CardTitle>
                <CardDescription>Register type: {result.register_type}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {result.extracted?.classification_summary && (
                  <div className="rounded-md bg-blue-50 border border-blue-200 p-3 text-sm text-blue-800">
                    {result.extracted.classification_summary}
                  </div>
                )}
                {result.validation?.issues?.length > 0 && (
                  <div className="rounded-md bg-amber-50 border border-amber-200 p-3 text-sm">
                    <div className="font-medium text-amber-800 mb-1">Validation issues:</div>
                    <ul className="text-amber-700 list-disc list-inside text-xs">
                      {result.validation.issues.map((i: string, idx: number) => (<li key={idx}>{i}</li>))}
                    </ul>
                  </div>
                )}
                {result.persist_error && (
                  <div className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-800">
                    <div className="font-medium mb-1">Save failed (data not persisted):</div>
                    <div className="text-xs">{result.persist_error}</div>
                  </div>
                )}
                {!result.persist_error && result.persisted && Object.keys(result.persisted).length > 0 && (
                  <div className="rounded-md bg-emerald-50 border border-emerald-200 p-3 text-sm text-emerald-800">
                    Saved to database: {JSON.stringify(result.persisted)}
                  </div>
                )}
                <details>
                  <summary className="cursor-pointer text-sm font-medium">Raw extracted JSON</summary>
                  <pre className="mt-2 p-3 bg-slate-50 rounded text-xs overflow-auto max-h-96">
                    {JSON.stringify(result.extracted, null, 2)}
                  </pre>
                </details>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="history">
          <Card>
            <CardContent className="pt-6">
              {history.length === 0 ? (
                <div className="text-sm text-muted-foreground text-center py-8">No uploads yet.</div>
              ) : (
                <div className="space-y-2">
                  {history.map((h) => (
                    <div key={h.id} className="flex items-center justify-between border-b pb-2 last:border-0">
                      <div className="flex items-center gap-3">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <div className="text-sm font-medium capitalize">{h.register_type.replace("_", " ")}</div>
                          <div className="text-xs text-muted-foreground">{new Date(h.created_at).toLocaleString()}</div>
                        </div>
                      </div>
                      <Badge variant={h.validation_status === "valid" ? "success" : "warning"}>
                        {h.validation_status}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
