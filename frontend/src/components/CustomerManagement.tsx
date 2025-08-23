import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Alert, AlertDescription } from './ui/alert';
import { Input } from './ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { 
  Plus, 
  Edit, 
  Trash2, 
  Search,
  Filter,
  AlertTriangle
} from 'lucide-react';
import { Customer } from '../types';
import { api } from '../services/api';

interface CustomerManagementProps {
  customers: Customer[];
  onCustomersChange: (customers: Customer[]) => void;
  selectedCustomers: Set<number>;
  onSelectedCustomersChange: (selected: Set<number>) => void;
}

export function CustomerManagement({ 
  customers, 
  onCustomersChange, 
  selectedCustomers, 
  onSelectedCustomersChange 
}: CustomerManagementProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDepot, setSelectedDepot] = useState<string>('all');
  const [isEditing, setIsEditing] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [error, setError] = useState<string | null>(null);

  const depots = ['Leesville', 'Lake Charles', 'Lufkin'];

  const filteredCustomers = customers.filter(customer => {
    const matchesSearch = customer.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         customer.address.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesDepot = selectedDepot === 'all' || customer.depot === selectedDepot;
    return matchesSearch && matchesDepot;
  });

  const handleSelectCustomer = (customerId: number) => {
    const newSelected = new Set(selectedCustomers);
    if (newSelected.has(customerId)) {
      newSelected.delete(customerId);
    } else {
      newSelected.add(customerId);
    }
    onSelectedCustomersChange(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedCustomers.size === filteredCustomers.length) {
      onSelectedCustomersChange(new Set());
    } else {
      onSelectedCustomersChange(new Set(filteredCustomers.map(c => c.id)));
    }
  };

  const handleEditCustomer = (customer: Customer) => {
    setEditingCustomer(customer);
    setIsEditing(true);
  };

  const handleDeleteCustomer = async (customerId: number) => {
    if (!confirm('Are you sure you want to delete this customer?')) return;
    
    try {
      await api.deleteCustomer(customerId);
      const updatedCustomers = customers.filter(c => c.id !== customerId);
      onCustomersChange(updatedCustomers);
      
      const newSelected = new Set(selectedCustomers);
      newSelected.delete(customerId);
      onSelectedCustomersChange(newSelected);
    } catch (err) {
      setError('Failed to delete customer');
    }
  };

  const handleSaveCustomer = async (customer: Customer) => {
    try {
      if (editingCustomer && editingCustomer.id) {
        await api.updateCustomer(customer.id, customer);
        const updatedCustomers = customers.map(c => 
          c.id === customer.id ? customer : c
        );
        onCustomersChange(updatedCustomers);
      } else {
        const result = await api.createCustomer(customer);
        const newCustomer = result.customer;
        onCustomersChange([...customers, newCustomer]);
      }
      setIsEditing(false);
      setEditingCustomer(null);
    } catch (err) {
      setError('Failed to save customer');
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Customer Management</span>
            <Button onClick={() => {
              setEditingCustomer(null);
              setIsEditing(true);
            }} className="flex items-center space-x-2">
              <Plus className="h-4 w-4" />
              <span>Add Customer</span>
            </Button>
          </CardTitle>
          <CardDescription>
            Manage customer database and select customers for route optimization
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-64">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search customers by name or address..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={selectedDepot} onValueChange={setSelectedDepot}>
              <SelectTrigger className="w-48">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Filter by depot" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Depots</SelectItem>
                {depots.map(depot => (
                  <SelectItem key={depot} value={depot}>{depot}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
            <div className="flex items-center space-x-4">
              <Button
                variant="outline"
                size="sm"
                onClick={handleSelectAll}
              >
                {selectedCustomers.size === filteredCustomers.length ? 'Deselect All' : 'Select All'}
              </Button>
              <span className="text-sm text-gray-600">
                {selectedCustomers.size} of {filteredCustomers.length} customers selected
              </span>
            </div>
          </div>

          {error && (
            <Alert className="border-red-200 bg-red-50">
              <AlertTriangle className="h-4 w-4 text-red-600" />
              <AlertDescription className="text-red-800">{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2 max-h-96 overflow-y-auto">
            {filteredCustomers.map((customer) => (
              <div
                key={customer.id}
                className={`p-4 rounded-lg border transition-all ${
                  selectedCustomers.has(customer.id)
                    ? 'bg-blue-50 border-blue-200'
                    : 'bg-gray-50 border-gray-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <input
                      type="checkbox"
                      checked={selectedCustomers.has(customer.id)}
                      onChange={() => handleSelectCustomer(customer.id)}
                      className="h-4 w-4 text-blue-600 rounded"
                    />
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <h4 className="font-medium text-gray-900">{customer.name}</h4>
                        <Badge variant="outline">{customer.depot}</Badge>
                        {customer.priority_level === 'URGENT' && (
                          <Badge variant="destructive">Urgent</Badge>
                        )}
                      </div>
                      <p className="text-sm text-gray-600">{customer.address}</p>
                      {customer.last_visit_date && (
                        <p className="text-xs text-gray-500">
                          Last visit: {new Date(customer.last_visit_date).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEditCustomer(customer)}
                    >
                      <Edit className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDeleteCustomer(customer.id)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {filteredCustomers.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No customers found matching your criteria
            </div>
          )}
        </CardContent>
      </Card>

      {isEditing && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>
                {editingCustomer ? 'Edit Customer' : 'Add New Customer'}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Name</label>
                <Input
                  value={editingCustomer?.name || ''}
                  onChange={(e) => setEditingCustomer(prev => ({
                    ...prev,
                    id: prev?.id || 0,
                    name: e.target.value,
                    address: prev?.address || '',
                    depot: prev?.depot || 'Leesville',
                    priority_level: prev?.priority_level || 'STANDARD',
                    weekly_visit_required: prev?.weekly_visit_required ?? true
                  }))}
                  placeholder="Customer name"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Address</label>
                <Input
                  value={editingCustomer?.address || ''}
                  onChange={(e) => setEditingCustomer(prev => ({
                    ...prev,
                    id: prev?.id || 0,
                    name: prev?.name || '',
                    address: e.target.value,
                    depot: prev?.depot || 'Leesville',
                    priority_level: prev?.priority_level || 'STANDARD',
                    weekly_visit_required: prev?.weekly_visit_required ?? true
                  }))}
                  placeholder="Customer address"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Depot</label>
                <Select 
                  value={editingCustomer?.depot || 'Leesville'} 
                  onValueChange={(value) => setEditingCustomer(prev => ({
                    ...prev,
                    id: prev?.id || 0,
                    name: prev?.name || '',
                    address: prev?.address || '',
                    depot: value,
                    priority_level: prev?.priority_level || 'STANDARD',
                    weekly_visit_required: prev?.weekly_visit_required ?? true
                  }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {depots.map(depot => (
                      <SelectItem key={depot} value={depot}>{depot}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex justify-end space-x-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setIsEditing(false);
                    setEditingCustomer(null);
                  }}
                >
                  Cancel
                </Button>
                <Button 
                  onClick={() => editingCustomer && handleSaveCustomer(editingCustomer)}
                  disabled={!editingCustomer?.name || !editingCustomer?.address}
                >
                  Save
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
