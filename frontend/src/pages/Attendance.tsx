import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";

export default function AttendancePage() {
  const [summary, setSummary] = useState<any | null>(null);
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [students, setStudents] = useState<any[]>([]);
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [marks, setMarks] = useState<Record<number, string>>({});
  const [saving, setSaving] = useState(false);

  const reload = async () => {
    const [s, a, st] = await Promise.all([
      api.attendance.summary(),
      api.attendance.anomalies(),
      api.students.list(),
    ]);
    setSummary(s);
    setAnomalies(a.anomalies);
    setStudents(st);
  };

  useEffect(() => {
    reload();
  }, []);

  useEffect(() => {
    if (!date) return;
    api.attendance.byDate(date).then((rows) => {
      const m: Record<number, string> = {};
      rows.forEach((r: any) => (m[r.student_id] = r.status));
      setMarks(m);
    });
  }, [date, students.length]);

  const save = async () => {
    setSaving(true);
    try {
      const entries = students.map((s) => ({ student_id: s.id, status: marks[s.id] || "absent" }));
      await api.attendance.bulk(date, entries);
      await reload();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Attendance</h1>
        <p className="text-muted-foreground">Daily marking, monthly summaries, anomaly detection</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Last 30 days</CardTitle></CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{summary?.attendance_percentage ?? 0}%</div>
            <div className="text-xs text-muted-foreground">{summary?.present} P / {summary?.absent} A / {summary?.late} L</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Students</CardTitle></CardHeader>
          <CardContent><div className="text-3xl font-bold">{summary?.total_students ?? 0}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Anomalies</CardTitle></CardHeader>
          <CardContent><div className="text-3xl font-bold text-amber-600">{anomalies.length}</div></CardContent>
        </Card>
      </div>

      <Tabs defaultValue="mark">
        <TabsList>
          <TabsTrigger value="mark">Mark Attendance</TabsTrigger>
          <TabsTrigger value="anomalies">Anomalies</TabsTrigger>
        </TabsList>

        <TabsContent value="mark">
          <Card>
            <CardHeader>
              <CardTitle>Daily Attendance</CardTitle>
              <CardDescription>Choose a date and mark each student</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3">
                <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="max-w-xs" />
                <Button onClick={save} disabled={saving}>{saving ? "Saving…" : "Save"}</Button>
              </div>

              <div className="border rounded-lg divide-y">
                {students.map((s) => (
                  <div key={s.id} className="flex items-center justify-between p-3">
                    <div>
                      <div className="font-medium">{s.name}</div>
                      <div className="text-xs text-muted-foreground">Roll {s.roll_no}</div>
                    </div>
                    <div className="flex gap-1">
                      {["present", "absent", "late"].map((status) => (
                        <Button
                          key={status}
                          size="sm"
                          variant={marks[s.id] === status ? "default" : "outline"}
                          onClick={() => setMarks({ ...marks, [s.id]: status })}
                          className="capitalize"
                        >
                          {status[0].toUpperCase()}
                        </Button>
                      ))}
                    </div>
                  </div>
                ))}
                {students.length === 0 && (
                  <div className="p-6 text-sm text-muted-foreground text-center">
                    No students yet. Upload an attendance register or add students.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="anomalies">
          <Card>
            <CardHeader>
              <CardTitle>Attendance Anomalies (under 75%)</CardTitle>
              <CardDescription>Students needing attention over last 30 days</CardDescription>
            </CardHeader>
            <CardContent>
              {anomalies.length === 0 ? (
                <div className="text-sm text-emerald-600">No anomalies detected.</div>
              ) : (
                <div className="space-y-2">
                  {anomalies.map((a) => (
                    <div key={a.student_id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <div className="font-medium">{a.name}</div>
                        <div className="text-xs text-muted-foreground">Roll {a.roll_no} · {a.present_days}/{a.total_days} days</div>
                      </div>
                      <Badge variant={a.attendance_pct < 50 ? "destructive" : "warning"}>{a.attendance_pct}%</Badge>
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
