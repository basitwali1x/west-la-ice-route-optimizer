import { Customer, RouteOptimizationRequest, RouteOptimizationResponse, WeeklyResetRequest, VisitTrackingUpdate } from '../types';

export interface SheetsSync {
  sheet_id: string;
  last_sync?: string;
  status?: string;
}

export interface DriverRoute {
  truck_id: string;
  depot: string;
  day: string;
  stops: any[];
  total_distance: number;
  estimated_hours: number;
  priority_stops: string[];
}

const API_URL = import.meta.env.VITE_API_URL || 'https://app-ezywugpc.fly.dev';

export const api = {
  async getCustomers(): Promise<Customer[]> {
    const response = await fetch(`${API_URL}/customers`);
    if (!response.ok) {
      throw new Error('Failed to fetch customers');
    }
    return response.json();
  },

  async getCustomerCount(): Promise<{ count: number }> {
    const response = await fetch(`${API_URL}/customers/count`);
    if (!response.ok) {
      throw new Error('Failed to fetch customer count');
    }
    return response.json();
  },

  async optimizeRoutes(request: RouteOptimizationRequest): Promise<RouteOptimizationResponse> {
    const response = await fetch(`${API_URL}/optimize-routes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    
    if (!response.ok) {
      throw new Error('Failed to optimize routes');
    }
    return response.json();
  },

  async getDepotInfo(): Promise<{ depots: { name: string; address: string; latitude: number; longitude: number }[] }> {
    const response = await fetch(`${API_URL}/depots`);
    if (!response.ok) {
      throw new Error('Failed to fetch depot info');
    }
    return response.json();
  },

  async verifyCompletion(): Promise<{ complete: boolean; last_update: string; status: string }> {
    const response = await fetch(`${API_URL}/verify-completion`);
    if (!response.ok) {
      throw new Error('Failed to verify completion');
    }
    return response.json();
  },

  async verifyLufkinRoute(stops: any[]): Promise<{ valid: boolean; errors: string[] }> {
    const response = await fetch(`${API_URL}/verify-lufkin-route`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ stops }),
    });
    
    if (!response.ok) {
      throw new Error('Failed to verify Lufkin route');
    }
    return response.json();
  },

  async reoptimizeRoutes(depot: string, day: string = 'Monday', force: boolean = true): Promise<any> {
    const response = await fetch(`${API_URL}/reoptimize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ depot, day, force }),
    });
    
    if (!response.ok) {
      throw new Error('Failed to reoptimize routes');
    }
    return response.json();
  },

  async syncFromSheets(sheetsSync: SheetsSync): Promise<any> {
    const response = await fetch(`${API_URL}/sync-from-sheets`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(sheetsSync),
    });
    
    if (!response.ok) {
      throw new Error('Failed to sync from sheets');
    }
    return response.json();
  },

  async optimizeWithSheets(sheetsSync: SheetsSync): Promise<any> {
    const response = await fetch(`${API_URL}/optimize-with-sheets`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(sheetsSync),
    });
    
    if (!response.ok) {
      throw new Error('Failed to optimize with sheets');
    }
    return response.json();
  },

  async getDriverRoutes(truckId: string, day: string = 'Monday'): Promise<any> {
    const response = await fetch(`${API_URL}/driver-routes/${truckId}?day=${day}`);
    if (!response.ok) {
      throw new Error('Failed to fetch driver routes');
    }
    return response.json();
  },

  async rebalanceTrucks(rebalanceData: any): Promise<any> {
    const response = await fetch(`${API_URL}/rebalance-trucks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(rebalanceData),
    });
    
    if (!response.ok) {
      throw new Error('Failed to rebalance trucks');
    }
    return response.json();
  },

  async optimizeCompleteWeeklyRoutes(request: RouteOptimizationRequest): Promise<RouteOptimizationResponse> {
    const response = await fetch(`${API_URL}/optimize-complete-weekly-routes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    
    if (!response.ok) {
      throw new Error('Failed to optimize complete weekly routes');
    }
    return response.json();
  },
};

export const resetWeeklyVisits = async (request: WeeklyResetRequest = {}) => {
  try {
    const response = await fetch(`${API_URL}/reset-weekly-visits`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      throw new Error('Failed to reset weekly visits');
    }
    return await response.json();
  } catch (error) {
    console.error('Error resetting weekly visits:', error);
    throw error;
  }
};

export const getVisitStatus = async () => {
  try {
    const response = await fetch(`${API_URL}/visit-status`);
    if (!response.ok) {
      throw new Error('Failed to get visit status');
    }
    return await response.json();
  } catch (error) {
    console.error('Error getting visit status:', error);
    throw error;
  }
};

export const markCustomerVisited = async (update: VisitTrackingUpdate) => {
  try {
    const response = await fetch(`${API_URL}/mark-customer-visited`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(update),
    });
    if (!response.ok) {
      throw new Error('Failed to mark customer as visited');
    }
    return await response.json();
  } catch (error) {
    console.error('Error marking customer as visited:', error);
    throw error;
  }
};

export const optimizeWeeklyRoutes = async (request: RouteOptimizationRequest) => {
  try {
    const response = await fetch(`${API_URL}/optimize-weekly-routes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      throw new Error('Failed to optimize weekly routes');
    }
    return await response.json();
  } catch (error) {
    console.error('Error optimizing weekly routes:', error);
    throw error;
  }
};

export const syncDayRoutes = async (sheetsSync: SheetsSync) => {
  try {
    const response = await fetch(`${API_URL}/sync-day-routes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(sheetsSync),
    });
    if (!response.ok) {
      throw new Error('Failed to sync day routes');
    }
    return await response.json();
  } catch (error) {
    console.error('Error syncing day routes:', error);
    throw error;
  }
};

export const updateDeliveryCompletion = async (completionData: any) => {
  try {
    const response = await fetch(`${API_URL}/update-delivery-completion`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(completionData),
    });
    if (!response.ok) {
      throw new Error('Failed to update delivery completion');
    }
    return await response.json();
  } catch (error) {
    console.error('Error updating delivery completion:', error);
    throw error;
  }
};

export const rebalanceTrucksAdvanced = async (rebalanceData: any) => {
  try {
    const response = await fetch(`${API_URL}/rebalance-trucks-advanced`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(rebalanceData),
    });
    if (!response.ok) {
      throw new Error('Failed to rebalance trucks (advanced)');
    }
    return await response.json();
  } catch (error) {
    console.error('Error rebalancing trucks (advanced):', error);
    throw error;
  }
};
