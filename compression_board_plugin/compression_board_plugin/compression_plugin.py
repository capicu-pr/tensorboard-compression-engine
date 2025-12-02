from __future__ import annotations

"""
TensorBoard Compression plugin.
"""

import json
from typing import Any, Dict

from tensorboard.backend import http_util
from tensorboard.plugins import base_plugin
from werkzeug.wrappers import Request, Response


class CompressionPlugin(base_plugin.TBPlugin):
    """TensorBoard plugin that provides a Compression dashboard tab."""

    plugin_name = "compression"

    def __init__(self, context: base_plugin.TBContext) -> None:
        super().__init__(context)
        self._context = context

    def is_active(self) -> bool:
        """Return True if the plugin should be shown."""
        multiplexer = getattr(self._context, "multiplexer", None)
        if not multiplexer:
            return False
        runs = multiplexer.Runs()
        for run_name, run_info in runs.items():
            tags = run_info.get("scalars", [])
            if any("compression/" in tag for tag in tags):
                return True
        return False

    def get_plugin_apps(self) -> Dict[str, Any]:
        # Return handlers directly - TensorBoard will call them with (environ, start_response).
        # NOTE: The empty-string route maps to `/data/plugin/compression` in TensorBoard.
        return {
            "": self._serve_index,
            "/api/summary": self._serve_summary,
        }

    def _serve_index(self, environ, start_response):
        """Serve the dashboard HTML."""
        request = Request(environ)
        html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Compression Dashboard</title>
  <style>
    body { font-family: sans-serif; margin: 16px; background: #202124; color: #e8eaed; }
    h1 { font-size: 20px; margin-bottom: 4px; }
    table { border-collapse: collapse; margin-top: 12px; width: 100%; font-size: 13px; }
    th, td { border-bottom: 1px solid #3c4043; padding: 6px 8px; text-align: right; }
    th { text-align: left; background: #303134; }
    tr:nth-child(even) { background: #292a2d; }
  </style>
</head>
<body>
  <h1>Compression Dashboard</h1>
  <div id="root">Loading...</div>
  <script>
    fetch('api/summary')
      .then(r => r.json())
      .then(data => {
        const root = document.getElementById('root');
        if (!data.models || data.models.length === 0) {
          root.textContent = 'No compression data found.';
          return;
        }
        let html = '<table><thead><tr><th>Model</th><th>FP32 Acc</th><th>INT8 Acc</th><th>Speedup</th></tr></thead><tbody>';
        data.models.forEach(m => {
          html += `<tr><td>${m.run}</td><td>${(m.metrics.accuracy_fp32 || 0).toFixed(4)}</td><td>${(m.metrics.accuracy_int8 || 0).toFixed(4)}</td><td>${(m.metrics.speedup || 0).toFixed(2)}x</td></tr>`;
        });
        html += '</tbody></table>';
        root.innerHTML = html;
      })
      .catch(e => {
        document.getElementById('root').textContent = 'Error: ' + e.message;
      });
  </script>
</body>
</html>"""
        # Return Response object as WSGI app - call it to get iterable
        response = http_util.Respond(request, html, content_type="text/html")
        return response(environ, start_response)

    def _serve_summary(self, environ, start_response):
        """Return compression metrics as JSON."""
        request = Request(environ)
        multiplexer = getattr(self._context, "multiplexer", None)
        if not multiplexer:
            body = json.dumps({"models": [], "error": "multiplexer not available"})
        else:
            models = []
            runs = multiplexer.Runs()
            
            for run_name, run_info in runs.items():
                tags = run_info.get("scalars", [])
                if not any("compression/" in tag for tag in tags):
                    continue
                
                def get_scalar(tag):
                    if tag not in tags:
                        return None
                    try:
                        events = multiplexer.Scalars(run_name, tag)
                        return float(events[-1].value) if events else None
                    except:
                        return None
                
                models.append({
                    "run": run_name,
                    "metrics": {
                        "accuracy_fp32": get_scalar(f"{run_name}/metrics/accuracy/fp32"),
                        "accuracy_int8": get_scalar(f"{run_name}/metrics/accuracy/int8"),
                        "speedup": get_scalar(f"{run_name}/compression/speedup"),
                        "size_ratio": get_scalar(f"{run_name}/compression/size_ratio"),
                    }
                })
            
            body = json.dumps({"models": models})
        
        # Return Response object as WSGI app - call it to get iterable
        response = http_util.Respond(request, body, content_type="application/json")
        return response(environ, start_response)
