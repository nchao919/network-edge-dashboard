# Network Edge Business Dashboard

A single-file, self-contained analytics dashboard for Equinix Network Edge built with vanilla HTML, CSS, and Chart.js.

![Equinix](https://img.shields.io/badge/Equinix-Network%20Edge-E91C24?style=flat&logoColor=white)

## Features

- **13 analytics tabs** covering the full NE business — Growth, Adoption, Partners, Health, Competitive, Financial, Vendor & Service, Connectivity, Architecture, Performance, Lifecycle, Segments & GTM, Ratios & Metro
- **50+ charts** (bar, line, doughnut, scatter, heatmap, stacked) powered by Chart.js 4
- **Equinix Horizon color scheme** — confirmed brand palette (#E91C24 red, #0057A0 blue, #00C4D4 aqua, #7B2FBE violet)
- **Dark mode default** with light/dark toggle
- **Left sidebar navigation** grouped into Growth · Commercial · Product · Customers
- **EAP API ready** — Bearer token config modal, auto-refresh, live/sample data status badge
- **Salesforce-ready** — structured for SOQL-based data injection
- **Zero build step** — open `NE_Dashboard.html` directly in any browser

## Quick Start

```bash
open NE_Dashboard.html
```

Or serve locally:

```bash
python3 -m http.server 8080
# then open http://localhost:8080/NE_Dashboard.html
```

## Connecting Live Data

### EAP API
1. Open the dashboard in your browser
2. Click the **⚠ Sample Data** badge in the header
3. Paste your EAP Bearer token and set the base URL (`https://eap.equinix.com/api/v1`)
4. Click **Connect & Refresh**

The token is stored in `localStorage` only — never sent anywhere except EAP.

### Salesforce
See the `EAP` config object in the `<script>` block for endpoint and field map configuration. SOQL queries can be injected by replacing sample data arrays with `fetch()` calls to your Salesforce Connected App.

## Dashboard Sections

| Tab | Section | Key Metrics |
|-----|---------|-------------|
| 0 | Growth & Revenue | New logos, pipeline, deal cycle, MRR trend |
| 1 | Adoption Metrics | Device growth, attachment rate, customer segments |
| 2 | Partners (MRR) | Partner MRR, tier distribution, pipeline contribution |
| 3 | Customer Health | NPS, churn risk, support tickets, CSAT |
| 4 | Competitive | Win rate, loss reasons, competitive displacement |
| 5 | Financial Health | Gross margin, revenue mix, cost per device |
| 6 | Vendor & Service | Vendor × service type heatmap, VNF mix |
| 7 | Connectivity | Destination mix, peering vs transit, port utilization |
| 8 | Architecture | Topology mix, complexity index, VNF ceiling |
| 9 | Performance | Throughput utilization, latency, capacity headroom |
| 10 | Lifecycle | Device age, deployment duration, coterm cohorts |
| 11 | Segments & GTM | Customer segment mix, buyer persona, GTM motion |
| 12 | Ratios & Metro | Multi-VNF, multi-metro, expansion ratio, geo utilization |

## Tech Stack

- **Chart.js 4.4.0** — all chart rendering
- **Vanilla HTML/CSS/JS** — no framework, no build tooling
- **CSS custom properties** — full light/dark theming via `[data-theme]`
- **localStorage** — token and theme persistence

## File Structure

```
Nelson Control Center/
└── NE_Dashboard.html    # entire dashboard — one file
└── README.md
```

## License

Internal Equinix use. Not for distribution.
