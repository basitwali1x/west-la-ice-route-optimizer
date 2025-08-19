import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Progress } from './ui/progress';
import { Badge } from './ui/badge';
import { Alert, AlertDescription } from './ui/alert';
import { getVisitStatus, resetWeeklyVisits } from '../services/api';
import { WeeklyVisitStatus } from '../types';

export function WeeklyVisitDashboard() {
  const [visitStatus, setVisitStatus] = useState<{
    depot_status: { [key: string]: WeeklyVisitStatus };
    total_customers: number;
    total_visited: number;
    total_overdue: number;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resetLoading, setResetLoading] = useState(false);

  const fetchVisitStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getVisitStatus();
      setVisitStatus(response);
    } catch (err) {
      setError('Failed to fetch visit status');
      console.error('Error fetching visit status:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleWeeklyReset = async () => {
    try {
      setResetLoading(true);
      setError(null);
      await resetWeeklyVisits({ force_reset: true });
      await fetchVisitStatus();
    } catch (err) {
      setError('Failed to reset weekly visits');
      console.error('Error resetting weekly visits:', err);
    } finally {
      setResetLoading(false);
    }
  };

  useEffect(() => {
    fetchVisitStatus();
    const interval = setInterval(fetchVisitStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !visitStatus) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Weekly Visit Dashboard</CardTitle>
          <CardDescription>Loading visit status...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Weekly Visit Dashboard</CardTitle>
        </CardHeader>
        <CardContent>
          <Alert>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          <Button onClick={fetchVisitStatus} className="mt-4">
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!visitStatus) {
    return null;
  }

  const getPriorityColor = (overdue: number) => {
    if (overdue > 10) return 'destructive';
    if (overdue > 5) return 'secondary';
    return 'default';
  };


  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Weekly Visit Dashboard</CardTitle>
            <CardDescription>
              Track weekly customer visits across all depots
            </CardDescription>
          </div>
          <Button 
            onClick={handleWeeklyReset} 
            disabled={resetLoading}
            variant="outline"
          >
            {resetLoading ? 'Resetting...' : 'Reset Weekly Visits'}
          </Button>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="text-center">
              <div className="text-2xl font-bold">{visitStatus.total_customers}</div>
              <div className="text-sm text-muted-foreground">Total Customers</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{visitStatus.total_visited}</div>
              <div className="text-sm text-muted-foreground">Visited This Week</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">{visitStatus.total_overdue}</div>
              <div className="text-sm text-muted-foreground">Overdue Visits</div>
            </div>
          </div>

          <div className="space-y-4">
            {Object.entries(visitStatus.depot_status).map(([depotName, status]) => (
              <Card key={depotName}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{depotName} Depot</CardTitle>
                    <div className="flex items-center space-x-2">
                      <Badge variant={getPriorityColor(status.overdue_customers)}>
                        {status.overdue_customers} Overdue
                      </Badge>
                      <Badge variant="outline">
                        {status.completion_percentage}% Complete
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span>Progress: {status.visited_this_week} / {status.total_customers}</span>
                      <span>{status.pending_visits} pending</span>
                    </div>
                    <Progress 
                      value={status.completion_percentage} 
                      className="h-3"
                    />
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <div className="font-medium">{status.total_customers}</div>
                        <div className="text-muted-foreground">Total</div>
                      </div>
                      <div>
                        <div className="font-medium text-green-600">{status.visited_this_week}</div>
                        <div className="text-muted-foreground">Visited</div>
                      </div>
                      <div>
                        <div className="font-medium text-red-600">{status.overdue_customers}</div>
                        <div className="text-muted-foreground">Overdue</div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {visitStatus.total_overdue > 0 && (
            <Alert className="mt-4">
              <AlertDescription>
                <strong>Attention:</strong> {visitStatus.total_overdue} customers are overdue for visits (&gt;7 days). 
                These customers will be prioritized in the next route optimization.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
