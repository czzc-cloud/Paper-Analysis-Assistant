import React from "react";
import { createRoot } from "react-dom/client";
import {
  BarChart3,
  BookOpen,
  Download,
  FileText,
  Filter,
  FlaskConical,
  LayoutDashboard,
  Lightbulb,
  Network,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  Search,
  Table2,
  Target,
} from "lucide-react";
import "./styles.css";

const TYPE_COLORS = {
  paper: "#2563eb",
  method: "#0891b2",
  direction: "#7c3aed",
  gap: "#e11d48",
  claim: "#16a34a",
  limitation: "#dc2626",
  dataset: "#ca8a04",
  metric: "#475569",
};

const TYPE_LOW_COLORS = {
  paper: "#2563eb",
  method: "#cffafe",
  direction: "#ede9fe",
  gap: "#ffe4e6",
  claim: "#dcfce7",
  limitation: "#fee2e2",
  dataset: "#fef3c7",
  metric: "#e2e8f0",
};

const TYPE_ORDER = ["direction", "method", "gap", "paper"];
const TYPE_RANK = new Map(TYPE_ORDER.map((type, index) => [type, index]));
const BRANCH_TYPES = new Set(["method", "gap", "paper"]);
const VIEWBOX = { width: 1200, height: 820, cx: 600, cy: 410 };
const TAU = Math.PI * 2;
const VIEW_PHASE_STEPS = 1000;
const VIEW_TABS = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "matrix", label: "Method Matrix", icon: Table2 },
  { id: "papers", label: "Papers", icon: BookOpen },
  { id: "gaps", label: "Gaps", icon: Target },
  { id: "ideas", label: "Ideas", icon: Lightbulb },
  { id: "graph", label: "Graph Explore", icon: Network },
];

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function fetchOptionalJson(path) {
  try {
    return await fetchJson(path);
  } catch {
    return null;
  }
}

