import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { Users, UtensilsCrossed, ShieldCheck, Upload as UploadIcon, AlertTriangle } from "lucide-react";

export default function Dashboard() {
  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.dashboard().then(setData).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-muted-foreground">Loading dashboard…</div>;
  if (!data) return <div className="p-8 text-destructive">Failed to load dashboard.</div>;

  const att = data.attendance;
  const poshan = data.poshan;
  const audit = data.audit;
  const stock = data.stock;
  const auditBadge: "success" | "warning" | "destructive" =
    audit.readiness_score >= 80 ? "success" : audit.readiness_score >= 50 ? "warning" : "destructive";

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Welcome back</h1>
        <p className="text-muted-foreground">Overview of your school administration today.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Attendance (30d)</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{att.attendance_percentage}%</div>
            <p className="text-xs text-muted-foreground">
              {att.present} present / {att.absent} absent / {att.late} late
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">PM POSHAN (this month)</CardTitle>
            <UtensilsCrossed className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{poshan.meals_served}</div>
            <p className="text-xs text-muted-foreground">
              meals · {poshan.utilization_pct}% utilization
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Audit Readiness</CardTitle>
            <ShieldCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{audit.readiness_score}</div>
            <Badge variant={auditBadge} className="mt-1">
              {audit.readiness_score >= 80 ? "Ready" : audit.readiness_score >= 50 ? "Needs work" : "Action needed"}
            </Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Stock Alerts</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stock.low_stock_alerts.length}</div>
            <p className="text-xs text-muted-foreground">low-stock items</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Audit Recommendations</CardTitle>
            <CardDescription>What to do to improve readiness</CardDescription>
          </CardHeader>
          <CardContent>
            {audit.recommendations.length === 0 ? (
              <div className="text-sm text-emerald-600">All requirements satisfied.</div>
            ) : (
              <ul className="space-y-2 text-sm">
                {audit.recommendations.map((r: string, i: number) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-primary">→</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UploadIcon className="h-4 w-4" /> Recent Uploads
            </CardTitle>
            <CardDescription>Last 5 register extractions</CardDescription>
          </CardHeader>
          <CardContent>
            {data.recent_uploads.length === 0 ? (
              <div className="text-sm text-muted-foreground">No uploads yet.</div>
            ) : (
              <ul className="space-y-2 text-sm">
                {data.recent_uploads.map((u: any) => (
                  <li key={u.id} className="flex items-center justify-between border-b last:border-0 pb-2">
                    <div>
                      <div className="font-medium capitalize">{u.register_type.replace("_", " ")}</div>
                      <div className="text-xs text-muted-foreground">{new Date(u.created_at).toLocaleString()}</div>
                    </div>
                    <Badge variant={u.validation_status === "valid" ? "success" : "warning"}>
                      {u.validation_status}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
