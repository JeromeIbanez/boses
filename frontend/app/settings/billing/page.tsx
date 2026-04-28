"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  ArrowRight,
  CheckCircle2,
  CreditCard,
  Loader2,
  Zap,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
  BillingStatus,
  createCheckoutSession,
  createPortalSession,
  getBillingStatus,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Plan metadata
// ---------------------------------------------------------------------------

type Plan = {
  key: string;
  name: string;
  price: string;
  seats: string;
  sims: string;
  overage: string;
  color: string;
  popular?: boolean;
};

const PLANS: Plan[] = [
  {
    key: "starter",
    name: "Starter",
    price: "$199",
    seats: "3 seats",
    sims: "10 simulations / mo",
    overage: "$20 / extra sim",
    color: "blue",
  },
  {
    key: "pro",
    name: "Pro",
    price: "$499",
    seats: "10 seats",
    sims: "35 simulations / mo",
    overage: "$15 / extra sim",
    color: "purple",
    popular: true,
  },
  {
    key: "agency",
    name: "Agency",
    price: "$999",
    seats: "Unlimited seats",
    sims: "100 simulations / mo",
    overage: "$10 / extra sim",
    color: "amber",
  },
];

const PLAN_LABELS: Record<string, string> = {
  free: "Free",
  starter: "Starter",
  pro: "Pro",
  agency: "Agency",
  enterprise: "Enterprise",
};

const PLAN_BADGE_CLASS: Record<string, string> = {
  free: "bg-gray-100 text-gray-700",
  starter: "bg-blue-100 text-blue-700",
  pro: "bg-purple-100 text-purple-700",
  agency: "bg-amber-100 text-amber-700",
  enterprise: "bg-green-100 text-green-700",
};