function App() {
  const [graph, setGraph] = React.useState(null);
  const [analysis, setAnalysis] = React.useState(null);
  const [error, setError] = React.useState("");
  const [query, setQuery] = React.useState("");
  const [selectedTypes, setSelectedTypes] = React.useState(new Set(TYPE_ORDER));
  const [selectedNodeId, setSelectedNodeId] = React.useState("");
  const [activeView, setActiveView] = React.useState("overview");

  const loadGraph = React.useCallback(() => {
    setError("");
    Promise.all([fetchJson("/api/graph"), fetchOptionalJson("/api/analysis")])
      .then(([graphData, analysisData]) => {
        setGraph(graphData);
        setAnalysis(analysisData);
        setSelectedNodeId(
          (graphData.nodes || []).find((node) => node.type === "direction")?.id ||
            graphData.nodes?.[0]?.id ||
            "",
        );
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  React.useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  const filtered = React.useMemo(() => {
    if (!graph) return { nodes: [], edges: [] };
    const q = query.trim().toLowerCase();
    const nodes = (graph.nodes || []).filter((node) => {
      if (!selectedTypes.has(node.type)) return false;
      if (!q) return true;
      return [node.name, node.summary, node.id, ...(node.tags || [])]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(q);
    });
    const nodeIds = new Set(nodes.map((node) => node.id));
    const edges = (graph.edges || []).filter(
      (edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target),
    );
    return { nodes, edges };
  }, [graph, query, selectedTypes]);

  const selectedNode = React.useMemo(
    () => (graph?.nodes || []).find((node) => node.id === selectedNodeId) || null,
    [graph, selectedNodeId],
  );

  const typeCounts = React.useMemo(() => {
    const counts = {};
    for (const node of graph?.nodes || []) counts[node.type] = (counts[node.type] || 0) + 1;
    return counts;
  }, [graph]);

  const dashboardData = React.useMemo(() => buildDashboardData(graph, analysis), [graph, analysis]);

  function toggleType(type) {
    setSelectedTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }

  if (error) {
    return (
      <main className="app app-centered">
        <section className="error-panel">
          <h1>Graph Load Failed</h1>
          <p>{error}</p>
          <button type="button" onClick={loadGraph}>
            <RefreshCw size={16} />
            Retry
          </button>
        </section>
      </main>
    );
  }

  if (!graph) {
    return (
      <main className="app app-centered">
        <div className="loading">Loading literature graph...</div>
      </main>
    );
  }

  return (
    <main className="app">
      <header className="topbar">
        <div>
          <h1>Literature Knowledge Graph</h1>
          <p>
            {graph.stats?.paperCount || 0} papers / {graph.stats?.nodeCount || 0} nodes /{" "}
            {graph.stats?.edgeCount || 0} edges
          </p>
        </div>
        <div className="topbar-actions">
          <a href="/api/graph" target="_blank" rel="noreferrer" title="Open graph JSON">
            <Download size={17} />
            Graph JSON
          </a>
          <a href="/api/report" target="_blank" rel="noreferrer" title="Open research report">
            <FileText size={17} />
            Report
          </a>
          <button type="button" onClick={loadGraph} title="Reload graph">
            <RefreshCw size={17} />
          </button>
        </div>
      </header>

      <nav className="view-tabs" aria-label="Dashboard views">
        {VIEW_TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              type="button"
              key={tab.id}
              className={activeView === tab.id ? "view-tab view-tab-active" : "view-tab"}
              onClick={() => setActiveView(tab.id)}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          );
        })}
      </nav>

      {activeView === "graph" ? (
        <section className="workspace">
          <aside className="sidebar">
            <label className="search-box">
              <Search size={16} />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search papers, methods, gaps"
              />
            </label>

            <div className="filter-title">
              <Filter size={15} />
              Node Types
            </div>
            <div className="type-list">
              {TYPE_ORDER.filter((type) => typeCounts[type]).map((type) => (
                <label key={type} className="type-toggle">
                  <input
                    type="checkbox"
                    checked={selectedTypes.has(type)}
                    onChange={() => toggleType(type)}
                  />
                  <span className="swatch" style={{ background: TYPE_COLORS[type] }} />
                  <span>{type}</span>
                  <strong>{typeCounts[type]}</strong>
                </label>
              ))}
            </div>
          </aside>

          <GraphCanvas
            nodes={filtered.nodes}
            edges={filtered.edges}
            selectedNodeId={selectedNodeId}
            onSelectNode={setSelectedNodeId}
          />

          <NodeDetails node={selectedNode} graph={graph} onSelectNode={setSelectedNodeId} />
        </section>
      ) : (
        <InsightsView
          view={activeView}
          data={dashboardData}
          graph={graph}
          analysis={analysis}
          onOpenGraph={(nodeId) => {
            if (nodeId) setSelectedNodeId(nodeId);
            setActiveView("graph");
          }}
        />
      )}
    </main>
  );
}

function InsightsView({ view, data, graph, analysis, onOpenGraph }) {
  if (view === "overview") {
    return <OverviewView data={data} onOpenGraph={onOpenGraph} />;
  }
  if (view === "matrix") {
    return <MethodMatrixView data={data} onOpenGraph={onOpenGraph} />;
  }
  if (view === "papers") {
    return <PapersView papers={data.papers} analysis={analysis} onOpenGraph={onOpenGraph} />;
  }
  if (view === "gaps") {
    return <GapsView data={data} onOpenGraph={onOpenGraph} />;
  }
  if (view === "ideas") {
    return <IdeasView data={data} />;
  }
  return <OverviewView data={data} graph={graph} onOpenGraph={onOpenGraph} />;
}

function OverviewView({ data, onOpenGraph }) {
  return (
    <section className="insight-page">
      <div className="summary-grid">
        <SummaryCard label="Papers" value={data.summary.paperCount} detail={`${data.summary.analysisMode || "analysis"} mode`} />
        <SummaryCard label="Research Areas" value={data.summary.researchAreaCount} detail={`${data.summary.mainstreamAreaCount || 0} mainstream`} />
        <SummaryCard label="Method Themes" value={data.summary.methodThemeCount} detail={`${data.hotMethods.length} ranked`} />
        <SummaryCard label="Gaps" value={data.summary.gapCount} detail={`${data.summary.underexploredAreaCount || 0} underexplored areas`} />
      </div>

      <div className="insight-grid insight-grid-3">
        <InsightPanel title="Mainstream Areas" icon={BarChart3}>
          <RankedList
            items={data.topResearchAreas}
            empty="No research areas detected."
            renderItem={(item, index) => (
              <ResearchAreaCard key={item.id || item.name} area={item} rank={index + 1} onOpenGraph={onOpenGraph} />
            )}
          />
        </InsightPanel>

        <InsightPanel title="Hot Methods" icon={FlaskConical}>
          <RankedList
            items={data.hotMethods}
            empty="No method themes detected."
            renderItem={(item, index) => (
              <MethodCard key={item.id || item.name} method={item} rank={index + 1} onOpenGraph={onOpenGraph} />
            )}
          />
        </InsightPanel>

        <InsightPanel title="Underexplored Areas" icon={Target}>
          <RankedList
            items={data.underexploredAreas}
            empty="No underexplored area signal detected."
            renderItem={(item, index) => (
              <ResearchAreaCard key={item.id || item.name} area={item} rank={index + 1} onOpenGraph={onOpenGraph} compact />
            )}
          />
        </InsightPanel>
      </div>
    </section>
  );
}

function MethodMatrixView({ data, onOpenGraph }) {
  const matrix = buildMatrixRows(data);
  return (
    <section className="insight-page">
      <InsightPanel title="Research Areas x Methods" icon={Table2}>
        <div className="matrix-wrap">
          <table className="method-matrix">
            <thead>
              <tr>
                <th>Area</th>
                {matrix.methods.map((method) => (
                  <th key={method}>{shortLabel(method, 18)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrix.rows.map((row) => (
                <tr key={row.area.id || row.area.name}>
                  <th>
                    <button type="button" onClick={() => onOpenGraph(row.area.id)}>
                      {shortLabel(row.area.name, 28)}
                    </button>
                    <span>{row.area.maturity}</span>
                  </th>
                  {matrix.methods.map((method) => {
                    const value = row.values.get(method) || 0;
                    return (
                      <td key={method}>
                        <span
                          className={value ? "matrix-cell matrix-cell-active" : "matrix-cell"}
                          style={{ opacity: value ? 0.28 + Math.min(value, 1) * 0.72 : 0.16 }}
                          title={`${row.area.name} / ${method}: ${Math.round(value * 100)}%`}
                        />
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </InsightPanel>
    </section>
  );
}

function PapersView({ papers, onOpenGraph }) {
  return (
    <section className="insight-page">
      <div className="paper-grid">
        {papers.length ? (
          papers.map((paper) => (
            <article key={paper.id} className="paper-card">
              <div className="card-kicker">paper</div>
              <h2>{paper.title || paper.id}</h2>
              <p>{paper.coreIdea || paper.problem || paper.summary || "No summary available."}</p>
              <MetaPills items={[...(paper.directions || []), paper.confidence].filter(Boolean).slice(0, 7)} />
              <h3>Methods</h3>
              <InlineList items={(paper.methods || []).map((method) => method.name || method).slice(0, 6)} />
              <h3>Limitations</h3>
              <InlineList items={(paper.limitations || []).map((item) => item.text || item).slice(0, 3)} />
              <button type="button" className="text-button" onClick={() => onOpenGraph(paper.id)}>
                Open in graph
              </button>
            </article>
          ))
        ) : (
          <EmptyState text="No paper summaries detected." />
        )}
      </div>
    </section>
  );
}

function GapsView({ data, onOpenGraph }) {
  return (
    <section className="insight-page">
      <div className="insight-grid insight-grid-2">
        <InsightPanel title="Research Gaps" icon={Target}>
          <RankedList
            items={data.researchGaps}
            empty="No research gaps detected."
            renderItem={(gap, index) => (
              <article key={gap.id || gap.name} className="rank-card">
                <div className="rank-index">{index + 1}</div>
                <div>
                  <h3>{gap.name}</h3>
                  <p>{gap.summary || gap.potentialValue || "No gap summary available."}</p>
                  <MetaPills items={[gap.gapType, gap.risk, `${gap.paperCount || 0} papers`, ...(gap.directions || [])].filter(Boolean).slice(0, 8)} />
                  {gap.id ? (
                    <button type="button" className="text-button" onClick={() => onOpenGraph(gap.id)}>
                      Open in graph
                    </button>
                  ) : null}
                </div>
              </article>
            )}
          />
        </InsightPanel>

        <InsightPanel title="Opportunity Areas" icon={Lightbulb}>
          <RankedList
            items={data.underexploredAreas}
            empty="No opportunity area detected."
            renderItem={(area, index) => (
              <ResearchAreaCard key={area.id || area.name} area={area} rank={index + 1} onOpenGraph={onOpenGraph} />
            )}
          />
        </InsightPanel>
      </div>
    </section>
  );
}

function IdeasView({ data }) {
  return (
    <section className="insight-page">
      <div className="ideas-grid">
        {data.methodologySuggestions.length ? (
          data.methodologySuggestions.map((idea, index) => (
            <article key={`${idea.title}-${index}`} className="idea-card">
              <div className="card-kicker">{idea.basis || "Inferred"}</div>
              <h2>{idea.title}</h2>
              <p>{idea.idea || "No idea text available."}</p>
              <h3>Candidate Methods</h3>
              <MetaPills items={(idea.candidateMethods || []).slice(0, 8)} />
              <h3>Experiment Sketch</h3>
              <p>{idea.experimentSketch || "No experiment sketch available."}</p>
            </article>
          ))
        ) : (
          <EmptyState text="No methodology suggestions detected." />
        )}
      </div>
    </section>
  );
}

function SummaryCard({ label, value, detail }) {
  return (
    <article className="summary-card">
      <span>{label}</span>
      <strong>{value ?? 0}</strong>
      <small>{detail}</small>
    </article>
  );
}

function InsightPanel({ title, icon: Icon, children }) {
  return (
    <section className="insight-panel">
      <header>
        <Icon size={17} />
        <h2>{title}</h2>
      </header>
      {children}
    </section>
  );
}

function RankedList({ items, empty, renderItem }) {
  if (!items?.length) return <EmptyState text={empty} />;
  return <div className="rank-list">{items.map(renderItem)}</div>;
}

function ResearchAreaCard({ area, rank, onOpenGraph, compact = false }) {
  const methods = area.topMethods?.length
    ? area.topMethods.map((method) => method.name || method)
    : area.trendTopMethods || [];
  return (
    <article className={compact ? "rank-card rank-card-compact" : "rank-card"}>
      <div className="rank-index">{rank}</div>
      <div>
        <h3>{area.name}</h3>
        <p>
          {area.paperCount || 0} papers / {area.methodCount || 0} methods / {area.gapCount || 0} gaps
        </p>
        <MetaPills items={[area.maturity, `heat ${formatNumber(area.heat)}`, ...methods].filter(Boolean).slice(0, 8)} />
        {area.id ? (
          <button type="button" className="text-button" onClick={() => onOpenGraph(area.id)}>
            Open in graph
          </button>
        ) : null}
      </div>
    </article>
  );
}

function MethodCard({ method, rank, onOpenGraph }) {
  return (
    <article className="rank-card">
      <div className="rank-index">{rank}</div>
      <div>
        <h3>{method.name}</h3>
        <p>
          {method.paperCount || 0} papers / {method.directionCount || 0} areas / hotness {formatNumber(method.hotness)}
        </p>
        <MetaPills items={(method.directions || []).slice(0, 6)} />
        {method.id ? (
          <button type="button" className="text-button" onClick={() => onOpenGraph(method.id)}>
            Open in graph
          </button>
        ) : null}
      </div>
    </article>
  );
}

function MetaPills({ items }) {
  const filtered = (items || []).filter(Boolean);
  if (!filtered.length) return null;
  return (
    <div className="meta-pills">
      {filtered.map((item, index) => (
        <span key={`${item}-${index}`}>{shortLabel(String(item), 36)}</span>
      ))}
    </div>
  );
}

function InlineList({ items }) {
  const filtered = (items || []).filter(Boolean);
  if (!filtered.length) return <p className="muted-text">None detected.</p>;
  return (
    <ul className="inline-list">
      {filtered.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </ul>
  );
}

function EmptyState({ text }) {
  return <p className="empty-state">{text}</p>;
}

function GraphCanvas({ nodes, edges, selectedNodeId, onSelectNode }) {
  const reducedMotion = usePrefersReducedMotion();
  const [isRotating, setIsRotating] = React.useState(true);
  const [yawPhase, setYawPhase] = React.useState(0);
  const [pitchPhase, setPitchPhase] = React.useState(0);
  const effectiveRotating = isRotating && !reducedMotion;
  const yawScrubberValue = phaseToScrubberValue(yawPhase);
  const pitchScrubberValue = phaseToScrubberValue(pitchPhase);

  React.useEffect(() => {
    if (!effectiveRotating) return undefined;
    let frame = 0;
    let previous = performance.now();
    const tick = (now) => {
      const delta = Math.min(now - previous, 48);
      previous = now;
      setYawPhase((value) => (value + delta * 0.00022) % TAU);
      setPitchPhase((value) => (value + delta * 0.00013) % TAU);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [effectiveRotating]);

  const layout = React.useMemo(() => buildSphericalLayout(nodes, edges), [nodes, edges]);
  const projected = React.useMemo(
    () => projectLayout(layout, yawPhase, pitchPhase),
    [layout, yawPhase, pitchPhase],
  );

  const selectedNeighborIds = React.useMemo(() => {
    const ids = new Set();
    for (const edge of layout.visualEdges) {
      if (edge.source === selectedNodeId) ids.add(edge.target);
      if (edge.target === selectedNodeId) ids.add(edge.source);
    }
    return ids;
  }, [layout.visualEdges, selectedNodeId]);

  return (
    <section className="graph-surface">
      <div className="graph-toolbar">
        <button
          type="button"
          onClick={() => setIsRotating((value) => !value)}
          title={isRotating ? "Pause rotation" : "Resume rotation"}
        >
          {isRotating ? <Pause size={16} /> : <Play size={16} />}
        </button>
        <button
          type="button"
          onClick={() => {
            setYawPhase(0);
            setPitchPhase(0);
          }}
          title="Reset view"
        >
          <RotateCcw size={16} />
        </button>
        <div className="heat-key" aria-label="Coverage heat">
          <span>Sparse</span>
          <i />
          <span>Dense</span>
        </div>
      </div>

      <svg
        viewBox={`0 0 ${VIEWBOX.width} ${VIEWBOX.height}`}
        role="img"
        aria-label="Literature knowledge graph"
      >
        <g className="sphere-guides" aria-hidden="true">
          <circle cx={VIEWBOX.cx} cy={VIEWBOX.cy} r="350" />
          <ellipse cx={VIEWBOX.cx} cy={VIEWBOX.cy} rx="430" ry="145" />
          <ellipse cx={VIEWBOX.cx} cy={VIEWBOX.cy} rx="185" ry="350" />
        </g>

        <g>
          {projected.edges.map((edge) => {
            const active = edge.source === selectedNodeId || edge.target === selectedNodeId;
            return (
              <line
                key={edge.id}
                x1={edge.sourcePoint.x}
                y1={edge.sourcePoint.y}
                x2={edge.targetPoint.x}
                y2={edge.targetPoint.y}
                className={active ? `edge edge-${edge.kind} edge-active` : `edge edge-${edge.kind}`}
                strokeWidth={edge.width}
                style={{ opacity: active ? Math.min(1, edge.opacity + 0.35) : edge.opacity }}
              />
            );
          })}
        </g>

        <g>
          {projected.nodes.map((node) => {
            const active = node.id === selectedNodeId || selectedNeighborIds.has(node.id);
            const labelVisible =
              node.type === "direction" ||
              active ||
              (node.heat >= 0.62 && node.depth > -140 && projected.nodes.length <= 130);
            const muted = selectedNodeId && !active && node.type !== "paper";
            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                className={active ? "node node-active" : "node"}
                opacity={muted ? Math.min(node.opacity, 0.48) : node.opacity}
                onPointerDown={(event) => event.preventDefault()}
                onClick={(event) => {
                  event.stopPropagation();
                  onSelectNode(node.id);
                }}
              >
                <title>{node.name || node.id}</title>
                <circle r={node.radius} fill={node.color} />
                {labelVisible ? (
                  <text x={node.radius + 7} y="4" className="node-label">
                    {shortLabel(node.name || node.id, node.type === "direction" ? 40 : 30)}
                  </text>
                ) : null}
              </g>
            );
          })}
        </g>
      </svg>

      <div
        className={
          effectiveRotating
            ? "view-scrubber view-scrubber-horizontal"
            : "view-scrubber view-scrubber-horizontal view-scrubber-active"
        }
      >
        <input
          type="range"
          min="0"
          max={VIEW_PHASE_STEPS}
          step="1"
          value={yawScrubberValue}
          disabled={effectiveRotating}
          aria-label="Horizontal view angle"
          title="Horizontal view angle"
          onChange={(event) => {
            const nextPhase = (Number(event.target.value) / VIEW_PHASE_STEPS) * TAU;
            setYawPhase(nextPhase);
          }}
        />
      </div>

      <div
        className={
          effectiveRotating
            ? "view-scrubber view-scrubber-vertical"
            : "view-scrubber view-scrubber-vertical view-scrubber-active"
        }
      >
        <input
          type="range"
          min="0"
          max={VIEW_PHASE_STEPS}
          step="1"
          value={pitchScrubberValue}
          disabled={effectiveRotating}
          aria-label="Vertical view angle"
          title="Vertical view angle"
          onChange={(event) => {
            const nextPhase = (Number(event.target.value) / VIEW_PHASE_STEPS) * TAU;
            setPitchPhase(nextPhase);
          }}
        />
      </div>
    </section>
  );
}

function NodeDetails({ node, graph, onSelectNode }) {
  const adjacent = React.useMemo(() => {
    if (!node) return [];
    const nodesById = new Map((graph.nodes || []).map((item) => [item.id, item]));
    return (graph.edges || [])
      .filter((edge) => edge.source === node.id || edge.target === node.id)
      .sort((left, right) => Number(right.weight || 0) - Number(left.weight || 0))
      .slice(0, 24)
      .map((edge) => {
        const otherId = edge.source === node.id ? edge.target : edge.source;
        return { edge, other: nodesById.get(otherId) };
      })
      .filter((item) => item.other);
  }, [node, graph]);

  if (!node) {
    return (
      <aside className="details">
        <h2>No Node Selected</h2>
      </aside>
    );
  }

  return (
    <aside className="details">
      <div className="node-type" style={{ color: TYPE_COLORS[node.type] || "#475569" }}>
        {node.type}
      </div>
      <h2>{node.name || node.id}</h2>
      <p>{node.summary || "No summary available."}</p>
      {node.tags?.length ? (
        <div className="tag-row">
          {node.tags.slice(0, 8).map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
        </div>
      ) : null}
      {node.metadata ? (
        <dl className="metadata">
          {Object.entries(node.metadata)
            .filter(([, value]) => value !== null && value !== undefined && value !== "")
            .slice(0, 10)
            .map(([key, value]) => (
              <React.Fragment key={key}>
                <dt>{key}</dt>
                <dd>{formatMetadataValue(value)}</dd>
              </React.Fragment>
            ))}
        </dl>
      ) : null}
      <h3>Connections</h3>
      <div className="connection-list">
        {adjacent.length ? (
          adjacent.map(({ edge, other }) => (
            <button
              type="button"
              key={`${edge.source}-${edge.target}-${edge.type}`}
              onClick={(event) => {
                event.preventDefault();
                onSelectNode(other.id);
              }}
            >
              <span>{formatEdgeType(edge)}</span>
              {shortLabel(other.name || other.id, 42)}
            </button>
          ))
        ) : (
          <p>No direct connections.</p>
        )}
      </div>
    </aside>
  );
}

function buildDashboardData(graph, analysis) {
  const insights = graph?.insights || {};
  const nodes = graph?.nodes || [];
  const analysisPapers = Array.isArray(analysis?.papers) ? analysis.papers : [];
  const paperNodesById = new Map(nodes.filter((node) => node.type === "paper").map((node) => [node.id, node]));
  const papers = analysisPapers.length
    ? analysisPapers.map((paper) => ({
        id: paper.paperId,
        title: paper.title,
        problem: paper.problem,
        coreIdea: paper.coreIdea,
        methods: paper.methods || [],
        limitations: paper.limitations || [],
        futureWork: paper.futureWork || [],
        directions: paper.directions || [],
        confidence: paper.confidence,
        summary: paperNodesById.get(paper.paperId)?.summary,
      }))
    : nodes
        .filter((node) => node.type === "paper")
        .map((node) => ({
          id: node.id,
          title: node.name,
          summary: node.summary,
          directions: node.tags || [],
          methods: [],
          limitations: [],
        }));

  const fallbackAreas = deriveAreasFromGraph(graph);
  const topResearchAreas = insights.topResearchAreas?.length ? insights.topResearchAreas : fallbackAreas;
  const methodsByArea = insights.methodsByArea?.length ? insights.methodsByArea : fallbackAreas;
  const hotMethods = insights.hotMethods?.length ? insights.hotMethods : deriveMethodsFromGraph(graph);
  const researchGaps = insights.researchGaps?.length ? insights.researchGaps : deriveGapsFromGraph(graph);
  const underexploredAreas = insights.underexploredAreas?.length
    ? insights.underexploredAreas
    : topResearchAreas.filter((area) => area.maturity === "underexplored" || area.gapCount > 0);

  return {
    summary: {
      paperCount: insights.summary?.paperCount ?? graph?.stats?.paperCount ?? papers.length,
      researchAreaCount: insights.summary?.researchAreaCount ?? graph?.stats?.directionCount ?? 0,
      methodThemeCount: insights.summary?.methodThemeCount ?? graph?.stats?.methodThemeCount ?? 0,
      gapCount: insights.summary?.gapCount ?? graph?.stats?.gapCount ?? 0,
      mainstreamAreaCount: insights.summary?.mainstreamAreaCount ?? topResearchAreas.filter((area) => area.maturity === "mainstream").length,
      underexploredAreaCount:
        insights.summary?.underexploredAreaCount ?? topResearchAreas.filter((area) => area.maturity === "underexplored").length,
      analysisMode: insights.summary?.analysisMode ?? analysis?.stats?.analysisMode ?? "analysis",
    },
    topResearchAreas,
    hotMethods,
    methodsByArea,
    underexploredAreas,
    researchGaps,
    methodologySuggestions: insights.methodologySuggestions?.length
      ? insights.methodologySuggestions
      : Array.isArray(analysis?.methodologySuggestions)
        ? analysis.methodologySuggestions
        : [],
    papers,
  };
}

function deriveAreasFromGraph(graph) {
  const nodesById = new Map((graph?.nodes || []).map((node) => [node.id, node]));
  return (graph?.nodes || [])
    .filter((node) => node.type === "direction")
    .map((node) => ({
      id: node.id,
      name: node.name,
      paperCount: node.metadata?.paperCount || 0,
      heat: node.metadata?.heat || 0,
      maturity: node.metadata?.maturity || "underexplored",
      methodCount: node.metadata?.methodThemeIds?.length || 0,
      gapCount: node.metadata?.gapThemeIds?.length || 0,
      topMethods: (node.metadata?.methodThemeIds || [])
        .map((id) => nodesById.get(id))
        .filter(Boolean)
        .map((method) => ({ id: method.id, name: method.name, paperCount: method.metadata?.paperCount || 0 })),
      trendTopMethods: node.metadata?.trendTopMethods || [],
    }))
    .sort((left, right) => Number(right.paperCount || 0) - Number(left.paperCount || 0));
}

function deriveMethodsFromGraph(graph) {
  return (graph?.nodes || [])
    .filter((node) => node.type === "method")
    .map((node) => ({
      id: node.id,
      name: node.name,
      paperCount: node.metadata?.paperCount || 0,
      directionCount: node.metadata?.directions?.length || 0,
      hotness: node.metadata?.heat || 0,
      directions: node.metadata?.directions || [],
      aliases: node.metadata?.aliases || [],
    }))
    .sort((left, right) => Number(right.hotness || 0) - Number(left.hotness || 0));
}

function deriveGapsFromGraph(graph) {
  return (graph?.nodes || [])
    .filter((node) => node.type === "gap")
    .map((node) => ({
      id: node.id,
      name: node.name,
      summary: node.summary,
      gapType: node.metadata?.gapType,
      paperCount: node.metadata?.paperCount || 0,
      directions: node.metadata?.directions || [],
      risk: node.metadata?.risk,
      potentialValue: node.metadata?.potentialValue,
    }))
    .sort((left, right) => Number(right.paperCount || 0) - Number(left.paperCount || 0));
}

function buildMatrixRows(data) {
  const methodNames = [];
  for (const method of data.hotMethods || []) {
    if (method.name && !methodNames.includes(method.name)) methodNames.push(method.name);
    if (methodNames.length >= 12) break;
  }
  for (const area of data.methodsByArea || []) {
    for (const method of area.topMethods || []) {
      const name = method.name || method;
      if (name && !methodNames.includes(name)) methodNames.push(name);
      if (methodNames.length >= 12) break;
    }
  }

  const rows = (data.methodsByArea || []).slice(0, 16).map((area) => {
    const values = new Map();
    for (const method of area.topMethods || []) {
      const name = method.name || method;
      if (!name) continue;
      const raw = Number(method.coverage ?? method.paperCount ?? 0);
      const value = raw > 1 ? raw / Math.max(1, Number(area.paperCount || 1)) : raw;
      values.set(name, Math.max(values.get(name) || 0, value));
    }
    return { area, values };
  });

  return { methods: methodNames.slice(0, 12), rows };
}

function buildSphericalLayout(nodes, semanticEdges) {
  const nodesById = new Map(nodes.map((node) => [node.id, node]));
  const directionNodes = nodes
    .filter((node) => node.type === "direction")
    .sort(compareNodes);
  const paperNodes = nodes.filter((node) => node.type === "paper").sort(compareNodes);
  const rootNodes = directionNodes.length ? directionNodes : paperNodes;
  const rootIds = new Set(rootNodes.map((node) => node.id));
  const heatById = computeHeat(nodes, semanticEdges);

  if (!rootNodes.length) {
    const positioned = [...nodes].sort(compareNodes).map((node, index) => {
      const heat = heatById.get(node.id) || 0.2;
      const point = fibonacciPoint(index, nodes.length, 290 + heat * 52);
      return layoutNode(node, point, heat);
    });
    return {
      nodes: positioned,
      visualEdges: buildMethodSimilarityEdges(nodes, semanticEdges, nodesById),
    };
  }

  const memberships = collectRootMemberships(nodes, semanticEdges, rootIds);
  const ownerByNodeId = assignNodeOwners(nodes, rootNodes, memberships);
  const rootRadius = rootNodes.length === 1 ? 0 : clamp(250 + rootNodes.length * 20, 300, 410);
  const childrenByRoot = new Map(rootNodes.map((root) => [root.id, []]));
  const positioned = [];

  rootNodes.forEach((root, index) => {
    const heat = heatById.get(root.id) || 1;
    positioned.push(layoutNode(root, rootPoint(index, rootNodes.length, rootRadius), heat));
  });

  for (const node of nodes) {
    if (rootIds.has(node.id)) continue;
    const rootId = ownerByNodeId.get(node.id);
    if (rootId && childrenByRoot.has(rootId)) {
      childrenByRoot.get(rootId).push(node);
    }
  }

  rootNodes.forEach((rootNode, rootIndex) => {
    const root = rootPoint(rootIndex, rootNodes.length, rootRadius);
    const children = childrenByRoot.get(rootNode.id).sort(compareNodes);
    const localRadius = clamp(96 + Math.sqrt(children.length) * 18, 116, 230);
    children.forEach((node, index) => {
      const heat = heatById.get(node.id) || 0.18;
      const radius = localRadius * typeDistance(node.type) * (0.88 + heat * 0.18);
      const localPoint = rotate3d(
        fibonacciPoint(index, children.length, radius),
        stableAngle(rootNode.id) * 0.45,
        stableAngle(`${rootNode.id}:${node.type}`) * 0.35,
      );
      positioned.push(layoutNode(node, addPoints(root, localPoint), heat));
    });
  });

  const visualEdges = [
    ...buildBranchEdges(nodes, nodesById, ownerByNodeId),
    ...buildMethodSimilarityEdges(nodes, semanticEdges, nodesById),
    ...buildPaperOverlapEdges(nodes, semanticEdges),
  ];

  return { nodes: positioned, visualEdges };
}

function projectLayout(layout, yawPhase, pitchPhase) {
  const projectedNodes = layout.nodes.map((item) => {
    const rotated = rotateWorld(item.point, yawPhase, pitchPhase);
    const perspective = 1180 / (1180 - rotated.z);
    const projectionScale = perspective * 0.95;
    const depthRatio = clamp((rotated.z + 540) / 1080, 0, 1);
    const radius = baseRadius(item.node.type) * projectionScale * (0.92 + item.heat * 0.22);
    return {
      ...item.node,
      color: colorForNode(item.node, item.heat),
      depth: rotated.z,
      heat: item.heat,
      opacity: clamp(0.34 + depthRatio * 0.62, 0.24, 0.98),
      radius: clamp(radius, 5.5, item.node.type === "direction" ? 25 : item.node.type === "paper" ? 14 : 17),
      x: VIEWBOX.cx + rotated.x * projectionScale,
      y: VIEWBOX.cy + rotated.y * projectionScale,
    };
  });

  const projectedById = new Map(projectedNodes.map((node) => [node.id, node]));
  const projectedEdges = layout.visualEdges
    .map((edge) => {
      const sourcePoint = projectedById.get(edge.source);
      const targetPoint = projectedById.get(edge.target);
      if (!sourcePoint || !targetPoint) return null;
      const depthRatio = clamp(((sourcePoint.depth + targetPoint.depth) / 2 + 540) / 1080, 0, 1);
      const baseOpacity =
        edge.kind === "similar"
          ? 0.24 + edge.weight * 0.48
          : edge.kind === "overlap"
            ? 0.18 + edge.weight * 0.32
            : 0.12 + edge.weight * 0.16;
      return {
        ...edge,
        sourcePoint,
        targetPoint,
        opacity: clamp(baseOpacity * (0.62 + depthRatio * 0.72), 0.07, 0.88),
        width:
          edge.kind === "similar"
            ? 0.9 + edge.weight * 4.2
            : edge.kind === "overlap"
              ? 0.8 + edge.weight * 2.4
              : 0.7 + edge.weight * 1.1,
        z: (sourcePoint.depth + targetPoint.depth) / 2,
      };
    })
    .filter(Boolean)
    .sort((left, right) => left.z - right.z);

  return {
    nodes: projectedNodes.sort((left, right) => left.depth - right.depth),
    edges: projectedEdges,
  };
}

function collectRootMemberships(nodes, semanticEdges, rootIds) {
  const memberships = new Map();

  function addMembership(nodeId, rootId) {
    if (!rootIds.has(rootId) || nodeId === rootId) return;
    if (!memberships.has(nodeId)) memberships.set(nodeId, new Set());
    memberships.get(nodeId).add(rootId);
  }

  for (const node of nodes) {
    for (const directionId of node.metadata?.directionIds || []) addMembership(node.id, directionId);
  }

  for (const edge of semanticEdges) {
    const sourceIsRoot = rootIds.has(edge.source);
    const targetIsRoot = rootIds.has(edge.target);
    if (sourceIsRoot && !targetIsRoot) addMembership(edge.target, edge.source);
    if (targetIsRoot && !sourceIsRoot) addMembership(edge.source, edge.target);
  }

  return memberships;
}

function assignNodeOwners(nodes, rootNodes, memberships) {
  const ownerByNodeId = new Map();
  const ownerCounts = new Map(rootNodes.map((root) => [root.id, 0]));

  for (const node of [...nodes].sort(compareNodes)) {
    if (ownerCounts.has(node.id)) continue;
    const candidates = [...(memberships.get(node.id) || [])].filter((rootId) => ownerCounts.has(rootId));
    const owner = candidates.length
      ? candidates.sort((left, right) => {
          const countDelta = ownerCounts.get(left) - ownerCounts.get(right);
          return countDelta || left.localeCompare(right);
        })[0]
      : rootNodes[stableHash(node.id) % rootNodes.length]?.id;
    if (!owner) continue;
    ownerByNodeId.set(node.id, owner);
    ownerCounts.set(owner, (ownerCounts.get(owner) || 0) + 1);
  }

  return ownerByNodeId;
}

function buildBranchEdges(nodes, nodesById, ownerByNodeId) {
  const edges = [];
  for (const node of nodes) {
    if (!BRANCH_TYPES.has(node.type)) continue;
    const rootId = ownerByNodeId.get(node.id);
    if (!rootId || !nodesById.has(rootId)) continue;
    edges.push({
      id: `branch:${rootId}:${node.id}`,
      source: rootId,
      target: node.id,
      kind: "branch",
      type: "overview_branch",
      weight: 0.18 + Math.min(Number(node.metadata?.heat || 0.2), 1) * 0.22,
    });
  }
  return edges;
}

function buildMethodSimilarityEdges(nodes, semanticEdges, nodesById) {
  const methodIds = new Set(nodes.filter((node) => node.type === "method").map((node) => node.id));
  const existing = semanticEdges
    .filter((edge) => edge.type === "similar_method" && methodIds.has(edge.source) && methodIds.has(edge.target))
    .map((edge, index) => ({
      id: `similar:${edge.source}:${edge.target}:${index}`,
      source: edge.source,
      target: edge.target,
      kind: "similar",
      type: edge.type,
      weight: clamp(Number(edge.weight || 0.35), 0.15, 1),
    }));

  if (existing.length) return existing;

  const methods = [...methodIds].map((id) => nodesById.get(id)).filter(Boolean);
  const candidates = [];
  for (let index = 0; index < methods.length; index += 1) {
    for (let next = index + 1; next < methods.length; next += 1) {
      const left = methods[index];
      const right = methods[next];
      const score = clientMethodSimilarity(left, right);
      if (score >= 0.11) {
        candidates.push({ source: left.id, target: right.id, score });
      }
    }
  }

  const degree = new Map();
  return candidates
    .sort((left, right) => right.score - left.score)
    .filter((edge) => {
      const sourceDegree = degree.get(edge.source) || 0;
      const targetDegree = degree.get(edge.target) || 0;
      if (sourceDegree >= 4 || targetDegree >= 4) return false;
      degree.set(edge.source, sourceDegree + 1);
      degree.set(edge.target, targetDegree + 1);
      return true;
    })
    .slice(0, 160)
    .map((edge, index) => ({
      id: `similar:client:${edge.source}:${edge.target}:${index}`,
      source: edge.source,
      target: edge.target,
      kind: "similar",
      type: "similar_method",
      weight: clamp(edge.score, 0.15, 1),
    }));
}

function buildPaperOverlapEdges(nodes, semanticEdges) {
  const paperIds = new Set(nodes.filter((node) => node.type === "paper").map((node) => node.id));
  return semanticEdges
    .filter((edge) => edge.type === "paper_overlap" && paperIds.has(edge.source) && paperIds.has(edge.target))
    .map((edge, index) => ({
      id: `overlap:${edge.source}:${edge.target}:${index}`,
      source: edge.source,
      target: edge.target,
      kind: "overlap",
      type: edge.type,
      weight: clamp(Number(edge.weight || 0.35), 0.15, 1),
    }));
}

function computeHeat(nodes, semanticEdges) {
  const heatById = new Map();
  const paperCounts = new Map();
  const paperIds = new Set(nodes.filter((node) => node.type === "paper").map((node) => node.id));

  for (const node of nodes) {
    if (typeof node.metadata?.heat === "number") {
      heatById.set(node.id, clamp(Number(node.metadata.heat), 0.12, 1));
    }
    if (typeof node.metadata?.paperCount === "number") {
      paperCounts.set(node.id, Number(node.metadata.paperCount));
    }
  }

  for (const edge of semanticEdges) {
    if (paperIds.has(edge.source) && !paperIds.has(edge.target)) {
      paperCounts.set(edge.target, Math.max(paperCounts.get(edge.target) || 0, 1));
    }
    if (paperIds.has(edge.target) && !paperIds.has(edge.source)) {
      paperCounts.set(edge.source, Math.max(paperCounts.get(edge.source) || 0, 1));
    }
  }

  const maxCount = Math.max(1, ...paperCounts.values());
  for (const node of nodes) {
    if (heatById.has(node.id)) continue;
    const count = node.type === "paper" ? maxCount : paperCounts.get(node.id) || 1;
    heatById.set(node.id, clamp(Math.log1p(count) / Math.log1p(maxCount), 0.14, 1));
  }

  return heatById;
}

function clientMethodSimilarity(left, right) {
  const leftTokens = tokenize(left.name || left.id);
  const rightTokens = tokenize(right.name || right.id);
  if (!leftTokens.size || !rightTokens.size) return 0;
  const sharedTokens = intersectionSize(leftTokens, rightTokens);
  const tokenScore = sharedTokens / unionSize(leftTokens, rightTokens);
  const leftPapers = new Set(left.metadata?.paperIds || []);
  const rightPapers = new Set(right.metadata?.paperIds || []);
  const paperScore = leftPapers.size && rightPapers.size ? intersectionSize(leftPapers, rightPapers) / Math.min(leftPapers.size, rightPapers.size) : 0;
  return tokenScore * 0.9 + paperScore * 0.1;
}

function layoutNode(node, point, heat) {
  return { node, point, heat: clamp(heat, 0.12, 1) };
}

function rootPoint(index, count, radius) {
  if (count <= 1) return { x: 0, y: 0, z: 0 };
  if (count === 2) {
    return { x: index === 0 ? -radius : radius, y: 0, z: index === 0 ? -radius * 0.25 : radius * 0.25 };
  }
  if (count === 3) {
    const angle = (Math.PI * 2 * index) / count - Math.PI / 2;
    return {
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius * 0.55,
      z: Math.sin(angle + Math.PI / 3) * radius * 0.42,
    };
  }
  return fibonacciPoint(index, count, radius);
}

function fibonacciPoint(index, count, radius) {
  if (count <= 1) return { x: radius * 0.2, y: 0, z: 0 };
  const offset = 2 / count;
  const increment = Math.PI * (3 - Math.sqrt(5));
  const y = index * offset - 1 + offset / 2;
  const r = Math.sqrt(Math.max(0, 1 - y * y));
  const phi = index * increment;
  return {
    x: Math.cos(phi) * r * radius,
    y: y * radius,
    z: Math.sin(phi) * r * radius,
  };
}

function rotateWorld(point, yawPhase, pitchPhase) {
  const tilted = rotate3d(point, pitchPhase - 0.32, yawPhase);
  return rotateZ(tilted, Math.sin(yawPhase * 0.45 + pitchPhase * 0.28) * 0.05);
}

function rotate3d(point, xAngle, yAngle) {
  const cosY = Math.cos(yAngle);
  const sinY = Math.sin(yAngle);
  const x = point.x * cosY + point.z * sinY;
  const z = -point.x * sinY + point.z * cosY;
  const cosX = Math.cos(xAngle);
  const sinX = Math.sin(xAngle);
  return {
    x,
    y: point.y * cosX - z * sinX,
    z: point.y * sinX + z * cosX,
  };
}

function rotateZ(point, angle) {
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  return {
    x: point.x * cos - point.y * sin,
    y: point.x * sin + point.y * cos,
    z: point.z,
  };
}

function addPoints(left, right) {
  return { x: left.x + right.x, y: left.y + right.y, z: left.z + right.z };
}

function typeDistance(type) {
  if (type === "paper") return 0.58;
  if (type === "direction") return 0.58;
  if (type === "method") return 0.92;
  if (type === "gap") return 1.12;
  if (type === "claim") return 1.02;
  if (type === "limitation") return 1.12;
  if (type === "dataset" || type === "metric") return 1.2;
  return 1;
}

function baseRadius(type) {
  if (type === "direction") return 18;
  if (type === "paper") return 8.6;
  if (type === "method") return 10.5;
  if (type === "gap") return 9.8;
  if (type === "claim") return 8.8;
  return 8.2;
}

function colorForNode(node, heat) {
  if (node.type === "paper") return TYPE_COLORS.paper;
  const low = TYPE_LOW_COLORS[node.type] || "#e2e8f0";
  const high = TYPE_COLORS[node.type] || "#64748b";
  return mixHex(low, high, clamp(heat, 0, 1));
}

function mixHex(left, right, amount) {
  const leftRgb = hexToRgb(left);
  const rightRgb = hexToRgb(right);
  const mixed = leftRgb.map((value, index) => Math.round(value + (rightRgb[index] - value) * amount));
  return `rgb(${mixed[0]}, ${mixed[1]}, ${mixed[2]})`;
}

function hexToRgb(value) {
  const normalized = value.replace("#", "");
  return [
    parseInt(normalized.slice(0, 2), 16),
    parseInt(normalized.slice(2, 4), 16),
    parseInt(normalized.slice(4, 6), 16),
  ];
}

function tokenize(value) {
  const stopWords = new Set([
    "and",
    "are",
    "based",
    "for",
    "from",
    "method",
    "methods",
    "model",
    "models",
    "network",
    "networks",
    "the",
    "with",
  ]);
  return new Set(
    String(value)
      .toLowerCase()
      .match(/[a-z0-9]+/g)
      ?.map((token) => normalizeToken(token))
      .filter((token) => token.length > 2 && !stopWords.has(token)) || [],
  );
}

function normalizeToken(token) {
  if (token.endsWith("ies") && token.length > 4) return `${token.slice(0, -3)}y`;
  if (token.endsWith("ing") && token.length > 5) return token.slice(0, -3);
  if (token.endsWith("ed") && token.length > 4) return token.slice(0, -2);
  if (token.endsWith("s") && token.length > 4 && !token.endsWith("ss") && !token.endsWith("is") && !token.endsWith("us")) {
    return token.slice(0, -1);
  }
  return token;
}

function intersectionSize(left, right) {
  let count = 0;
  for (const item of left) {
    if (right.has(item)) count += 1;
  }
  return count;
}

function unionSize(left, right) {
  return new Set([...left, ...right]).size || 1;
}

function stableHash(value) {
  let hash = 2166136261;
  for (let index = 0; index < String(value).length; index += 1) {
    hash ^= String(value).charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function stableAngle(value) {
  return (stableHash(value) / 0xffffffff) * Math.PI * 2;
}

function compareNodes(left, right) {
  const rankDelta = (TYPE_RANK.get(left.type) ?? 99) - (TYPE_RANK.get(right.type) ?? 99);
  if (rankDelta) return rankDelta;
  return String(left.name || left.id).localeCompare(String(right.name || right.id));
}

function phaseToScrubberValue(phase) {
  const normalized = ((phase % TAU) + TAU) % TAU;
  return Math.round((normalized / TAU) * VIEW_PHASE_STEPS);
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function shortLabel(value, maxLength) {
  if (!value) return "";
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}...` : value;
}

function formatMetadataValue(value) {
  if (Array.isArray(value)) return value.slice(0, 6).join(", ");
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(3);
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function formatNumber(value) {
  const number = Number(value || 0);
  if (!Number.isFinite(number)) return "0.00";
  return number.toFixed(2);
}

function formatEdgeType(edge) {
  const weight = typeof edge.weight === "number" ? ` ${edge.weight.toFixed(2)}` : "";
  return `${edge.type}${weight}`;
}

function usePrefersReducedMotion() {
  const [prefersReducedMotion, setPrefersReducedMotion] = React.useState(false);

  React.useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setPrefersReducedMotion(mediaQuery.matches);
    update();
    mediaQuery.addEventListener?.("change", update);
    return () => mediaQuery.removeEventListener?.("change", update);
  }, []);

  return prefersReducedMotion;
}

createRoot(document.getElementById("root")).render(<App />);
