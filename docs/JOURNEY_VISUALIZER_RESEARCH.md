# Journey Visualizer Research

## Feature Request

Add a journey DAG visualizer to the GUI admin. It should render journey steps as nodes and transitions as directed edges, with node-level state and conditions visible at a glance.

## Recommended Direction

Use React Flow for the GUI implementation, with Dagre for automatic directed layout.

- React Flow is designed for interactive React node and edge diagrams, supports custom nodes, custom edges, controls, and fit/zoom behavior.
- Dagre provides directed graph layout, which matches journey step ordering and branch visualization.
- Cytoscape.js is a strong fallback for graph analysis-heavy views, but it is less directly aligned with workflow-builder UX than React Flow.

## Node Data

Each node should expose:

- Step name, type, and position.
- Current state counts from `GET /api/v1/analytics/journeys`.
- Conditions and branch rules from step `config`.
- Wait settings for delay nodes.
- Template/campaign references for send-email nodes.
- Queued, completed, failed, and skipped counts.
- Recent error metadata when available.

## Edge Data

Initial edges can be derived from ordered `journey_steps.position`. Branch/exit edges should be added once branch config becomes explicit enough to model multiple downstream paths.

## API Support Needed

- Existing: `GET /api/v1/journeys/list`
- Existing: `GET /api/v1/analytics/journeys`
- Future: explicit journey graph endpoint returning `{ nodes, edges }` for GUI rendering.
- Future: branch-condition schema so DAG edges are not inferred from ad hoc config.

## Sources

- React Flow docs: https://reactflow.dev/docs/concepts/introduction
- React Flow API: https://reactflow.dev/api-reference/react-flow
- Dagre: https://github.com/dagrejs/dagre
- Cytoscape.js: https://js.cytoscape.org/
