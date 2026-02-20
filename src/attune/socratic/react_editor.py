"""React Flow Editor Components

Generates React Flow compatible schemas and standalone HTML pages
for interactive workflow editing in the browser.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from typing import Any

from .blueprint import WorkflowBlueprint
from .editor_models import EditorState, NodeType
from .workflow_visualizer import WorkflowVisualizer


def generate_react_flow_schema(state: EditorState) -> dict[str, Any]:
    """Generate React Flow compatible schema.

    Args:
        state: Editor state

    Returns:
        Schema for React Flow library
    """
    # Node types for React Flow
    node_type_map = {
        NodeType.START: "input",
        NodeType.END: "output",
        NodeType.STAGE: "default",
        NodeType.AGENT: "default",
    }

    # Node styles
    node_styles = {
        NodeType.START: {
            "background": "#10b981",
            "color": "white",
            "border": "2px solid #059669",
            "borderRadius": "50%",
            "width": 80,
            "height": 80,
        },
        NodeType.END: {
            "background": "#ef4444",
            "color": "white",
            "border": "2px solid #dc2626",
            "borderRadius": "50%",
            "width": 80,
            "height": 80,
        },
        NodeType.STAGE: {
            "background": "#3b82f6",
            "color": "white",
            "border": "2px solid #2563eb",
            "borderRadius": "8px",
            "padding": "10px",
        },
        NodeType.AGENT: {
            "background": "#8b5cf6",
            "color": "white",
            "border": "2px solid #7c3aed",
            "borderRadius": "8px",
            "padding": "8px",
        },
    }

    nodes = []
    for node in state.nodes:
        rf_node = {
            "id": node.node_id,
            "type": node_type_map.get(node.node_type, "default"),
            "position": node.position.to_dict(),
            "data": {
                "label": node.label,
                **node.data,
            },
            "style": node_styles.get(node.node_type, {}),
            "draggable": not node.locked,
            "selectable": True,
        }
        nodes.append(rf_node)

    edges = []
    for edge in state.edges:
        rf_edge = {
            "id": edge.edge_id,
            "source": edge.source,
            "target": edge.target,
            "label": edge.label,
            "animated": edge.animated,
            "style": {"strokeWidth": 2},
            "markerEnd": {"type": "arrowclosed"},
        }
        edges.append(rf_edge)

    return {
        "nodes": nodes,
        "edges": edges,
        "defaultViewport": {
            "x": state.pan_x,
            "y": state.pan_y,
            "zoom": state.zoom,
        },
    }


def generate_editor_html(
    blueprint: WorkflowBlueprint,
    title: str = "Workflow Editor",
) -> str:
    """Generate standalone HTML page with workflow editor.

    Args:
        blueprint: The workflow blueprint
        title: Page title

    Returns:
        Complete HTML page
    """
    visualizer = WorkflowVisualizer()
    state = visualizer.blueprint_to_editor(blueprint)
    react_schema = generate_react_flow_schema(state)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/reactflow@11/dist/umd/index.js"></script>
    <link href="https://unpkg.com/reactflow@11/dist/style.css" rel="stylesheet" />
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: system-ui, -apple-system, sans-serif; }}
        #root {{ width: 100vw; height: 100vh; }}
        .react-flow__node {{ font-size: 12px; }}
        .react-flow__edge-path {{ stroke-width: 2; }}

        .panel {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 1000;
        }}

        .panel h3 {{
            margin-bottom: 10px;
            font-size: 14px;
            color: #374151;
        }}

        .panel p {{
            font-size: 12px;
            color: #6b7280;
            margin-bottom: 5px;
        }}

        .export-btn {{
            margin-top: 10px;
            padding: 8px 16px;
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }}

        .export-btn:hover {{ background: #2563eb; }}
    </style>
</head>
<body>
    <div id="root"></div>
    <script>
        const {{ useState, useCallback }} = React;
        const {{ ReactFlow, Background, Controls, MiniMap }} = window.ReactFlow;

        const initialNodes = {json.dumps(react_schema["nodes"], indent=2)};
        const initialEdges = {json.dumps(react_schema["edges"], indent=2)};

        function WorkflowEditor() {{
            const [nodes, setNodes] = useState(initialNodes);
            const [edges, setEdges] = useState(initialEdges);
            const [selectedNode, setSelectedNode] = useState(null);

            const onNodesChange = useCallback((changes) => {{
                setNodes((nds) => {{
                    return nds.map((node) => {{
                        const change = changes.find(c => c.id === node.id);
                        if (change && change.type === 'position' && change.position) {{
                            return {{ ...node, position: change.position }};
                        }}
                        return node;
                    }});
                }});
            }}, []);

            const onNodeClick = useCallback((event, node) => {{
                setSelectedNode(node);
            }}, []);

            const exportWorkflow = () => {{
                const data = {{ nodes, edges }};
                const blob = new Blob([JSON.stringify(data, null, 2)], {{ type: 'application/json' }});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'workflow.json';
                a.click();
            }};

            return React.createElement('div', {{ style: {{ width: '100%', height: '100%' }} }},
                React.createElement(ReactFlow, {{
                    nodes: nodes,
                    edges: edges,
                    onNodesChange: onNodesChange,
                    onNodeClick: onNodeClick,
                    fitView: true,
                }},
                    React.createElement(Background, null),
                    React.createElement(Controls, null),
                    React.createElement(MiniMap, null)
                ),
                React.createElement('div', {{ className: 'panel' }},
                    React.createElement('h3', null, '{blueprint.name}'),
                    React.createElement('p', null, 'Agents: {len(blueprint.agents)}'),
                    React.createElement('p', null, 'Stages: {len(blueprint.stages)}'),
                    selectedNode && React.createElement('div', null,
                        React.createElement('hr', {{ style: {{ margin: '10px 0' }} }}),
                        React.createElement('p', null, 'Selected: ' + selectedNode.data.label),
                        selectedNode.data.role && React.createElement('p', null, 'Role: ' + selectedNode.data.role),
                        selectedNode.data.tools && React.createElement('p', null, 'Tools: ' + selectedNode.data.tools.length)
                    ),
                    React.createElement('button', {{
                        className: 'export-btn',
                        onClick: exportWorkflow
                    }}, 'Export JSON')
                )
            );
        }}

        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(React.createElement(WorkflowEditor));
    </script>
</body>
</html>"""
