import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_APP_ENV ?? "development",

  // Capture 10% of transactions for performance monitoring.
  // Raise this in production once you have a baseline.
  tracesSampleRate: 0.1,

  // Disable session replays (requires a paid Sentry plan).
  replaysSessionSampleRate: 0,
  replaysOnErrorSampleRate: 0,

  // Don't log Sentry debug info to the browser console.
  debug: false,
});
