"use client";

import { useCallback, useMemo } from "react";
import {
    ReactFlow,
    Background,
    type Node,
    type Edge,
    Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { CareerPath } from "@/lib/api";

interface PathVisualizationProps {
    paths: CareerPath[];
}

const STAGE_COLORS: Record<string, { bg: string; border: string; icon: string }> = {
    education: { bg: "linear-gradient(135deg, #667eea, #7c94f4)", border: "#667eea", icon: "🎓" },
    first_job: { bg: "linear-gradient(135deg, #764ba2, #9b6bc4)", border: "#764ba2", icon: "💼" },
    mid_career: { bg: "linear-gradient(135deg, #f093fb, #f5a7fc)", border: "#f093fb", icon: "📈" },
    current: { bg: "linear-gradient(135deg, #4ade80, #6ee7a0)", border: "#4ade80", icon: "⭐" },
};

const STAGE_LABELS: Record<string, string> = {
    education: "Education",
    first_job: "First Job",
    mid_career: "Mid Career",
    current: "Current Position",
};

/**
 * Custom node rendered inside React Flow.
 * We use a CSS-based approach (via the label string) since custom node
 * components require registration. React Flow renders the label as HTML
 * when it receives an HTMLElement via Data.label — but the simplest path
 * is to use the default node with a styled label.
 *
 * Instead, we build proper Node[] with styled labels rendered by React Flow.
 */
function buildFlowData(paths: CareerPath[]) {
    const nodes: Node[] = [];
    const edges: Edge[] = [];

    const Y_GAP = 180;
    const X_GAP = 280;

    paths.forEach((path, pathIdx) => {
        const yOffset = pathIdx * Y_GAP;
        const sourceLabel =
            path.source === "rapidfire"
                ? "Evidence-ranked"
                : "Prototype sample (demo)";
        const evidenceLabel =
            (path.evidence_count ?? 0) > 0
                ? `evidence: ${path.evidence_count} alumni trajectory signals`
                : "evidence: limited in demo";
        const whyPath =
            "Why this path: similar education starting point + realistic progression toward your target role.";

        // Path label node (left side)
        const pathLabelId = `path-label-${pathIdx}`;
        nodes.push({
            id: pathLabelId,
            position: { x: -280, y: yOffset + 15 },
            data: {
                label: `Path ${pathIdx + 1} · ${path.total_people} people · ~${path.avg_years}yr\n${sourceLabel}\n${evidenceLabel}\n${whyPath}`,
            },
            style: {
                background: "transparent",
                border: "none",
                color: "#8888aa",
                fontSize: "12px",
                width: 260,
                textAlign: "right" as const,
                whiteSpace: "pre-line" as const,
            },
            draggable: false,
            selectable: false,
            sourcePosition: Position.Right,
            targetPosition: Position.Left,
        });

        path.nodes.forEach((node, nodeIdx) => {
            const stage = STAGE_COLORS[node.stage] || STAGE_COLORS.current;
            const nodeId = `p${pathIdx}-n${nodeIdx}`;

            nodes.push({
                id: nodeId,
                position: { x: nodeIdx * X_GAP, y: yOffset },
                data: {
                    label: `${stage.icon} ${STAGE_LABELS[node.stage] || node.stage}\n${node.label}\n${node.typical_duration > 0 ? `~${Math.round(node.typical_duration / 12)}yr` : ""}`,
                },
                style: {
                    background: "#1e1e36",
                    border: `2px solid ${stage.border}`,
                    borderRadius: "12px",
                    padding: "12px 16px",
                    color: "#e8e8f0",
                    fontSize: "12px",
                    whiteSpace: "pre-line" as const,
                    width: 220,
                    textAlign: "center" as const,
                    boxShadow: `0 0 20px ${stage.border}22`,
                },
                sourcePosition: Position.Right,
                targetPosition: Position.Left,
            });

            // Edge to next node
            if (nodeIdx > 0) {
                const prevId = `p${pathIdx}-n${nodeIdx - 1}`;
                edges.push({
                    id: `e-${prevId}-${nodeId}`,
                    source: prevId,
                    target: nodeId,
                    animated: false,
                    style: { stroke: stage.border, strokeWidth: 2, opacity: 0.6 },
                });
            }
        });
    });

    return { nodes, edges };
}

export default function PathVisualization({ paths }: PathVisualizationProps) {
    const { nodes, edges } = useMemo(() => buildFlowData(paths), [paths]);
    const onInit = useCallback(() => {}, []);

    if (paths.length === 0) {
        return (
            <div className="glass rounded-2xl p-8 text-center text-[var(--color-muted)]">
                <p className="text-lg mb-2">📭 No career paths found</p>
                <p className="text-sm">Try broadening your search criteria.</p>
            </div>
        );
    }

    return (
        <div
            className="glass rounded-2xl overflow-hidden"
            style={{ height: 620 }}
        >
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onInit={onInit}
                fitView
                fitViewOptions={{ padding: 0.28 }}
                panOnScroll={false}
                panOnDrag={false}
                zoomOnScroll={false}
                zoomOnPinch={false}
                zoomOnDoubleClick={false}
                preventScrolling={false}
                proOptions={{ hideAttribution: true }}
                nodesDraggable={false}
                nodesConnectable={false}
                elementsSelectable={false}
            >
                <Background color="#2a2a48" gap={20} size={1} />
            </ReactFlow>
        </div>
    );
}
