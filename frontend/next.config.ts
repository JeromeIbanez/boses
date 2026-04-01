import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const nextConfig: NextConfig = {
  output: "standalone",
};

export default withSentryConfig(nextConfig, {
  // Suppress noisy Sentry CLI output during builds.
  silent: true,

  // Source map upload requires a Sentry auth token (SENTRY_AUTH_TOKEN env var).
  // Without it, source maps are simply not uploaded — error tracking still works.
  hideSourceMaps: true,

  // Tree-shake Sentry debug logging out of production bundles.
  disableLogger: true,
});
