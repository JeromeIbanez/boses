// This file is required by Next.js to initialise Sentry on the server side.
// It is loaded once when the server starts and supports both Node.js and Edge runtimes.
export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("./sentry.server.config");
  }
  if (process.env.NEXT_RUNTIME === "edge") {
    await import("./sentry.edge.config");
  }
}
