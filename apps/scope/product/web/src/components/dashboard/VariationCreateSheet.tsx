/**
 * VariationCreateSheet — Bottom drawer for proposing a change order.
 * Contractor fills in title, optional description, amount, and reason.
 * Sends the change order to the homeowner for approval.
 */

import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { apiFetch, API_BASE } from '../../lib/api';
import { Button, Input, Sheet, Textarea } from '@scope/ui';

const variationSchema = z.object({
  title: z.string().min(3, 'Describe the change (minimum 3 characters)'),
  description: z.string().optional(),
  amount_cents: z.number().min(100, 'Minimum amount is €1'),
  reason: z.enum(['additional_materials', 'unforeseen_work', 'scope_change']),
});

type VariationForm = z.infer<typeof variationSchema>;

const REASON_LABELS: Record<string, string> = {
  additional_materials: 'Additional materials',
  unforeseen_work: 'Unforeseen work',
  scope_change: 'Scope change',
};

interface VariationCreateSheetProps {
  open: boolean;
  onClose: () => void;
  quoteToken: string;
  contractorId: string;
}

export function VariationCreateSheet({ open, onClose, quoteToken, contractorId }: VariationCreateSheetProps) {
  const { register, handleSubmit, reset, formState: { errors } } = useForm<VariationForm>({
    resolver: zodResolver(variationSchema),
    defaultValues: { reason: 'unforeseen_work' },
  });

  const onSubmit = async (data: VariationForm) => {
    const resp = await apiFetch(`${API_BASE}/v1/variation/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...data, quote_token: quoteToken, contractor_auth_id: contractorId }),
    });
    if (resp.ok) {
      toast.success('Change order sent to homeowner');
      reset();
      onClose();
    } else {
      toast.error('Failed to submit change order');
    }
  };

  return (
    <Sheet open={open} onClose={onClose}>
<div className="flex-1 overflow-y-auto px-5 pb-6">
            <h2 className="text-lg font-semibold text-ink mb-4 font-display">Propose change order</h2>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <label className="block text-xs text-stone mb-1.5">Change title</label>
                <Input {...register('title')}
                  placeholder="e.g. Additional debris removal" />
                {errors.title && <p className="text-xs text-red-500 mt-1">{errors.title.message}</p>}
              </div>

              <div>
                <label className="block text-xs text-stone mb-1.5">Description (optional)</label>
                <Textarea
                  {...register('description')}
                  rows={2}
                  className="w-full px-4 py-3 rounded-sm border border-border text-sm text-ink bg-white resize-none focus:outline-none focus:ring-1 focus:ring-terracotta"
                  placeholder="Explain the reason for the change…"
                />
              </div>

              <div>
                <label className="block text-xs text-stone mb-1.5">Additional amount (€)</label>
                <Input
                  type="number"
                  step="1"
                  min="1"
                  {...register('amount_cents', { setValueAs: (v) => Math.round(Number(v) * 100) })}
                  placeholder="200"
                  className="w-full px-4 py-3 rounded-sm border border-border text-sm text-ink bg-white focus:outline-none focus:ring-1 focus:ring-terracotta"
                />
                {errors.amount_cents && <p className="text-xs text-red-500 mt-1">{errors.amount_cents.message}</p>}
              </div>

              <div>
                <label className="block text-xs text-stone mb-1.5">Reason</label>
                <div className="space-y-1.5">
                  {Object.entries(REASON_LABELS).map(([value, label]) => (
                    <label key={value} className="flex items-center gap-2.5 px-3 py-2.5 rounded-sm border border-border cursor-pointer has-[:checked]:border-terracotta has-[:checked]:bg-terracotta/5">
                      <input type="radio" value={value} {...register('reason')} className="accent-terracotta" />
                      <span className="text-sm text-ink">{label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <Button fullWidth className="py-3.5" type="submit">Send to homeowner</Button>
            </form>
          </div>
        </Sheet>
  );
}
