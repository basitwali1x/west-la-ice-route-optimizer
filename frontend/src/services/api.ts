import { Customer, RouteOptimizationRequest, RouteOptimizationResponse } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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
};