const OVERAGE_NOTE: Record<string, string> = {
  free: "No overage — upgrade to run more simulations.",
  starter: "Extra simulations are billed at $20 each.",
  pro: "Extra simulations are billed at $15 each.",
  agency: "Extra simulations are billed at $10 each.",
  enterprise: "Overage terms are per your agreement.",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function BillingPage() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const checkoutStatus = searchParams.get("checkout");

  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkoutPlan, setCheckoutPlan] = useState<string | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  // Load billing status
  useEffect(() => {
    getBillingStatus()
      .then(setStatus)
      .catch(() => setStatus(null))
      .finally(() => setLoading(false));
  }, []);

  // Show success toast when returning from Stripe
  useEffect(() => {
    if (checkoutStatus === "success") {
      setToast("Subscription activated! Your new plan is now live.");
      // Refresh status after a short delay to pick up webhook update
      const t = setTimeout(() => {
        getBillingStatus().then(setStatus).catch(() => null);
      }, 3000);
      return () => clearTimeout(t);
    }
    if (checkoutStatus === "cancelled") {
      setToast("Checkout cancelled — no changes were made.");
    }
  }, [checkoutStatus]);

  // Auto-dismiss toast
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 5000);
    return () => clearTimeout(t);
  }, [toast]);

  const handleUpgrade = async (plan: string) => {
    setCheckoutPlan(plan);
    try {
      const { url } = await createCheckoutSession(plan);
      window.location.href = url;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Something went wrong. Please try again.";
      setToast(msg);
      setCheckoutPlan(null);
    }
  };

  const handlePortal = async () => {
    setPortalLoading(true);
    try {
      const { url } = await createPortalSession();
      window.location.href = url;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Something went wrong.";
      setToast(msg);
      setPortalLoading(false);
    }
  };

  const isOwnerOrAdmin = user?.role === "owner" || user?.role === "admin";

  const currentPlan = status?.plan ?? "free";
  const used = status?.simulations_used ?? 0;
  const limit = status?.plan_limit ?? 3;
  const pct = Math.min((used / Math.max(limit, 1)) * 100, 100);
  const periodEnds = status?.billing_period_ends_at
    ? new Date(status.billing_period_ends_at).toLocaleDateString(undefined, {
        month: "long",
        day: "numeric",
        year: "numeric",
      })
    : null;

  return (
    <div className="max-w-3xl mx-auto py-10 px-4 space-y-10">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-6 right-6 z-50 flex items-center gap-2 rounded-lg px-4 py-3 shadow-lg text-sm font-medium transition-all ${
            checkoutStatus === "success" || toast.includes("activated")
              ? "bg-green-50 text-green-800 border border-green-200"
              : "bg-red-50 text-red-800 border border-red-200"
          }`}
        >
          {(checkoutStatus === "success" || toast.includes("activated")) && (
            <CheckCircle2 className="h-4 w-4 shrink-0" />
          )}
          {toast}
        </div>
      )}

      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Billing</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage your subscription and simulation usage.
        </p>
      </div>

      {/* Current Plan Card */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm space-y-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
              Current Plan
            </p>
            <div className="mt-1 flex items-center gap-2">
              <span
                className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-sm font-semibold ${
                  PLAN_BADGE_CLASS[currentPlan] ?? "bg-gray-100 text-gray-700"
                }`}
              >
                {PLAN_LABELS[currentPlan] ?? currentPlan}
              </span>
            </div>
          </div>

          {status?.stripe_customer_id && isOwnerOrAdmin && (
            <button
              onClick={handlePortal}
              disabled={portalLoading}
              className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              {portalLoading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <CreditCard className="h-3.5 w-3.5" />
              )}
              Manage billing
            </button>
          )}
        </div>

        {/* Usage bar */}
        {loading ? (
          <div className="h-10 animate-pulse rounded-lg bg-gray-100" />
        ) : (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-gray-700">
                {used} / {limit} simulations used this period
              </span>
              {periodEnds && (
                <span className="text-gray-400 text-xs">Resets {periodEnds}</span>
              )}
            </div>
            <div className="h-2.5 w-full overflow-hidden rounded-full bg-gray-100">
              <div
                className={`h-full rounded-full transition-all ${
                  pct >= 90
                    ? "bg-red-500"
                    : pct >= 70
                    ? "bg-amber-500"
                    : "bg-emerald-500"
                }`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <p className="text-xs text-gray-400">{OVERAGE_NOTE[currentPlan]}</p>
          </div>
        )}
      </div>

      {/* Upgrade cards — only shown for owner/admin who aren't on enterprise */}
      {isOwnerOrAdmin && currentPlan !== "enterprise" && (
        <div>
          <h2 className="text-base font-semibold text-gray-800 mb-4">
            {currentPlan === "free" ? "Choose a plan" : "Upgrade your plan"}
          </h2>
          <div className="grid gap-4 sm:grid-cols-3">
            {PLANS.map((plan) => {
              const isCurrent = plan.key === currentPlan;
              const isLoading = checkoutPlan === plan.key;
              return (
                <div
                  key={plan.key}
                  className={`relative rounded-2xl border bg-white p-5 shadow-sm flex flex-col gap-4 ${
                    plan.popular
                      ? "border-purple-300 ring-1 ring-purple-200"
                      : "border-gray-200"
                  }`}
                >
                  {plan.popular && (
                    <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-purple-600 px-3 py-0.5 text-xs font-semibold text-white">
                      Most popular
                    </span>
                  )}
                  <div>
                    <p className="text-sm font-semibold text-gray-900">
                      {plan.name}
                    </p>
                    <p className="mt-0.5 text-2xl font-bold text-gray-900">
                      {plan.price}
                      <span className="text-sm font-normal text-gray-400">
                        /mo
                      </span>
                    </p>
                  </div>
                  <ul className="space-y-1.5 text-sm text-gray-600 flex-1">
                    <li className="flex items-center gap-1.5">
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                      {plan.seats}
                    </li>
                    <li className="flex items-center gap-1.5">
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                      {plan.sims}
                    </li>
                    <li className="flex items-center gap-1.5">
                      <Zap className="h-3.5 w-3.5 text-amber-400 shrink-0" />
                      {plan.overage}
                    </li>
                  </ul>
                  <button
                    onClick={() => handleUpgrade(plan.key)}
                    disabled={isCurrent || isLoading || !isOwnerOrAdmin}
                    className={`mt-auto flex items-center justify-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold transition-colors disabled:opacity-50 ${
                      isCurrent
                        ? "bg-gray-100 text-gray-500 cursor-default"
                        : plan.popular
                        ? "bg-purple-600 text-white hover:bg-purple-700"
                        : "bg-gray-900 text-white hover:bg-gray-700"
                    }`}
                  >
                    {isLoading ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : isCurrent ? (
                      "Current plan"
                    ) : (
                      <>
                        Get {plan.name}
                        <ArrowRight className="h-3.5 w-3.5" />
                      </>
                    )}
                  </button>
                </div>
              );
            })}
          </div>
          <p className="mt-4 text-center text-xs text-gray-400">
            Need custom volume or enterprise terms?{" "}
            <a
              href="mailto:hello@temujintechnologies.com"
              className="text-gray-600 underline hover:text-gray-900"
            >
              Contact us
            </a>
            .
          </p>
        </div>
      )}

      {/* Non-admin notice */}
      {!isOwnerOrAdmin && (
        <p className="text-sm text-gray-500 text-center">
          Only workspace owners and admins can manage billing.
        </p>
      )}
    </div>
  );
}
