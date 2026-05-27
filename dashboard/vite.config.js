import fs from "node:fs";
import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

function graphApiPlugin() {
  return {
    name: "paper-research-assistant-graph-api",
    configureServer(server) {
      server.middlewares.use("/api/graph", (_req, res) => {
        const graphFile =
          process.env.PRA_GRAPH_FILE ||
          path.join(process.env.PRA_GRAPH_DIR || process.cwd(), "literature-graph.json");
        if (!fs.existsSync(graphFile)) {
          res.statusCode = 404;
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(JSON.stringify({ error: `Graph file not found: ${graphFile}` }));
          return;
        }
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        res.end(fs.readFileSync(graphFile, "utf-8"));
      });

      server.middlewares.use("/api/analysis", (_req, res) => {
        const graphFile =
          process.env.PRA_GRAPH_FILE ||
          path.join(process.env.PRA_GRAPH_DIR || process.cwd(), "literature-graph.json");
        const analysisFile =
          process.env.PRA_ANALYSIS_FILE ||
          path.join(path.dirname(graphFile), "analysis.json");
        if (!fs.existsSync(analysisFile)) {
          res.statusCode = 404;
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(JSON.stringify({ error: `Analysis file not found: ${analysisFile}` }));
          return;
        }
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        res.end(fs.readFileSync(analysisFile, "utf-8"));
      });

      server.middlewares.use("/api/report", (_req, res) => {
        const reportFile = process.env.PRA_REPORT_FILE;
        if (!reportFile || !fs.existsSync(reportFile)) {
          res.statusCode = 404;
          res.setHeader("Content-Type", "text/plain; charset=utf-8");
          res.end("Report file not found.");
          return;
        }
        res.setHeader("Content-Type", "text/markdown; charset=utf-8");
        res.end(fs.readFileSync(reportFile, "utf-8"));
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), graphApiPlugin()],
  server: {
    host: "127.0.0.1",
    port: 5179,
  },
});
