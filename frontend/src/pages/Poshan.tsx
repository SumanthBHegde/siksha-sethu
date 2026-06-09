import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";

export default function PoshanPage() {
  const [summary, setSummary] = useState<any | null>(null);
  const [stock, setStock] = useState<any | null>(null);
  const [meal, setMeal] = useState({
    date: new Date().toISOString().slice(0, 10),
    beneficiaries: 15,
    meals_served: 15,
    rice_kg: 1.5,
    dal_kg: 0.5,
    vegetables_kg: 0.75,
    oil_l: 0.15,
  });
  const [saving, setSaving] = useState(false);

  const reload = async () => {
    const [s, st] = await Promise.all([api.poshan.summary(), api.poshan.stockStatus()]);
    setSummary(s);
    setStock(st);
  };
  useEffect(() => {
    reload();
  }, []);

  const saveMeal = async () => {
    setSaving(true);
    try {
      await api.poshan.addMeal({ ...meal, meal_type: "lunch", notes: "" });
      await reload();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">PM POSHAN</h1>
        <p className="text-muted-foreground">Mid-day meal records, stock, and consumption</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Meals served (month)</CardTitle></CardHeader>
          <CardContent><div className="text-3xl font-bold">{summary?.meals_served ?? 0}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Utilization</CardTitle></CardHeader>
          <CardContent><div className="text-3xl font-bold">{summary?.utilization_pct ?? 0}%</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Low stock alerts</CardTitle></CardHeader>
          <CardContent><div className="text-3xl font-bold text-amber-600">{stock?.low_stock_alerts?.length ?? 0}</div></CardContent>
        </Card>
      </div>

      <Tabs defaultValue="meal">
        <TabsList>
          <TabsTrigger value="meal">Record Meal</TabsTrigger>
          <TabsTrigger value="stock">Stock</TabsTrigger>
        </TabsList>

        <TabsContent value="meal">
          <Card>
            <CardHeader><CardTitle>Record Today's Meal</CardTitle></CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-3">
                <div className="space-y-1"><Label>Date</Label><Input type="date" value={meal.date} onChange={(e) => setMeal({ ...meal, date: e.target.value })} /></div>
                <div className="space-y-1"><Label>Beneficiaries</Label><Input type="number" value={meal.beneficiaries} onChange={(e) => setMeal({ ...meal, beneficiaries: +e.target.value })} /></div>
                <div className="space-y-1"><Label>Meals Served</Label><Input type="number" value={meal.meals_served} onChange={(e) => setMeal({ ...meal, meals_served: +e.target.value })} /></div>
                <div className="space-y-1"><Label>Rice (kg)</Label><Input type="number" step="0.1" value={meal.rice_kg} onChange={(e) => setMeal({ ...meal, rice_kg: +e.target.value })} /></div>
                <div className="space-y-1"><Label>Dal (kg)</Label><Input type="number" step="0.1" value={meal.dal_kg} onChange={(e) => setMeal({ ...meal, dal_kg: +e.target.value })} /></div>
                <div className="space-y-1"><Label>Vegetables (kg)</Label><Input type="number" step="0.1" value={meal.vegetables_kg} onChange={(e) => setMeal({ ...meal, vegetables_kg: +e.target.value })} /></div>
                <div className="space-y-1"><Label>Oil (L)</Label><Input type="number" step="0.01" value={meal.oil_l} onChange={(e) => setMeal({ ...meal, oil_l: +e.target.value })} /></div>
              </div>
              <Button onClick={saveMeal} disabled={saving} className="mt-4">{saving ? "Saving…" : "Save Meal Record"}</Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="stock">
          <Card>
            <CardHeader>
              <CardTitle>Current Stock</CardTitle>
              <CardDescription>Latest closing balances per item</CardDescription>
            </CardHeader>
            <CardContent>
              {!stock || stock.items.length === 0 ? (
                <div className="text-sm text-muted-foreground">No stock records yet. Upload a stock register.</div>
              ) : (
                <div className="space-y-2">
                  {stock.items.map((it: any) => {
                    const alert = stock.low_stock_alerts.find((a: any) => a.item === it.item);
                    return (
                      <div key={it.item} className="flex items-center justify-between p-3 border rounded-lg">
                        <div>
                          <div className="font-medium capitalize">{it.item}</div>
                          <div className="text-xs text-muted-foreground">As of {it.as_of}</div>
                        </div>
                        <div className="text-right">
                          <div className="font-mono text-lg">{it.closing_kg} kg</div>
                          {alert && <Badge variant="warning">Low stock</Badge>}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
